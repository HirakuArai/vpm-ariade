"""
Memory Bridge: Memory Layer Phase 2 Implementation
Lv2 常駐メモリ + イベントログ管理
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

from config import get_memory_config, is_memory_enabled

logger = logging.getLogger(__name__)

class MemoryBridge:
    """Memory Layer Phase 2 - Bridge for memory operations"""
    
    def __init__(self):
        """Initialize memory bridge"""
        self.config = get_memory_config()
        self.repo_path = Path(self.config["memory_repo_path"])
        self.current_memory_path = self.repo_path / self.config["current_memory_file"]
        self.events_dir = self.repo_path / self.config["events_dir"]
        self.schema_path = self.repo_path / self.config["schema_dir"] / "lv2_schema.json"
        
        # Initialize directories
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Ensure required directories exist"""
        self.repo_path.mkdir(exist_ok=True)
        self.events_dir.mkdir(exist_ok=True)
        (self.repo_path / self.config["snapshots_dir"]).mkdir(exist_ok=True)
        (self.repo_path / self.config["schema_dir"]).mkdir(exist_ok=True)
    
    def load_current_memory(self) -> Dict[str, Any]:
        """Load current memory state"""
        # Check both global setting and instance config (for beta override)
        if not (is_memory_enabled() or self.config.get("enabled", False)):
            return self._get_empty_memory()
        
        try:
            if self.current_memory_path.exists():
                with open(self.current_memory_path, 'r', encoding='utf-8') as f:
                    memory = json.load(f)
                return memory
            else:
                return self._get_empty_memory()
        except Exception as e:
            logger.error(f"Failed to load memory: {e}")
            return self._get_empty_memory()
    
    def save_current_memory(self, memory: Dict[str, Any]) -> bool:
        """Save current memory state"""
        # Check both global setting and instance config (for beta override)
        if not (is_memory_enabled() or self.config.get("enabled", False)):
            return False
        
        try:
            # Update timestamp
            memory["last_updated"] = datetime.now(timezone.utc).isoformat()
            
            # Backup existing memory if enabled
            if self.config["backup_before_write"] and self.current_memory_path.exists():
                backup_path = self.current_memory_path.with_suffix('.json.backup')
                backup_path.write_text(self.current_memory_path.read_text())
            
            # Validate schema if enabled
            if self.config["validate_schema"]:
                self._validate_memory_schema(memory)
            
            # Save memory
            with open(self.current_memory_path, 'w', encoding='utf-8') as f:
                json.dump(memory, f, ensure_ascii=False, indent=2)
            
            logger.info("Memory saved successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to save memory: {e}")
            return False
    
    def log_event(self, event_type: str, description: str, project_id: Optional[str] = None, 
                  importance: str = "medium", metadata: Optional[Dict] = None) -> bool:
        """Log an event to memory"""
        # Check both global setting and instance config (for beta override)
        if not (is_memory_enabled() or self.config.get("enabled", False)):
            return False
        
        try:
            # Create event entry
            event = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "event_type": event_type,
                "description": description,
                "importance": importance
            }
            
            if project_id:
                event["project_id"] = project_id
            if metadata:
                event["metadata"] = metadata
            
            # Log to events file
            self._log_to_events_file(event)
            
            # Update current memory with event
            memory = self.load_current_memory()
            memory["events"].append(event)
            
            # Keep only recent events in memory (last 50)
            memory["events"] = memory["events"][-50:]
            
            # Save updated memory
            return self.save_current_memory(memory)
        except Exception as e:
            logger.error(f"Failed to log event: {e}")
            return False
    
    def update_project_context(self, project_id: str, name: str, status: str, 
                             key_context: Optional[str] = None) -> bool:
        """Update project context in memory"""
        # Check both global setting and instance config (for beta override)
        if not (is_memory_enabled() or self.config.get("enabled", False)):
            return False
        
        try:
            memory = self.load_current_memory()
            active_projects = memory["current_memory"]["active_projects"]
            
            # Find existing project or create new
            project_found = False
            for project in active_projects:
                if project["project_id"] == project_id:
                    project["name"] = name
                    project["status"] = status
                    project["last_interaction"] = datetime.now(timezone.utc).isoformat()
                    if key_context:
                        project["key_context"] = key_context
                    project_found = True
                    break
            
            if not project_found:
                new_project = {
                    "project_id": project_id,
                    "name": name,
                    "status": status,
                    "last_interaction": datetime.now(timezone.utc).isoformat()
                }
                if key_context:
                    new_project["key_context"] = key_context
                active_projects.append(new_project)
            
            # Keep only active projects (last 10)
            memory["current_memory"]["active_projects"] = active_projects[-10:]
            
            return self.save_current_memory(memory)
        except Exception as e:
            logger.error(f"Failed to update project context: {e}")
            return False
    
    def get_context_for_ai(self, max_events: int = 10) -> str:
        """Get formatted context for AI"""
        # Check both global setting and instance config (for beta override)
        if not (is_memory_enabled() or self.config.get("enabled", False)):
            return ""
        
        try:
            memory = self.load_current_memory()
            context_parts = []
            
            # Active projects
            active_projects = memory["current_memory"]["active_projects"]
            if active_projects:
                context_parts.append("## アクティブプロジェクト")
                for project in active_projects[-5:]:  # Last 5 projects
                    context_parts.append(f"- {project['name']} ({project['project_id']}): {project['status']}")
            
            # Recent events
            recent_events = memory["events"][-max_events:]
            if recent_events:
                context_parts.append("\n## 最近のイベント")
                for event in recent_events:
                    timestamp = event["timestamp"][:16].replace('T', ' ')  # Format: YYYY-MM-DD HH:MM
                    context_parts.append(f"- [{timestamp}] {event['description']}")
            
            # Session context
            session = memory["current_memory"]["session_context"]
            if session.get("current_focus"):
                context_parts.append(f"\n## 現在の焦点: {session['current_focus']}")
            
            return "\n".join(context_parts)
        except Exception as e:
            logger.error(f"Failed to get context for AI: {e}")
            return ""
    
    def _get_empty_memory(self) -> Dict[str, Any]:
        """Get empty memory structure"""
        return {
            "memory_version": "2.0",
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "current_memory": {
                "active_projects": [],
                "user_preferences": {
                    "language": "ja",
                    "communication_style": "professional",
                    "project_templates": []
                },
                "session_context": {
                    "current_focus": "",
                    "recent_topics": [],
                    "pending_actions": []
                }
            },
            "events": []
        }
    
    def _log_to_events_file(self, event: Dict[str, Any]):
        """Log event to daily events file"""
        today = datetime.now().strftime("%Y-%m")
        daily_file = self.events_dir / f"{today}" / f"{datetime.now().strftime('%d')}.log"
        
        # Ensure daily directory exists
        daily_file.parent.mkdir(exist_ok=True)
        
        # Append event to daily log
        with open(daily_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(event, ensure_ascii=False) + '\n')
    
    def _validate_memory_schema(self, memory: Dict[str, Any]):
        """Validate memory against schema (basic validation)"""
        required_fields = ["memory_version", "last_updated", "current_memory", "events"]
        for field in required_fields:
            if field not in memory:
                raise ValueError(f"Missing required field: {field}")
        
        if memory["memory_version"] != "2.0":
            raise ValueError(f"Invalid memory version: {memory['memory_version']}")

# Global instance
memory_bridge = MemoryBridge()

# Convenience functions
def log_event(event_type: str, description: str, project_id: Optional[str] = None, 
              importance: str = "medium", metadata: Optional[Dict] = None) -> bool:
    """Log an event to memory (convenience function)"""
    return memory_bridge.log_event(event_type, description, project_id, importance, metadata)

def update_project_context(project_id: str, name: str, status: str, 
                         key_context: Optional[str] = None) -> bool:
    """Update project context (convenience function)"""
    return memory_bridge.update_project_context(project_id, name, status, key_context)

def get_context_for_ai(max_events: int = 10) -> str:
    """Get context for AI (convenience function)"""
    return memory_bridge.get_context_for_ai(max_events)

def load_current_memory() -> Dict[str, Any]:
    """Load current memory (convenience function)"""
    return memory_bridge.load_current_memory()