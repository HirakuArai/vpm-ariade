# --- core/project_diff.py ---
"""
Self-checker diff functionality for project snapshots
Enhanced with update candidate generation and chat content extraction
"""

import json
import re
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
from core.models import DEFAULT_UNDEF

PROJECTS_DIR = Path("data/projects")

def compare_snapshots(old_snapshot: Dict[str, Any], new_snapshot: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compare two project snapshots and return differences, ignoring __UNDEFINED__ values.
    
    Args:
        old_snapshot: Previous project state
        new_snapshot: Current project state
        
    Returns:
        Dictionary containing differences found
    """
    differences = {}
    
    # Get all keys from both snapshots
    all_keys = set(old_snapshot.keys()) | set(new_snapshot.keys())
    
    for key in all_keys:
        old_val = old_snapshot.get(key)
        new_val = new_snapshot.get(key)
        
        # Skip undefined fields as specified in the prompt
        if old_val == DEFAULT_UNDEF or new_val == DEFAULT_UNDEF:
            continue
        
        if old_val != new_val:
            differences[key] = {
                "old": old_val,
                "new": new_val
            }
    
    return differences

def check_project_changes(project_id: str, projects_dir: Path | None = None) -> Dict[str, Any]:
    """
    Check for changes in a project by comparing current state with previous snapshot.
    
    Args:
        project_id: Project identifier
        projects_dir: Directory containing project snapshots (defaults to PROJECTS_DIR)
        
    Returns:
        Change report with any differences found
    """
    if projects_dir is None:
        projects_dir = PROJECTS_DIR
        
    snapshot_path = projects_dir / f"{project_id}.json"
    
    if not snapshot_path.exists():
        return {"error": f"Project {project_id} not found"}
    
    try:
        with open(snapshot_path, 'r', encoding='utf-8') as f:
            current_snapshot = json.load(f)
        
        # For now, we just validate the snapshot is readable
        # In future, this could compare against a previous version
        return {
            "project_id": project_id,
            "status": "valid",
            "snapshot_valid": True,
            "has_undefined_fields": any(
                v == DEFAULT_UNDEF for v in current_snapshot.values()
            )
        }
        
    except Exception as e:
        return {
            "project_id": project_id,
            "error": f"Failed to read snapshot: {str(e)}"
        }

def generate_update_candidates(project_id: str, new_data_dict: Dict[str, Any], projects_dir: Path | None = None) -> List[Dict[str, Any]]:
    """
    Generate update candidates by comparing current project data with proposed new data.
    
    Args:
        project_id: The project identifier
        new_data_dict: Dictionary containing proposed new values
        projects_dir: Directory containing project files (defaults to PROJECTS_DIR)
    
    Returns:
        List of update candidates in format [{"field": str, "old": Any, "new": Any}]
    """
    if projects_dir is None:
        projects_dir = PROJECTS_DIR
        
    project_path = projects_dir / f"{project_id}.json"
    
    if not project_path.exists():
        raise FileNotFoundError(f"Project {project_id} not found")
    
    try:
        with open(project_path, 'r', encoding='utf-8') as f:
            current_data = json.load(f)
    except Exception as e:
        raise RuntimeError(f"Failed to read project {project_id}: {str(e)}")
    
    update_candidates = []
    
    # Compare each field in new_data_dict
    for field, new_value in new_data_dict.items():
        # Skip system fields that shouldn't be updated via diff
        if field in ["identifier", "uuid", "schema_version", "change_log"]:
            continue
        
        current_value = current_data.get(field, DEFAULT_UNDEF)
        
        # Treat DEFAULT_UNDEF as None for comparison purposes
        comparison_current = None if current_value == DEFAULT_UNDEF else current_value
        comparison_new = None if new_value == DEFAULT_UNDEF else new_value
        
        # Skip if values are identical
        if comparison_current == comparison_new:
            continue
        
        # Skip if new value is undefined (no meaningful update)
        if new_value == DEFAULT_UNDEF:
            continue
        
        
        # Create update candidate with old value converted to None if DEFAULT_UNDEF or missing
        candidate = {
            "field": field,
            "old": None if (current_value == DEFAULT_UNDEF or field not in current_data) else current_value,
            "new": new_value
        }
        
        # Validate the candidate before adding
        if validate_update_candidate(candidate):
            update_candidates.append(candidate)
    
    return update_candidates

def extract_new_data_from_chat(chat_content: str, project_id: str) -> Dict[str, Any]:
    """
    Extract structured data from chat content that could be used to update a project.
    
    Args:
        chat_content: Text content from chat/conversation
        project_id: The project identifier (for context)
    
    Returns:
        Dictionary with extracted fields and values
    """
    extracted_data = {}
    
    # Priority pattern: bare URLs (highest priority)
    bare_url_pattern = r"(https?://[^\s]+)"
    bare_urls = re.findall(bare_url_pattern, chat_content)
    if bare_urls:
        # Use the first URL found as repository_url
        extracted_data["repository_url"] = bare_urls[0]
    
    # Pattern matching for common project fields
    patterns = {
        "overview": [
            r"概要[：:]\s*(.+)",
            r"プロジェクト概要[：:]\s*(.+)",
            r"要約[：:]\s*(.+)",
            r"説明[：:]\s*(.+)"
        ],
        "status": [
            r"ステータス[：:]\s*([A-Z_]+)",
            r"状態[：:]\s*([A-Z_]+)",
            r"進捗[：:]\s*([A-Z_]+)",
            r"(?:アクティブ|active)"  # Added: non-capturing group for アクティブ|active
        ],
        "due_date": [
            r"期日(?:は)?\s*(\d{4}-\d{2}-\d{2})",  # Added: 期日は2024-12-31に pattern
            r"納期[：:]\s*(\d{4}-\d{2}-\d{2})",
            r"締切[：:]\s*(\d{4}-\d{2}-\d{2})",
            r"deadline\s*(\d{4}-\d{2}-\d{2})"  # Added: deadline pattern
        ],
        "budget": [
            r"予算[：:]\s*([\d,]+)\s*円",
            r"費用[：:]\s*([\d,]+)\s*円",
            r"コスト[：:]\s*([\d,]+)\s*円"
        ],
        "priority": [
            r"優先度[：:]\s*(HIGH|MEDIUM|LOW)",
            r"重要度[：:]\s*(HIGH|MEDIUM|LOW)"
        ],
        "repository_url": [
            r"リポジトリ[：:]\s*(https?://[^\s]+)",
            r"GitHub[：:]\s*(https?://[^\s]+)",
            r"repo[：:]\s*(https?://[^\s]+)"
        ]
    }
    
    # Apply pattern matching (but don't override bare URL if already found)
    for field, field_patterns in patterns.items():
        # Skip repository_url patterns if we already found a bare URL
        if field == "repository_url" and "repository_url" in extracted_data:
            continue
            
        for pattern in field_patterns:
            match = re.search(pattern, chat_content, re.IGNORECASE | re.MULTILINE)
            if match:
                # Special handling for status pattern that doesn't have capture group
                if field == "status" and pattern == r"(?:アクティブ|active)":
                    value = "ACTIVE"
                else:
                    value = match.group(1).strip()
                
                # Type conversion based on field
                if field in ["status", "priority"]:
                    value = value.upper()
                
                extracted_data[field] = value
                break  # Use first match for each field
    
    # Extract tasks from chat content
    task_patterns = [
        r"タスク[：:]\s*(.+)",
        r"作業[：:]\s*(.+)",
        r"TODO[：:]\s*(.+)"
    ]
    
    tasks = []
    for pattern in task_patterns:
        matches = re.findall(pattern, chat_content, re.IGNORECASE | re.MULTILINE)
        for match in matches:
            # Simple task parsing - each line is a task
            task_lines = [line.strip() for line in match.split('\n') if line.strip()]
            for task_line in task_lines:
                if task_line and len(task_line) > 3:  # Minimum meaningful task length
                    tasks.append({
                        "description": task_line,
                        "due_date": DEFAULT_UNDEF,
                        "owner": DEFAULT_UNDEF,
                        "status": DEFAULT_UNDEF
                    })
    
    if tasks:
        extracted_data["tasks"] = tasks
    
    # Extract tags
    tag_pattern = r"#(\w+)"
    tags = re.findall(tag_pattern, chat_content)
    if tags:
        extracted_data["tags"] = list(set(tags))  # Remove duplicates
    
    return extracted_data

def generate_diff_summary(update_candidates: List[Dict[str, Any]]) -> str:
    """
    Generate a human-readable summary of update candidates.
    
    Args:
        update_candidates: List of update candidates
    
    Returns:
        Formatted summary string
    """
    if not update_candidates:
        return "変更候補はありません。"
    
    summary_lines = [
        f"{len(update_candidates)} 件の更新候補があります",
        ""
    ]
    
    # Group changes by type
    field_groups = {
        "基本情報": ["overview", "status", "priority"],
        "スケジュール": ["due_date", "created_at", "updated_at"],
        "リソース": ["budget", "repository_url", "created_by"],
        "タスク": ["tasks"],
        "その他": []
    }
    
    # Categorize candidates
    categorized = {group: [] for group in field_groups}
    for candidate in update_candidates:
        field = candidate["field"]
        categorized_flag = False
        
        for group, fields in field_groups.items():
            if field in fields:
                categorized[group].append(candidate)
                categorized_flag = True
                break
        
        if not categorized_flag:
            categorized["その他"].append(candidate)
    
    # Generate summary by category
    for group, candidates in categorized.items():
        if not candidates:
            continue
        
        summary_lines.append(f"## {group}")
        
        for candidate in candidates:
            field = candidate["field"]
            old_val = candidate["old"]
            new_val = candidate["new"]
            
            # Format values for display
            old_display = _format_value_for_display(old_val)
            new_display = _format_value_for_display(new_val)
            
            # Translate field names to Japanese
            field_japanese = {
                "overview": "概要",
                "status": "ステータス",
                "priority": "優先度",
                "due_date": "期日",
                "budget": "予算",
                "repository_url": "リポジトリURL",
                "created_by": "作成者",
                "tasks": "タスク",
                "tags": "タグ"
            }.get(field, field)
            
            summary_lines.append(f"- **{field_japanese}**: {old_display} → {new_display}")
        
        summary_lines.append("")
    
    # Add validation warnings
    invalid_candidates = [c for c in update_candidates if not validate_update_candidate(c)]
    if invalid_candidates:
        summary_lines.extend([
            "⚠️ **検証エラー**",
            f"{len(invalid_candidates)} 件の無効な更新候補が検出されました。",
            ""
        ])
    
    return "\n".join(summary_lines)

def validate_update_candidate(candidate: Dict[str, Any]) -> bool:
    """
    Validate an update candidate for correctness and safety.
    
    Args:
        candidate: Update candidate dictionary
    
    Returns:
        True if valid, False otherwise
    """
    # Check required fields
    required_fields = ["field", "old", "new"]
    for field in required_fields:
        if field not in candidate:
            return False
    
    field = candidate["field"]
    old_val = candidate["old"]
    new_val = candidate["new"]
    
    # Reject system/protected fields
    protected_fields = [
        "identifier", "uuid", "schema_version", "change_log", 
        "created_at"  # created_at should not be changed after creation
    ]
    if field in protected_fields:
        return False
    
    # Validate field-specific constraints
    if field == "status":
        valid_statuses = ["DRAFT", "ACTIVE", "ON_HOLD", "COMPLETED", "CANCELLED"]
        if new_val not in valid_statuses:
            return False
    
    elif field == "priority":
        valid_priorities = ["HIGH", "MEDIUM", "LOW"]
        if new_val not in valid_priorities:
            return False
    
    elif field == "due_date":
        # Basic date format validation
        if isinstance(new_val, str) and new_val != DEFAULT_UNDEF:
            try:
                datetime.fromisoformat(new_val.replace('Z', '+00:00'))
            except ValueError:
                # Try simple YYYY-MM-DD format
                try:
                    datetime.strptime(new_val, "%Y-%m-%d")
                except ValueError:
                    return False
    
    elif field == "budget":
        # Accept both int/float and string numbers
        if isinstance(new_val, str) and new_val.isdigit():
            return True  # String numbers are valid
        elif not isinstance(new_val, (int, float)) or new_val < 0:
            return False
    
    elif field == "repository_url":
        if isinstance(new_val, str) and new_val != DEFAULT_UNDEF:
            if not new_val.startswith(("http://", "https://")):
                return False
    
    elif field == "tasks":
        if not isinstance(new_val, list):
            return False
        
        # Validate each task structure
        for task in new_val:
            if not isinstance(task, dict):
                return False
            if "description" not in task:
                return False
    
    # Check that old and new values are different (treating DEFAULT_UNDEF as None)
    comparison_old = None if old_val == DEFAULT_UNDEF else old_val
    comparison_new = None if new_val == DEFAULT_UNDEF else new_val
    if comparison_old == comparison_new:
        return False
    
    # Don't allow updating to undefined
    if new_val == DEFAULT_UNDEF:
        return False
    
    return True

def _format_value_for_display(value: Any) -> str:
    """
    Format a value for human-readable display.
    
    Args:
        value: Value to format
    
    Returns:
        Formatted string representation
    """
    if value == DEFAULT_UNDEF or value is None:
        return "（未設定）"
    elif isinstance(value, list):
        if not value:
            return "（空のリスト）"
        elif len(value) <= 3:
            return f"[{', '.join(str(v) for v in value)}]"
        else:
            return f"[{', '.join(str(v) for v in value[:3])}... +{len(value)-3}件]"
    elif isinstance(value, dict):
        return f"{{...}} ({len(value)}個のフィールド)"
    elif isinstance(value, str) and len(value) > 50:
        return f"{value[:47]}..."
    else:
        return str(value)

def apply_update_candidates(project_id: str, update_candidates: List[Dict[str, Any]], projects_dir: Path | None = None) -> Dict[str, Any]:
    """
    Apply validated update candidates to a project.
    
    Args:
        project_id: The project identifier
        update_candidates: List of validated update candidates
        projects_dir: Directory containing project files (defaults to PROJECTS_DIR)
    
    Returns:
        Result dictionary with success status and details
    """
    if projects_dir is None:
        projects_dir = PROJECTS_DIR
        
    project_path = projects_dir / f"{project_id}.json"
    
    if not project_path.exists():
        return {"success": False, "error": f"Project {project_id} not found"}
    
    # Validate all candidates first
    invalid_candidates = [c for c in update_candidates if not validate_update_candidate(c)]
    if invalid_candidates:
        return {
            "success": False, 
            "error": f"{len(invalid_candidates)} invalid update candidates",
            "invalid_candidates": invalid_candidates
        }
    
    try:
        # Load current project data
        with open(project_path, 'r', encoding='utf-8') as f:
            project_data = json.load(f)
        
        # Safe initialization for corrupted fields
        if "tasks" not in project_data or isinstance(project_data["tasks"], str):
            project_data["tasks"] = []
        if "change_log" not in project_data or isinstance(project_data["change_log"], str):
            project_data["change_log"] = []
        
        # Apply updates
        applied_updates = []
        for candidate in update_candidates:
            field = candidate["field"]
            old_val = candidate["old"]
            new_val = candidate["new"]
            
            # Verify old value matches (safety check) - handle None comparison for DEFAULT_UNDEF
            current_val = project_data.get(field, DEFAULT_UNDEF)
            comparison_current = None if (current_val == DEFAULT_UNDEF or current_val is None) else current_val
            comparison_old = None if (old_val == DEFAULT_UNDEF or old_val is None) else old_val
            
            if comparison_current != comparison_old:
                continue  # Skip this update due to value mismatch
            
            # Apply the update
            project_data[field] = new_val
            applied_updates.append(field)
        
        # Update timestamp and add change log
        if applied_updates:
            project_data["updated_at"] = datetime.utcnow().isoformat()
            
            project_data["change_log"].append({
                "timestamp": datetime.utcnow().isoformat(),
                "type": "diff_updates_applied",
                "fields_updated": applied_updates,
                "source": "project_diff_engine"
            })
        
        # Save updated project
        with open(project_path, 'w', encoding='utf-8') as f:
            json.dump(project_data, f, indent=2, ensure_ascii=False)
        
        return {
            "success": True,
            "updates_applied": len(applied_updates),
            "fields_updated": applied_updates
        }
        
    except Exception as e:
        return {"success": False, "error": f"Failed to apply updates: {str(e)}"}