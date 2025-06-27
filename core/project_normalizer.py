# -*- coding: utf-8 -*-
"""
Project Data Normalizer - プロジェクトデータ統一化システム
プロジェクトデータの構造とフィールドを統一する
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class ProjectNormalizer:
    """プロジェクトデータの統一化"""
    
    def __init__(self):
        self.standard_schema = {
            "identifier": "",
            "display_name": "",
            "overview": "",
            "created_at": "",
            "created_by": "human_user",
            "status": "DRAFT",
            "schema_version": "1.0",
            "updated_at": "",
            "change_log": [],
            "uuid": "",
            "tasks": [],
            "phase": "INCEPTION",
            "completion_percentage": 0.0,
            "next_actions": [],
            "blocking_issues": [],
            "phase_requirements": {},
            "phase_history": []
        }
        
        self.task_schema = {
            "id": 0,
            "description": "",
            "due_date": "",
            "owner": "human_user",
            "status": "pending"
        }
    
    def normalize_all_projects(self) -> Dict[str, Any]:
        """全プロジェクトを統一化"""
        results = {
            "normalized_count": 0,
            "errors": [],
            "projects": []
        }
        
        projects_dir = Path("data/projects")
        if not projects_dir.exists():
            results["errors"].append("プロジェクトディレクトリが存在しません")
            return results
        
        for project_file in projects_dir.glob("*.json"):
            try:
                result = self.normalize_project(project_file.stem)
                if result["success"]:
                    results["normalized_count"] += 1
                    results["projects"].append({
                        "id": project_file.stem,
                        "changes": result["changes"]
                    })
                else:
                    results["errors"].append(f"{project_file.stem}: {result['error']}")
            except Exception as e:
                results["errors"].append(f"{project_file.stem}: {str(e)}")
        
        return results
    
    def normalize_project(self, project_id: str) -> Dict[str, Any]:
        """単一プロジェクトの統一化"""
        try:
            project_path = Path(f"data/projects/{project_id}.json")
            if not project_path.exists():
                return {"success": False, "error": "プロジェクトファイルが存在しません"}
            
            # 現在のデータを読み込み
            with project_path.open("r", encoding="utf-8") as f:
                original_data = json.load(f)
            
            # 統一化実行
            normalized_data, changes = self._normalize_data(original_data)
            
            # 変更があった場合のみ保存
            if changes:
                # バックアップ作成
                backup_path = project_path.with_suffix(f".json.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}")
                with backup_path.open("w", encoding="utf-8") as f:
                    json.dump(original_data, f, ensure_ascii=False, indent=2)
                
                # 統一化されたデータを保存
                with project_path.open("w", encoding="utf-8") as f:
                    json.dump(normalized_data, f, ensure_ascii=False, indent=2)
                
                logger.info(f"Project {project_id} normalized with {len(changes)} changes")
            
            return {
                "success": True,
                "changes": changes,
                "backup_created": len(changes) > 0
            }
            
        except Exception as e:
            logger.error(f"Failed to normalize project {project_id}: {e}")
            return {"success": False, "error": str(e)}
    
    def _normalize_data(self, data: Dict[str, Any]) -> tuple[Dict[str, Any], List[str]]:
        """データの統一化実行"""
        normalized = data.copy()
        changes = []
        
        # 基本フィールドの統一化
        for field, default_value in self.standard_schema.items():
            if field not in normalized:
                normalized[field] = default_value
                changes.append(f"フィールド追加: {field}")
            elif normalized[field] == "__UNDEFINED__":
                normalized[field] = default_value
                changes.append(f"未定義値修正: {field}")
        
        # display_nameの統一化
        if not normalized.get("display_name"):
            if normalized.get("overview"):
                # overviewから表示名を生成
                overview = normalized["overview"]
                if len(overview) > 20:
                    normalized["display_name"] = overview[:20] + "..."
                else:
                    normalized["display_name"] = overview
                changes.append("display_name を overview から生成")
            else:
                normalized["display_name"] = normalized.get("identifier", "無題プロジェクト")
                changes.append("display_name を identifier から生成")
        
        # タスクの統一化
        if normalized.get("tasks"):
            normalized_tasks = []
            for task in normalized["tasks"]:
                normalized_task = self._normalize_task(task)
                normalized_tasks.append(normalized_task)
            
            if normalized_tasks != normalized["tasks"]:
                normalized["tasks"] = normalized_tasks
                changes.append("タスクフィールドを統一化")
        
        # 型の統一化
        if isinstance(normalized.get("completion_percentage"), str):
            try:
                normalized["completion_percentage"] = float(normalized["completion_percentage"])
                changes.append("completion_percentage を数値に変換")
            except:
                normalized["completion_percentage"] = 0.0
                changes.append("completion_percentage をデフォルト値に設定")
        
        # updated_atの更新
        if changes:
            normalized["updated_at"] = datetime.now().isoformat()
            changes.append("updated_at を更新")
        
        # 変更ログの追加
        if changes:
            change_entry = {
                "timestamp": datetime.now().isoformat(),
                "type": "data_normalization",
                "description": f"プロジェクトデータ統一化: {len(changes)}件の変更",
                "changes": changes,
                "source": "project_normalizer"
            }
            if "change_log" not in normalized:
                normalized["change_log"] = []
            normalized["change_log"].append(change_entry)
        
        return normalized, changes
    
    def _normalize_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """単一タスクの統一化"""
        normalized_task = {}
        
        for field, default_value in self.task_schema.items():
            if field in task:
                value = task[field]
                if value == "__UNDEFINED__":
                    normalized_task[field] = default_value
                else:
                    normalized_task[field] = value
            else:
                normalized_task[field] = default_value
        
        # 追加フィールドも保持
        for field, value in task.items():
            if field not in self.task_schema:
                normalized_task[field] = value
        
        return normalized_task
    
    def validate_project_consistency(self) -> Dict[str, Any]:
        """プロジェクト間の一貫性検証"""
        validation_results = {
            "total_projects": 0,
            "consistent_projects": 0,
            "issues": [],
            "schema_compliance": {},
            "recommendations": []
        }
        
        projects_dir = Path("data/projects")
        if not projects_dir.exists():
            validation_results["issues"].append("プロジェクトディレクトリが存在しません")
            return validation_results
        
        for project_file in projects_dir.glob("*.json"):
            validation_results["total_projects"] += 1
            
            try:
                with project_file.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                
                # スキーマ準拠性チェック
                compliance = self._check_schema_compliance(data)
                validation_results["schema_compliance"][project_file.stem] = compliance
                
                if compliance["compliant"]:
                    validation_results["consistent_projects"] += 1
                else:
                    for issue in compliance["issues"]:
                        validation_results["issues"].append(f"{project_file.stem}: {issue}")
                
            except Exception as e:
                validation_results["issues"].append(f"{project_file.stem}: 読み込みエラー - {str(e)}")
        
        # 推奨事項の生成
        if validation_results["issues"]:
            validation_results["recommendations"].append("プロジェクトデータの統一化を実行してください")
        
        return validation_results
    
    def _check_schema_compliance(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """スキーマ準拠性の検証"""
        issues = []
        
        # 必須フィールドのチェック
        for field in self.standard_schema.keys():
            if field not in data:
                issues.append(f"必須フィールド欠落: {field}")
            elif data[field] == "__UNDEFINED__":
                issues.append(f"未定義値: {field}")
        
        # データ型のチェック
        if "completion_percentage" in data:
            if not isinstance(data["completion_percentage"], (int, float)):
                issues.append("completion_percentage が数値ではありません")
        
        if "tasks" in data:
            for i, task in enumerate(data["tasks"]):
                for field in self.task_schema.keys():
                    if field not in task:
                        issues.append(f"タスク{i+1}: フィールド欠落 {field}")
                    elif task[field] == "__UNDEFINED__":
                        issues.append(f"タスク{i+1}: 未定義値 {field}")
        
        return {
            "compliant": len(issues) == 0,
            "issues": issues,
            "score": max(0, 100 - len(issues) * 10)  # 問題1件につき10点減点
        }

def normalize_all_projects() -> Dict[str, Any]:
    """全プロジェクト統一化のエントリーポイント"""
    normalizer = ProjectNormalizer()
    return normalizer.normalize_all_projects()

def validate_project_consistency() -> Dict[str, Any]:
    """プロジェクト一貫性検証のエントリーポイント"""
    normalizer = ProjectNormalizer()
    return normalizer.validate_project_consistency()