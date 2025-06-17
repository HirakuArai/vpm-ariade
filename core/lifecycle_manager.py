# --- core/lifecycle_manager.py ---
"""
ProjectLifecycleManager - プロジェクトライフサイクル管理
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional

from .models import Project, ProjectPhase, ProjectStatus, DEFAULT_UNDEF
from .project_service import get_project, update_project_field

logger = logging.getLogger(__name__)

class PhaseRequirements:
    """各フェーズの進行要件定義"""
    
    @staticmethod
    def get_requirements(phase: ProjectPhase) -> Dict[str, Any]:
        """フェーズ進行に必要な要件を返す"""
        requirements = {
            ProjectPhase.INCEPTION: {
                "name": "構想段階から定義段階への進行",
                "required_fields": ["overview"],
                "required_actions": [],
                "description": "プロジェクトの基本概要が定義されている"
            },
            ProjectPhase.DEFINITION: {
                "name": "定義段階から計画段階への進行", 
                "required_fields": ["overview"],
                "required_actions": ["charter_created"],
                "description": "プロジェクトチャーターが作成されている"
            },
            ProjectPhase.PLANNING: {
                "name": "計画段階から実行段階への進行",
                "required_fields": ["tasks"],
                "required_actions": ["wbs_created", "timeline_defined"],
                "description": "WBSとタイムラインが定義されている"
            },
            ProjectPhase.EXECUTION: {
                "name": "実行段階から監視段階への進行",
                "required_fields": ["tasks"],
                "required_actions": ["tasks_started"],
                "description": "タスクが開始されている"
            },
            ProjectPhase.MONITORING: {
                "name": "監視段階から完了段階への進行",
                "required_fields": ["completion_percentage"],
                "required_actions": ["deliverables_completed"],
                "description": "成果物が完成している"
            }
        }
        return requirements.get(phase, {})

class ProjectLifecycleManager:
    """プロジェクトライフサイクル管理クラス"""
    
    def __init__(self, projects_dir: Path | None = None):
        self.projects_dir = projects_dir
        self.phase_requirements = PhaseRequirements()
    
    def get_current_phase(self, project_id: str) -> ProjectPhase:
        """現在のプロジェクトフェーズを取得"""
        project_data = get_project(project_id, self.projects_dir)
        if not project_data:
            raise ValueError(f"Project {project_id} not found")
        
        phase_str = project_data.get("phase", ProjectPhase.INCEPTION.value)
        try:
            return ProjectPhase(phase_str)
        except ValueError:
            logger.warning("Invalid phase %s for project %s, defaulting to INCEPTION", phase_str, project_id)
            return ProjectPhase.INCEPTION
    
    def can_advance_to_next_phase(self, project_id: str) -> Tuple[bool, List[str]]:
        """次のフェーズに進行可能かチェック"""
        current_phase = self.get_current_phase(project_id)
        
        # CLOSUREフェーズは最終フェーズ
        if current_phase == ProjectPhase.CLOSURE:
            return False, ["プロジェクトは既に完了フェーズです"]
        
        # 次のフェーズを取得
        next_phase = self._get_next_phase(current_phase)
        if not next_phase:
            return False, ["次のフェーズが定義されていません"]
        
        # 要件チェック
        requirements = self.phase_requirements.get_requirements(current_phase)
        missing_requirements = self._check_phase_requirements(project_id, requirements)
        
        return len(missing_requirements) == 0, missing_requirements
    
    def advance_phase(self, project_id: str) -> bool:
        """プロジェクトを次のフェーズに進める"""
        can_advance, missing_requirements = self.can_advance_to_next_phase(project_id)
        
        if not can_advance:
            logger.warning("Cannot advance phase for project %s: %s", project_id, missing_requirements)
            return False
        
        current_phase = self.get_current_phase(project_id)
        next_phase = self._get_next_phase(current_phase)
        
        if not next_phase:
            logger.error("No next phase defined for %s", current_phase)
            return False
        
        # フェーズ更新
        success = update_project_field(project_id, "phase", next_phase.value, self.projects_dir)
        
        if success:
            # フェーズ履歴に記録
            self._record_phase_transition(project_id, current_phase, next_phase)
            
            # 完了率更新 - 直接ファイルを更新
            completion_percentage = self._calculate_completion_percentage(next_phase)
            try:
                if self.projects_dir:
                    project_path = self.projects_dir / f"{project_id}.json"
                else:
                    from .project_service import PROJECTS_DIR
                    project_path = PROJECTS_DIR / f"{project_id}.json"
                
                if project_path.exists():
                    import json
                    with open(project_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    data["completion_percentage"] = completion_percentage
                    data["updated_at"] = datetime.utcnow().isoformat()
                    
                    with open(project_path, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)
            except Exception as e:
                logger.error("Error updating completion percentage for project %s: %s", project_id, str(e))
            
            logger.info("Advanced project %s from %s to %s", project_id, current_phase.value, next_phase.value)
            return True
        
        return False
    
    def get_phase_progress(self, project_id: str) -> Dict[str, Any]:
        """フェーズの進捗情報を取得"""
        current_phase = self.get_current_phase(project_id)
        project_data = get_project(project_id, self.projects_dir)
        
        if not project_data:
            return {}
        
        can_advance, requirements = self.can_advance_to_next_phase(project_id)
        
        # Safe initialization for completion_percentage
        completion_percentage = project_data.get("completion_percentage", 0.0)
        if not isinstance(completion_percentage, (int, float)) or completion_percentage == 0.0:
            # Calculate based on current phase if not set or is zero
            completion_percentage = self._calculate_completion_percentage(current_phase)
        
        # Safe initialization for phase_history
        phase_history = project_data.get("phase_history", [])
        if not isinstance(phase_history, list):
            phase_history = []
        
        return {
            "current_phase": current_phase.value,
            "completion_percentage": completion_percentage,
            "can_advance": can_advance,
            "missing_requirements": requirements,
            "phase_history": phase_history,
            "next_phase": self._get_next_phase(current_phase).value if self._get_next_phase(current_phase) else None
        }
    
    def get_phase_requirements_checklist(self, project_id: str) -> Dict[str, Any]:
        """現在フェーズの要件チェックリストを取得"""
        current_phase = self.get_current_phase(project_id)
        requirements = self.phase_requirements.get_requirements(current_phase)
        
        if not requirements:
            return {}
        
        checklist = {
            "phase": current_phase.value,
            "requirements": requirements,
            "status": []
        }
        
        # 各要件のステータスをチェック
        missing_requirements = self._check_phase_requirements(project_id, requirements)
        
        for field in requirements.get("required_fields", []):
            is_satisfied = field not in [req.split(":")[0] for req in missing_requirements if ":" in req]
            checklist["status"].append({
                "requirement": f"必須フィールド: {field}",
                "satisfied": is_satisfied
            })
        
        for action in requirements.get("required_actions", []):
            is_satisfied = action not in missing_requirements
            checklist["status"].append({
                "requirement": f"必須アクション: {action}",
                "satisfied": is_satisfied
            })
        
        return checklist
    
    def _get_next_phase(self, current_phase: ProjectPhase) -> Optional[ProjectPhase]:
        """次のフェーズを取得"""
        phase_order = [
            ProjectPhase.INCEPTION,
            ProjectPhase.DEFINITION,
            ProjectPhase.PLANNING,
            ProjectPhase.EXECUTION,
            ProjectPhase.MONITORING,
            ProjectPhase.CLOSURE
        ]
        
        try:
            current_index = phase_order.index(current_phase)
            if current_index < len(phase_order) - 1:
                return phase_order[current_index + 1]
        except ValueError:
            logger.error("Unknown phase: %s", current_phase)
        
        return None
    
    def _check_phase_requirements(self, project_id: str, requirements: Dict[str, Any]) -> List[str]:
        """フェーズ要件をチェックして不足している要件を返す"""
        project_data = get_project(project_id, self.projects_dir)
        if not project_data:
            return ["プロジェクトが見つかりません"]
        
        missing = []
        
        # 必須フィールドチェック
        for field in requirements.get("required_fields", []):
            value = project_data.get(field)
            if not value or value == DEFAULT_UNDEF:
                missing.append(f"必須フィールド: {field}")
            elif field == "tasks" and not isinstance(value, list):
                missing.append(f"必須フィールド: {field} (リスト形式である必要があります)")
            elif field == "tasks" and len(value) == 0:
                missing.append(f"必須フィールド: {field} (最低1つのタスクが必要です)")
        
        # 必須アクションチェック
        for action in requirements.get("required_actions", []):
            if not self._check_action_completed(project_id, action):
                missing.append(f"必須アクション: {action}")
        
        return missing
    
    def _check_action_completed(self, project_id: str, action: str) -> bool:
        """特定のアクションが完了しているかチェック"""
        project_data = get_project(project_id, self.projects_dir)
        if not project_data:
            return False
        
        # チャーター作成チェック
        if action == "charter_created":
            # チャーターファイルの存在確認またはプロジェクトデータにチャーター情報があるかチェック
            charter_dir = Path("data/charters")
            charter_files = list(charter_dir.glob(f"*{project_id}*.yaml")) if charter_dir.exists() else []
            return len(charter_files) > 0 or project_data.get("charter_path") is not None
        
        # WBS作成チェック
        elif action == "wbs_created":
            tasks = project_data.get("tasks", [])
            return len(tasks) > 0
        
        # タイムライン定義チェック
        elif action == "timeline_defined":
            tasks = project_data.get("tasks", [])
            return any(task.get("due_date") for task in tasks if isinstance(task, dict))
        
        # タスク開始チェック
        elif action == "tasks_started":
            tasks = project_data.get("tasks", [])
            return any(task.get("status") not in [None, DEFAULT_UNDEF, ""] for task in tasks if isinstance(task, dict))
        
        # 成果物完成チェック
        elif action == "deliverables_completed":
            completion = project_data.get("completion_percentage", 0.0)
            # Safe conversion for completion percentage
            if isinstance(completion, str):
                try:
                    completion = float(completion)
                except (ValueError, TypeError):
                    completion = 0.0
            elif not isinstance(completion, (int, float)):
                completion = 0.0
            return completion >= 90.0
        
        return False
    
    def _record_phase_transition(self, project_id: str, from_phase: ProjectPhase, to_phase: ProjectPhase):
        """フェーズ遷移を履歴に記録"""
        try:
            # Read current project data
            if self.projects_dir:
                project_path = self.projects_dir / f"{project_id}.json"
            else:
                from .project_service import PROJECTS_DIR
                project_path = PROJECTS_DIR / f"{project_id}.json"
            
            if not project_path.exists():
                return
            
            # Read and update project data directly to avoid circular references
            import json
            with open(project_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Safe initialization for phase_history
            if "phase_history" not in data or not isinstance(data["phase_history"], list):
                data["phase_history"] = []
            
            data["phase_history"].append({
                "from_phase": from_phase.value,
                "to_phase": to_phase.value,
                "timestamp": datetime.utcnow().isoformat(),
                "type": "phase_transition"
            })
            
            # Safe initialization for change_log
            if "change_log" not in data or not isinstance(data["change_log"], list):
                data["change_log"] = []
            
            data["change_log"].append({
                "timestamp": datetime.utcnow().isoformat(),
                "type": "phase_advancement",
                "description": f"フェーズを {from_phase.value} から {to_phase.value} に進行",
                "source": "lifecycle_manager"
            })
            
            # Update timestamp
            data["updated_at"] = datetime.utcnow().isoformat()
            
            # Write back to file
            with open(project_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
        except Exception as e:
            logger.error("Error recording phase transition for project %s: %s", project_id, str(e))
    
    def _calculate_completion_percentage(self, phase: ProjectPhase) -> float:
        """フェーズに基づく完了率の概算計算"""
        phase_completion = {
            ProjectPhase.INCEPTION: 10.0,
            ProjectPhase.DEFINITION: 25.0,
            ProjectPhase.PLANNING: 40.0,
            ProjectPhase.EXECUTION: 70.0,
            ProjectPhase.MONITORING: 90.0,
            ProjectPhase.CLOSURE: 100.0
        }
        
        return phase_completion.get(phase, 0.0)