# --- core/project_service.py ---
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from .models import Project, DEFAULT_UNDEF

logger = logging.getLogger(__name__)

PROJECTS_DIR = Path("data/projects")
PROJECTS_DIR.mkdir(parents=True, exist_ok=True)

def _autogen_id() -> str:
    """Generate unique project ID with format proj-YYYYMMDD-HHMMSS"""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    # Add microseconds to ensure uniqueness within same second
    microseconds = str(int(time.time() * 1000000) % 1000000).zfill(6)
    return f"proj-{timestamp}-{microseconds[:3]}"

def create_project(identifier: Optional[str], overview: str, created_by: str, display_name: Optional[str] = None, projects_dir: Path | None = None) -> Project:
    """Create a new Project instance, save snapshot, and return it (idempotent)."""
    if projects_dir is None:
        projects_dir = PROJECTS_DIR
    
    # Auto-generate identifier if None
    if identifier is None:
        identifier = _autogen_id()
        # Ensure uniqueness by checking if file exists
        while (projects_dir / f"{identifier}.json").exists():
            identifier = _autogen_id()
    
    path = projects_dir / f"{identifier}.json"
    if path.exists():
        return Project(**json.loads(path.read_text()))
    # Set display_name from parameter or fallback to overview
    if display_name is None:
        display_name = overview
    project = Project(identifier=identifier, overview=overview, display_name=display_name, created_by=created_by)
    path.write_text(json.dumps(project.to_dict(), indent=2))
    return project

def set_status(identifier: str, status: str, projects_dir: Path | None = None):
    """Update project status and timestamp"""
    if projects_dir is None:
        projects_dir = PROJECTS_DIR
        
    path = projects_dir / f"{identifier}.json"
    if not path.exists():
        raise FileNotFoundError(f"Project {identifier} not found")
    
    data = json.loads(path.read_text())
    data["status"] = status
    data["updated_at"] = datetime.utcnow().isoformat()
    path.write_text(json.dumps(data, indent=2))

def add_task(project_id: str, description: str, due_date: str, owner: str = "human_user", projects_dir: Path | None = None) -> dict:
    """Add a task to a project with sequential ID"""
    if projects_dir is None:
        projects_dir = PROJECTS_DIR
        
    path = projects_dir / f"{project_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"Project {project_id} not found")
    
    data = json.loads(path.read_text())
    
    # Ensure tasks field exists and is a list (fix for corrupted data)
    if "tasks" not in data or isinstance(data["tasks"], str):
        data["tasks"] = []
    
    # Generate sequential task ID
    task_id = len(data["tasks"]) + 1
    
    # Create new task with proper defaults
    new_task = {
        "id": task_id,
        "description": description,
        "due_date": due_date,
        "owner": owner if owner != DEFAULT_UNDEF else "human_user",
        "status": "pending"
    }
    
    # Add task and update timestamp
    data["tasks"].append(new_task)
    from zoneinfo import ZoneInfo
    jst = ZoneInfo("Asia/Tokyo")
    data["updated_at"] = datetime.now(jst).isoformat()
    
    # Save updated project with proper encoding
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    
    return new_task

def remove_task(project_id: str, task_id: int, projects_dir: Path | None = None) -> bool:
    """Remove a task from a project by task ID"""
    if projects_dir is None:
        projects_dir = PROJECTS_DIR
        
    path = projects_dir / f"{project_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"Project {project_id} not found")
    
    data = json.loads(path.read_text())
    
    # Ensure tasks field exists
    if "tasks" not in data or not isinstance(data["tasks"], list):
        return False
    
    # Find and remove task with matching ID
    original_count = len(data["tasks"])
    data["tasks"] = [task for task in data["tasks"] if task.get("id") != task_id]
    
    if len(data["tasks"]) == original_count:
        return False  # Task not found
    
    # Update timestamp
    data["updated_at"] = datetime.utcnow().isoformat()
    
    # Save updated project
    path.write_text(json.dumps(data, indent=2))
    
    return True

def remove_duplicate_tasks(project_id: str, projects_dir: Path | None = None) -> int:
    """Remove duplicate tasks based on description and due_date"""
    if projects_dir is None:
        projects_dir = PROJECTS_DIR
        
    path = projects_dir / f"{project_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"Project {project_id} not found")
    
    data = json.loads(path.read_text())
    
    # Ensure tasks field exists
    if "tasks" not in data or not isinstance(data["tasks"], list):
        return 0
    
    # Track unique tasks by (description, due_date)
    seen = set()
    unique_tasks = []
    removed_count = 0
    
    for task in data["tasks"]:
        key = (task.get("description", ""), task.get("due_date", ""))
        if key not in seen:
            seen.add(key)
            unique_tasks.append(task)
        else:
            removed_count += 1
    
    # Update tasks list if duplicates were found
    if removed_count > 0:
        data["tasks"] = unique_tasks
        # Reassign sequential IDs
        for i, task in enumerate(data["tasks"], 1):
            task["id"] = i
        
        data["updated_at"] = datetime.utcnow().isoformat()
        path.write_text(json.dumps(data, indent=2))
    
    return removed_count

def get_project(project_id: str, projects_dir: Path | None = None) -> Optional[Dict[str, Any]]:
    """
    Get project data by ID.
    
    Args:
        project_id: The project identifier
        projects_dir: Directory containing project files (defaults to PROJECTS_DIR)
    
    Returns:
        Project data dictionary or None if not found
    """
    if projects_dir is None:
        projects_dir = PROJECTS_DIR
        
    path = projects_dir / f"{project_id}.json"
    if not path.exists():
        return None
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None

def update_project_field(project_id: str, field: str, value: Any, projects_dir: Path | None = None) -> bool:
    """
    Update a single field in a project.
    
    Args:
        project_id: The project identifier
        field: Field name to update
        value: New value for the field
        projects_dir: Directory containing project files (defaults to PROJECTS_DIR)
    
    Returns:
        True if successful, False otherwise
    """
    if projects_dir is None:
        projects_dir = PROJECTS_DIR
        
    path = projects_dir / f"{project_id}.json"
    if not path.exists():
        return False
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        data[field] = value
        data["updated_at"] = datetime.utcnow().isoformat()
        
        # Add change log entry with safe initialization
        if "change_log" not in data or isinstance(data["change_log"], str):
            data["change_log"] = []
        
        data["change_log"].append({
            "timestamp": datetime.utcnow().isoformat(),
            "type": "field_update",
            "field": field,
            "new_value": value,
            "source": "project_service"
        })
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return True
        
    except Exception as e:
        logger.error("Error updating field %s for project %s: %s", field, project_id, str(e))
        return False

def merge_updates(project_id: str, update_candidates: List[Dict[str, Any]], projects_dir: Path | None = None) -> bool:
    """
    Apply update candidates to a project JSON file.
    
    Args:
        project_id: The project identifier
        update_candidates: List of updates in format [{"field": str, "old": Any, "new": Any}]
        projects_dir: Directory containing project files (defaults to PROJECTS_DIR)
    
    Returns:
        True if successful, False otherwise
    """
    if projects_dir is None:
        projects_dir = PROJECTS_DIR
        
    path = projects_dir / f"{project_id}.json"
    if not path.exists():
        return False
    
    try:
        # Load current project data
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Safe initialization for corrupted fields
        if "tasks" not in data or isinstance(data["tasks"], str):
            data["tasks"] = []
        if "change_log" not in data or isinstance(data["change_log"], str):
            data["change_log"] = []
        
        # Apply each update candidate
        updates_applied = []
        for candidate in update_candidates:
            field = candidate["field"]
            old_value = candidate["old"]
            new_value = candidate["new"]
            
            # Verify old value matches current value (for safety)
            current_value = data.get(field)
            if current_value != old_value:
                # Log the mismatch but continue with other updates
                logger.warning("Field '%s' current value '%s' doesn't match expected old value '%s'", field, current_value, old_value)
                continue
            
            # Apply the update
            data[field] = new_value
            updates_applied.append(field)
        
        # Update timestamp if any changes were made
        if updates_applied:
            data["updated_at"] = datetime.utcnow().isoformat()
            
            data["change_log"].append({
                "timestamp": datetime.utcnow().isoformat(),
                "type": "update_candidates_applied",
                "fields_updated": updates_applied,
                "source": "diff_proposal_ui"
            })
        
        # Save updated data
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return True
        
    except Exception as e:
        logger.error("Error merging updates for project %s: %s", project_id, str(e))
        return False

def apply_updates(project_id: str, update_candidates: List[Dict[str, Any]], projects_dir: Path | None = None) -> Dict[str, Any]:
    """
    Apply updates and optionally commit to git (PoC implementation).
    
    Args:
        project_id: The project identifier
        update_candidates: List of updates to apply
        projects_dir: Directory containing project files (defaults to PROJECTS_DIR)
    
    Returns:
        Dictionary with operation result
    """
    if projects_dir is None:
        projects_dir = PROJECTS_DIR
        
    try:
        # Apply the updates
        success = merge_updates(project_id, update_candidates, projects_dir)
        
        if not success:
            return {"success": False, "error": "Failed to merge updates"}
        
        return {
            "success": True,
            "updates_applied": len(update_candidates),
            "git_committed": False
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}

def list_projects(projects_dir: Path | None = None) -> List[Dict[str, Any]]:
    """
    List all projects with their basic information.
    
    Args:
        projects_dir: Directory containing project files (defaults to PROJECTS_DIR)
    
    Returns:
        List of project summary dictionaries
    """
    if projects_dir is None:
        projects_dir = PROJECTS_DIR
        
    if not projects_dir.exists():
        return []
    
    projects = []
    for project_file in projects_dir.glob("*.json"):
        try:
            with open(project_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            projects.append({
                "identifier": data.get("identifier", project_file.stem),
                "overview": data.get("overview", "概要なし"),
                "status": data.get("status", "DRAFT"),
                "created_by": data.get("created_by", DEFAULT_UNDEF),
                "created_at": data.get("created_at"),
                "updated_at": data.get("updated_at"),
                "task_count": len(data.get("tasks", []))
            })
        except Exception as e:
            logger.error("Error reading project file %s: %s", project_file, str(e))
            continue
    
    # Sort by modification time (most recent first)
    projects.sort(key=lambda x: x.get("updated_at", x.get("created_at", "")), reverse=True)
    return projects

def delete_project(project_id: str, projects_dir: Path | None = None) -> bool:
    """
    Delete a project file.
    
    Args:
        project_id: The project identifier
        projects_dir: Directory containing project files (defaults to PROJECTS_DIR)
    
    Returns:
        True if successful, False otherwise
    """
    if projects_dir is None:
        projects_dir = PROJECTS_DIR
        
    path = projects_dir / f"{project_id}.json"
    if not path.exists():
        return False
    
    try:
        path.unlink()
        return True
    except Exception as e:
        logger.error("Error deleting project %s: %s", project_id, str(e))
        return False

def update_task_status(project_id: str, task_id: int, status: str, projects_dir: Path | None = None) -> bool:
    """
    Update the status of a specific task in a project.
    
    Args:
        project_id: The project identifier
        task_id: The task ID
        status: New status for the task
        projects_dir: Directory containing project files (defaults to PROJECTS_DIR)
    
    Returns:
        True if successful, False otherwise
    """
    if projects_dir is None:
        projects_dir = PROJECTS_DIR
        
    path = projects_dir / f"{project_id}.json"
    if not path.exists():
        return False
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Safe initialization for corrupted tasks
        if "tasks" not in data or isinstance(data["tasks"], str):
            data["tasks"] = []
        
        # Find and update the task
        tasks = data["tasks"]
        for task in tasks:
            if task.get("id") == task_id:
                task["status"] = status
                break
        else:
            return False  # Task not found
        
        # Update timestamp
        data["updated_at"] = datetime.utcnow().isoformat()
        
        # Add change log entry with safe initialization
        if "change_log" not in data or isinstance(data["change_log"], str):
            data["change_log"] = []
        
        data["change_log"].append({
            "timestamp": datetime.utcnow().isoformat(),
            "type": "task_status_update",
            "task_id": task_id,
            "new_status": status,
            "source": "project_service"
        })
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return True
        
    except Exception as e:
        logger.error("Error updating task %s status for project %s: %s", task_id, project_id, str(e))
        return False

def clean_meaningless_tasks(project_id: str, projects_dir: Path | None = None) -> int:
    """
    無意味なタスクを自動削除
    
    Args:
        project_id: プロジェクトID
        projects_dir: プロジェクトディレクトリ
        
    Returns:
        削除されたタスク数
    """
    if projects_dir is None:
        projects_dir = PROJECTS_DIR
        
    path = projects_dir / f"{project_id}.json"
    if not path.exists():
        return 0
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if "tasks" not in data or not isinstance(data["tasks"], list):
            return 0
        
        # 無意味なタスクのパターン
        meaningless_patterns = [
            "新しいタスク",
            "タスクの削除", 
            "タスクを追加",
            "設計タスクを追加",
            "作業内容を明確化"
        ]
        
        original_count = len(data["tasks"])
        
        # 無意味なタスクを除外
        data["tasks"] = [
            task for task in data["tasks"] 
            if not any(pattern in task.get("description", "") for pattern in meaningless_patterns)
        ]
        
        removed_count = original_count - len(data["tasks"])
        
        if removed_count > 0:
            # タスクIDを再振り番
            for i, task in enumerate(data["tasks"], 1):
                task["id"] = i
            
            # JST タイムゾーンで更新時刻を設定
            from zoneinfo import ZoneInfo
            jst = ZoneInfo("Asia/Tokyo")
            data["updated_at"] = datetime.now(jst).isoformat()
            
            # 変更ログを追加
            if "change_log" not in data or isinstance(data["change_log"], str):
                data["change_log"] = []
            
            data["change_log"].append({
                "timestamp": datetime.now(jst).isoformat(),
                "type": "meaningless_task_cleanup",
                "description": f"無意味なタスク {removed_count} 件を自動削除",
                "source": "project_service"
            })
            
            # ファイルを保存
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        
        return removed_count
        
    except Exception as e:
        logger.error("Error cleaning meaningless tasks for project %s: %s", project_id, str(e))
        return 0