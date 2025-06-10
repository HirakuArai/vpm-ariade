import json
import time
from datetime import datetime
from pathlib import Path
from typing import Optional
from .models import Project

PROJECTS_DIR = Path("data/projects")
PROJECTS_DIR.mkdir(parents=True, exist_ok=True)

def _autogen_id() -> str:
    """Generate unique project ID with format proj-YYYYMMDD-HHMMSS"""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    # Add microseconds to ensure uniqueness within same second
    microseconds = str(int(time.time() * 1000000) % 1000000).zfill(6)
    return f"proj-{timestamp}-{microseconds[:3]}"

def create_project(identifier: Optional[str], overview: str, created_by: str) -> Project:
    """Create a new Project instance, save snapshot, and return it (idempotent)."""
    # Auto-generate identifier if None
    if identifier is None:
        identifier = _autogen_id()
        # Ensure uniqueness by checking if file exists
        while (PROJECTS_DIR / f"{identifier}.json").exists():
            identifier = _autogen_id()
    
    path = PROJECTS_DIR / f"{identifier}.json"
    if path.exists():
        return Project(**json.loads(path.read_text()))
    project = Project(identifier=identifier, overview=overview, created_by=created_by)
    path.write_text(json.dumps(project.to_dict(), indent=2))
    return project

def set_status(identifier: str, status: str):
    """Update project status and timestamp"""
    path = PROJECTS_DIR / f"{identifier}.json"
    if not path.exists():
        raise FileNotFoundError(f"Project {identifier} not found")
    
    data = json.loads(path.read_text())
    data["status"] = status
    data["updated_at"] = datetime.utcnow().isoformat()
    path.write_text(json.dumps(data, indent=2))