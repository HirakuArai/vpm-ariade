"""
Self-checker diff functionality for project snapshots
"""

import json
from typing import Dict, Any, List
from pathlib import Path
from core.models import DEFAULT_UNDEF

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

def check_project_changes(project_id: str, projects_dir: Path = None) -> Dict[str, Any]:
    """
    Check for changes in a project by comparing current state with previous snapshot.
    
    Args:
        project_id: Project identifier
        projects_dir: Directory containing project snapshots
        
    Returns:
        Change report with any differences found
    """
    if projects_dir is None:
        projects_dir = Path("data/projects")
    
    snapshot_path = projects_dir / f"{project_id}.json"
    
    if not snapshot_path.exists():
        return {"error": f"Project {project_id} not found"}
    
    try:
        with open(snapshot_path, 'r') as f:
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