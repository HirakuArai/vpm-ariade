# --- core/conversation_migrator.py ---
"""
Conversation Migration - 会話ログ移行機能
全体会話ログからプロジェクト固有ログを生成
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)
_JST = ZoneInfo("Asia/Tokyo")

class ConversationMigrator:
    """会話ログ移行管理"""
    
    def __init__(self):
        self.conversations_dir = Path("conversations")
        self.data_conversations_dir = Path("data/conversations")
        self.projects_dir = Path("data/projects")
        
        # プロジェクト固有会話ディレクトリを作成
        self.data_conversations_dir.mkdir(parents=True, exist_ok=True)
    
    def get_available_projects(self) -> List[str]:
        """利用可能なプロジェクトIDリストを取得"""
        projects = []
        if self.projects_dir.exists():
            for project_file in self.projects_dir.glob("*.json"):
                projects.append(project_file.stem)
        return sorted(projects)
    
    def migrate_conversations_for_project(self, project_id: str) -> Dict:
        """特定プロジェクトの会話ログを移行"""
        try:
            migrated_dates = []
            
            # 全体会話ログファイルを検索
            if not self.conversations_dir.exists():
                return {"success": False, "message": "会話ログディレクトリが見つかりません"}
            
            for conv_file in self.conversations_dir.glob("conversation_*.json"):
                date_str = conv_file.stem.replace("conversation_", "")
                
                # 該当プロジェクトの会話を抽出
                project_messages = self._extract_project_messages(conv_file, project_id)
                
                if project_messages:
                    # プロジェクト固有ログとして保存
                    success = self._save_project_conversation(project_id, date_str, project_messages)
                    if success:
                        migrated_dates.append(date_str)
            
            return {
                "success": True,
                "message": f"{len(migrated_dates)}日分の会話ログを移行しました",
                "migrated_dates": migrated_dates
            }
            
        except Exception as e:
            logger.error(f"Conversation migration failed for {project_id}: {e}")
            return {"success": False, "message": f"移行エラー: {str(e)}"}
    
    def _extract_project_messages(self, conv_file: Path, project_id: str) -> List[Dict]:
        """全体会話ログから特定プロジェクトの会話を抽出"""
        try:
            with open(conv_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            messages = data.get("messages", [])
            project_messages = []
            
            # プロジェクト関連の会話を特定
            in_project_context = False
            
            for i, msg in enumerate(messages):
                content = msg.get("content", "")
                
                # プロジェクト選択や作成の検出
                if self._is_project_related(content, project_id):
                    in_project_context = True
                
                # プロジェクトコンテキスト外への移行検出
                elif self._is_context_change(content):
                    in_project_context = False
                
                # プロジェクト関連の会話を収集
                if in_project_context:
                    project_messages.append({
                        "role": msg["role"],
                        "content": content,
                        "timestamp": msg.get("ts", "")
                    })
            
            return project_messages
            
        except Exception as e:
            logger.error(f"Failed to extract project messages from {conv_file}: {e}")
            return []
    
    def _is_project_related(self, content: str, project_id: str) -> bool:
        """会話がプロジェクト関連かを判定"""
        # プロジェクトID直接言及
        if project_id in content:
            return True
        
        # 基本的なプロジェクト関連キーワードのみ（汎用的なもの）
        generic_project_keywords = [
            "プロジェクト作成",
            "プロジェクト開始",
            "プロジェクト選択"
        ]
        
        # Note: 特定プロジェクト固有のキーワード検出は制限的
        # より精密な会話移行が必要な場合は、AI判定機能の実装が推奨される
        return any(keyword in content for keyword in generic_project_keywords)
    
    def _is_context_change(self, content: str) -> bool:
        """プロジェクトコンテキストから外れたかを判定"""
        context_change_keywords = [
            "別のプロジェクト",
            "新しいプロジェクト",
            "他の件",
            "次の話題",
            "ホームページ",
            "メインメニュー"
        ]
        
        # Note: シンプルなキーワードマッチングのみ
        # より高精度な文脈変化検出には、AI判定機能の実装が必要
        return any(keyword in content for keyword in context_change_keywords)
    
    def _save_project_conversation(self, project_id: str, date_str: str, messages: List[Dict]) -> bool:
        """プロジェクト固有会話ログを保存"""
        try:
            # プロジェクト会話ディレクトリを作成
            project_conv_dir = self.data_conversations_dir / project_id
            project_conv_dir.mkdir(parents=True, exist_ok=True)
            
            # JSONL形式で保存
            jsonl_file = project_conv_dir / f"{date_str}.jsonl"
            
            with open(jsonl_file, 'w', encoding='utf-8') as f:
                for msg in messages:
                    log_entry = {
                        "project_id": project_id,
                        "role": msg["role"],
                        "content": msg["content"],
                        "timestamp": msg.get("timestamp", "")
                    }
                    f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
            
            logger.info(f"Saved {len(messages)} messages to {jsonl_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save project conversation: {e}")
            return False
    
    def migrate_all_projects(self) -> Dict:
        """全プロジェクトの会話ログを移行"""
        projects = self.get_available_projects()
        results = {}
        total_migrated = 0
        
        for project_id in projects:
            result = self.migrate_conversations_for_project(project_id)
            results[project_id] = result
            
            if result["success"]:
                total_migrated += len(result.get("migrated_dates", []))
        
        return {
            "success": True,
            "message": f"{len(projects)}プロジェクト、合計{total_migrated}日分を移行しました",
            "project_results": results
        }
    
    def get_migration_status(self) -> Dict:
        """移行状況を取得"""
        projects = self.get_available_projects()
        status = {}
        
        for project_id in projects:
            project_conv_dir = self.data_conversations_dir / project_id
            
            if project_conv_dir.exists():
                jsonl_files = list(project_conv_dir.glob("*.jsonl"))
                status[project_id] = {
                    "migrated": True,
                    "available_dates": [f.stem for f in jsonl_files]
                }
            else:
                status[project_id] = {
                    "migrated": False,
                    "available_dates": []
                }
        
        return status


def create_migrator() -> ConversationMigrator:
    """ConversationMigratorのファクトリ関数"""
    return ConversationMigrator()