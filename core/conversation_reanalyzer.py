# --- core/conversation_reanalyzer.py ---
"""
Conversation Reanalyzer - 会話再分析モジュール
過去の会話ログを指定日付で再分析し、プロジェクト情報を更新する機能
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)
_JST = ZoneInfo("Asia/Tokyo")

class ConversationReanalyzer:
    """過去会話の再分析機能"""
    
    def __init__(self):
        self.data_dir = Path("data")
        self.conversations_dir = self.data_dir / "conversations"
        self.projects_dir = self.data_dir / "projects"
    
    def get_available_dates(self, project_id: str) -> List[str]:
        """指定プロジェクトで利用可能な会話日付一覧を取得"""
        try:
            project_conv_dir = self.conversations_dir / project_id
            if not project_conv_dir.exists():
                return []
            
            dates = []
            for jsonl_file in project_conv_dir.glob("*.jsonl"):
                if jsonl_file.stem.isdigit() and len(jsonl_file.stem) == 8:  # YYYYMMDD形式
                    dates.append(jsonl_file.stem)
            
            return sorted(dates, reverse=True)  # 新しい順
            
        except Exception as e:
            logger.error(f"Error getting available dates for {project_id}: {e}")
            return []
    
    def load_conversation_by_date(self, project_id: str, date_str: str) -> List[Dict]:
        """指定日付の会話ログを読み込み"""
        try:
            jsonl_file = self.conversations_dir / project_id / f"{date_str}.jsonl"
            if not jsonl_file.exists():
                logger.warning(f"Conversation file not found: {jsonl_file}")
                return []
            
            messages = []
            with jsonl_file.open(encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        try:
                            entry = json.loads(line.strip())
                            # 会話分析用の形式に変換
                            messages.append({
                                "role": entry["role"],
                                "content": entry["content"],
                                "timestamp": entry.get("timestamp", "")
                            })
                        except json.JSONDecodeError as e:
                            logger.warning(f"Invalid JSON line in {jsonl_file}: {e}")
                            continue
            
            logger.info(f"Loaded {len(messages)} messages from {date_str}")
            return messages
            
        except Exception as e:
            logger.error(f"Error loading conversation for {project_id} on {date_str}: {e}")
            return []
    
    def reanalyze_conversation(self, project_id: str, date_str: str, dry_run: bool = False) -> Dict:
        """指定日付の会話を再分析してプロジェクト情報を更新"""
        try:
            # 1. 会話ログの読み込み
            messages = self.load_conversation_by_date(project_id, date_str)
            if not messages:
                return {
                    "success": False,
                    "message": f"No conversation found for {date_str}",
                    "updated_fields": 0,
                    "conflicts": [],
                    "extracted_info": []
                }
            
            logger.info(f"Starting reanalysis of {len(messages)} messages from {date_str}")
            
            # 2. 不足しているフィールドを追加
            from core.dynamic_schema import add_missing_fields_to_project
            add_missing_fields_to_project(project_id)
            
            # 3. シンプルな会話分析機能を使用
            from core.simple_conversation_analyzer import SimpleConversationAnalyzer
            
            # 4. AIによる直接的な分析と更新
            analyzer = SimpleConversationAnalyzer()
            result, updated_count = analyzer.analyze_and_update_project(messages, project_id, dry_run=dry_run)
            
            # 更新結果のサマリーを作成
            extraction_summary = []
            if result.get("updates") and result["updates"].get("fields"):
                for field_name, update_info in result["updates"]["fields"].items():
                    extraction_summary.append({
                        "field_name": field_name,
                        "value": update_info["value"],
                        "confidence": update_info.get("confidence", 0.9),
                        "extraction_method": "ai_direct_analysis",
                        "reason": update_info.get("reason", "")
                    })
            
            logger.info(f"AI identified {len(extraction_summary)} updates")
            
            # 5. 分析実行結果の処理
            if dry_run:
                # ドライランモード：実際の更新は行わない
                logger.info("Running in dry-run mode - no actual updates will be made")
                
                return {
                    "success": True,
                    "message": f"Dry run completed for {date_str}",
                    "updated_fields": 0,
                    "conflicts": [],
                    "dry_run": True,
                    "extracted_info": extraction_summary,
                    "analyzed_messages": len(messages)
                }
            else:
                # 実際の更新は既に analyzer.analyze_and_update_project で完了
                
                # 6. 再分析メタデータの記録
                self._record_reanalysis_metadata(project_id, date_str, updated_count)
                
                # 7. プロジェクトデータをGitにプッシュ
                try:
                    from core.git_ops import commit_and_push_project_data
                    push_success = commit_and_push_project_data(project_id)
                    if push_success:
                        logger.info(f"Successfully pushed reanalysis results for {project_id} to Git")
                    else:
                        logger.warning(f"Failed to push reanalysis results for {project_id} to Git")
                except Exception as e:
                    logger.error(f"Error pushing reanalysis results to Git: {e}")
                
                return {
                    "success": True,
                    "message": f"Successfully reanalyzed {date_str}",
                    "updated_fields": updated_count,
                    "conflicts": [],
                    "analyzed_messages": len(messages),
                    "extracted_info": extraction_summary
                }
                
        except Exception as e:
            logger.error(f"Error during reanalysis of {project_id} on {date_str}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "success": False,
                "message": f"Error during reanalysis: {str(e)}",
                "updated_fields": 0,
                "conflicts": [],
                "extracted_info": []
            }
    
    def _record_reanalysis_metadata(self, project_id: str, date_str: str, updated_count: int):
        """再分析のメタデータを記録"""
        try:
            project_file = self.projects_dir / f"{project_id}.json"
            if not project_file.exists():
                logger.warning(f"Project file not found: {project_file}")
                return
            
            # プロジェクトファイルの読み込み
            with project_file.open(encoding="utf-8") as f:
                project_data = json.load(f)
            
            # 再分析履歴の追加
            if "reanalysis_history" not in project_data:
                project_data["reanalysis_history"] = []
            
            reanalysis_entry = {
                "date_analyzed": date_str,
                "reanalyzed_at": datetime.now(_JST).isoformat(),
                "updated_fields": updated_count,
                "analyzer_version": "v2_phase_2_4"
            }
            
            project_data["reanalysis_history"].append(reanalysis_entry)
            
            # プロジェクトファイルの更新
            with project_file.open("w", encoding="utf-8") as f:
                json.dump(project_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Recorded reanalysis metadata for {project_id} - {date_str}")
            
        except Exception as e:
            logger.error(f"Error recording reanalysis metadata: {e}")
    
    def get_reanalysis_history(self, project_id: str) -> List[Dict]:
        """プロジェクトの再分析履歴を取得"""
        try:
            project_file = self.projects_dir / f"{project_id}.json"
            if not project_file.exists():
                return []
            
            with project_file.open(encoding="utf-8") as f:
                project_data = json.load(f)
            
            return project_data.get("reanalysis_history", [])
            
        except Exception as e:
            logger.error(f"Error getting reanalysis history for {project_id}: {e}")
            return []
    
    def batch_reanalyze_project(self, project_id: str, date_range: Optional[Tuple[str, str]] = None) -> Dict:
        """プロジェクトの複数日付を一括再分析"""
        try:
            available_dates = self.get_available_dates(project_id)
            if not available_dates:
                return {
                    "success": False,
                    "message": "No conversation dates found",
                    "results": []
                }
            
            # 日付範囲のフィルタリング
            if date_range:
                start_date, end_date = date_range
                available_dates = [
                    date for date in available_dates 
                    if start_date <= date <= end_date
                ]
            
            logger.info(f"Starting batch reanalysis for {len(available_dates)} dates")
            
            results = []
            total_updated = 0
            
            for date_str in available_dates:
                logger.info(f"Processing date: {date_str}")
                result = self.reanalyze_conversation(project_id, date_str)
                results.append({
                    "date": date_str,
                    "result": result
                })
                
                if result["success"]:
                    total_updated += result["updated_fields"]
            
            return {
                "success": True,
                "message": f"Batch reanalysis completed for {len(available_dates)} dates",
                "total_updated_fields": total_updated,
                "results": results
            }
            
        except Exception as e:
            logger.error(f"Error during batch reanalysis: {e}")
            return {
                "success": False,
                "message": f"Batch reanalysis error: {str(e)}",
                "results": []
            }

def create_reanalyzer() -> ConversationReanalyzer:
    """ConversationReanalyzerのファクトリ関数"""
    return ConversationReanalyzer()