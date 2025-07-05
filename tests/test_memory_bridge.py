"""
Unit tests for Memory Bridge (Memory Layer Phase 2)
メモリブリッジのテスト
"""

import json
import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock

# Import the module under test
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.memory_bridge import MemoryBridge, log_event, update_project_context
from config import get_memory_config


class TestMemoryBridge(unittest.TestCase):
    """Memory Bridge unit tests"""
    
    def setUp(self):
        """Set up test environment"""
        # Create temporary directory for test
        self.test_dir = tempfile.mkdtemp()
        self.original_config = get_memory_config()
        
        # Mock memory config to use test directory
        self.test_config = self.original_config.copy()
        self.test_config["memory_repo_path"] = self.test_dir
        
        # Patch config functions
        self.config_patcher = patch('core.memory_bridge.get_memory_config', return_value=self.test_config)
        self.enabled_patcher = patch('core.memory_bridge.is_memory_enabled', return_value=True)
        
        self.config_patcher.start()
        self.enabled_patcher.start()
        
        # Create memory bridge instance
        self.memory_bridge = MemoryBridge()
        
    def tearDown(self):
        """Clean up test environment"""
        self.config_patcher.stop()
        self.enabled_patcher.stop()
        
        # Clean up test directory
        import shutil
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_init_creates_directories(self):
        """Test that initialization creates required directories"""
        expected_dirs = [
            Path(self.test_dir),
            Path(self.test_dir) / "events",
            Path(self.test_dir) / "snapshots", 
            Path(self.test_dir) / "schema"
        ]
        
        for dir_path in expected_dirs:
            self.assertTrue(dir_path.exists(), f"Directory {dir_path} should exist")
    
    def test_load_current_memory_empty(self):
        """Test loading memory when no file exists"""
        memory = self.memory_bridge.load_current_memory()
        
        # Should return empty memory structure
        self.assertEqual(memory["memory_version"], "2.0")
        self.assertIn("current_memory", memory)
        self.assertIn("events", memory)
        self.assertEqual(memory["events"], [])
        self.assertEqual(memory["current_memory"]["active_projects"], [])
    
    def test_save_and_load_memory(self):
        """Test saving and loading memory"""
        # Create test memory
        test_memory = {
            "memory_version": "2.0",
            "last_updated": "2025-07-05T16:00:00Z",
            "current_memory": {
                "active_projects": [{
                    "project_id": "test_project",
                    "name": "Test Project",
                    "status": "active"
                }],
                "user_preferences": {
                    "language": "ja"
                },
                "session_context": {
                    "current_focus": "testing"
                }
            },
            "events": []
        }
        
        # Save memory
        result = self.memory_bridge.save_current_memory(test_memory)
        self.assertTrue(result, "Save should succeed")
        
        # Load memory back
        loaded_memory = self.memory_bridge.load_current_memory()
        
        # Verify content (excluding timestamp which gets updated)
        self.assertEqual(loaded_memory["memory_version"], test_memory["memory_version"])
        self.assertEqual(loaded_memory["current_memory"], test_memory["current_memory"])
        self.assertEqual(loaded_memory["events"], test_memory["events"])
        
    def test_log_event(self):
        """Test logging events"""
        # Log an event
        result = self.memory_bridge.log_event(
            event_type="user_message",
            description="Test message",
            project_id="test_project",
            importance="medium"
        )
        
        self.assertTrue(result, "Event logging should succeed")
        
        # Load memory and check event was added
        memory = self.memory_bridge.load_current_memory()
        events = memory["events"]
        
        self.assertEqual(len(events), 1)
        event = events[0]
        self.assertEqual(event["event_type"], "user_message")
        self.assertEqual(event["description"], "Test message")
        self.assertEqual(event["project_id"], "test_project")
        self.assertEqual(event["importance"], "medium")
        self.assertIn("timestamp", event)
    
    def test_log_event_creates_daily_file(self):
        """Test that logging creates daily event files"""
        # Log an event
        self.memory_bridge.log_event(
            event_type="system",
            description="Test system event"
        )
        
        # Check daily file was created
        today = datetime.now()
        year_month = today.strftime("%Y-%m")
        day = today.strftime("%d")
        
        events_dir = Path(self.test_dir) / "events" / year_month
        daily_file = events_dir / f"{day}.log"
        
        self.assertTrue(daily_file.exists(), "Daily event file should be created")
        
        # Check file content
        with open(daily_file, 'r', encoding='utf-8') as f:
            line = f.readline().strip()
            event_data = json.loads(line)
            self.assertEqual(event_data["event_type"], "system")
            self.assertEqual(event_data["description"], "Test system event")
    
    def test_update_project_context_new_project(self):
        """Test updating project context for new project"""
        result = self.memory_bridge.update_project_context(
            project_id="new_project",
            name="New Project",
            status="planning",
            key_context="Important project details"
        )
        
        self.assertTrue(result, "Project context update should succeed")
        
        # Load memory and check project was added
        memory = self.memory_bridge.load_current_memory()
        projects = memory["current_memory"]["active_projects"]
        
        self.assertEqual(len(projects), 1)
        project = projects[0]
        self.assertEqual(project["project_id"], "new_project")
        self.assertEqual(project["name"], "New Project")
        self.assertEqual(project["status"], "planning")
        self.assertEqual(project["key_context"], "Important project details")
    
    def test_update_project_context_existing_project(self):
        """Test updating existing project context"""
        # First, add a project
        self.memory_bridge.update_project_context(
            project_id="existing_project",
            name="Existing Project",
            status="planning"
        )
        
        # Then update it
        result = self.memory_bridge.update_project_context(
            project_id="existing_project",
            name="Updated Project",
            status="executing",
            key_context="Updated details"
        )
        
        self.assertTrue(result, "Project context update should succeed")
        
        # Load memory and check project was updated
        memory = self.memory_bridge.load_current_memory()
        projects = memory["current_memory"]["active_projects"]
        
        self.assertEqual(len(projects), 1)
        project = projects[0]
        self.assertEqual(project["project_id"], "existing_project")
        self.assertEqual(project["name"], "Updated Project")
        self.assertEqual(project["status"], "executing")
        self.assertEqual(project["key_context"], "Updated details")
    
    def test_get_context_for_ai(self):
        """Test getting formatted context for AI"""
        # Set up test data
        self.memory_bridge.update_project_context(
            project_id="test_project",
            name="Test Project",
            status="active"
        )
        
        self.memory_bridge.log_event(
            event_type="user_message",
            description="User asked about project status",
            importance="medium"
        )
        
        # Get context
        context = self.memory_bridge.get_context_for_ai(max_events=5)
        
        # Verify context contains expected sections
        self.assertIn("アクティブプロジェクト", context)
        self.assertIn("Test Project", context)
        self.assertIn("最近のイベント", context)
        self.assertIn("User asked about project status", context)
    
    def test_event_limit_enforcement(self):
        """Test that events are limited to last 50 in memory"""
        # Add 60 events
        for i in range(60):
            self.memory_bridge.log_event(
                event_type="system",
                description=f"Event {i}",
                importance="low"
            )
        
        # Load memory and check only last 50 events are kept
        memory = self.memory_bridge.load_current_memory()
        events = memory["events"]
        
        self.assertEqual(len(events), 50, "Should keep only last 50 events")
        
        # Check that we have the last 50 events (10-59)
        self.assertEqual(events[0]["description"], "Event 10")
        self.assertEqual(events[-1]["description"], "Event 59")
    
    def test_memory_disabled(self):
        """Test behavior when memory is disabled"""
        with patch('core.memory_bridge.is_memory_enabled', return_value=False):
            bridge = MemoryBridge()
            
            # All operations should return False or empty results
            self.assertFalse(bridge.log_event("test", "Test message"))
            self.assertFalse(bridge.update_project_context("test", "Test", "active"))
            self.assertEqual(bridge.get_context_for_ai(), "")
            
            # Load should return empty memory
            memory = bridge.load_current_memory()
            self.assertEqual(memory["memory_version"], "2.0")
            self.assertEqual(memory["events"], [])

    def test_schema_validation(self):
        """Test memory schema validation"""
        # Test invalid memory (missing required field)
        invalid_memory = {
            "memory_version": "2.0",
            # Missing required fields
        }
        
        with self.assertRaises(ValueError):
            self.memory_bridge._validate_memory_schema(invalid_memory)
        
        # Test invalid version
        invalid_version = {
            "memory_version": "1.0",  # Wrong version
            "last_updated": "2025-07-05T16:00:00Z",
            "current_memory": {},
            "events": []
        }
        
        with self.assertRaises(ValueError):
            self.memory_bridge._validate_memory_schema(invalid_version)

# Test convenience functions
class TestConvenienceFunctions(unittest.TestCase):
    """Test convenience functions"""
    
    @patch('core.memory_bridge.memory_bridge')
    def test_convenience_functions(self, mock_bridge):
        """Test that convenience functions call the bridge correctly"""
        mock_bridge.log_event.return_value = True
        mock_bridge.update_project_context.return_value = True
        mock_bridge.get_context_for_ai.return_value = "context"
        mock_bridge.load_current_memory.return_value = {"test": "data"}
        
        # Test log_event
        result = log_event("test", "message")
        self.assertTrue(result)
        mock_bridge.log_event.assert_called_with("test", "message", None, "medium", None)
        
        # Test update_project_context
        result = update_project_context("proj", "name", "status")
        self.assertTrue(result)
        mock_bridge.update_project_context.assert_called_with("proj", "name", "status", None)


if __name__ == '__main__':
    unittest.main()