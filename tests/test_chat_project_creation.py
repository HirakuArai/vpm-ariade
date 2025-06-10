"""
Test chat-based project creation and auto-generated IDs
"""

import pytest
import tempfile
import json
import time
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.project_service import create_project, set_status, _autogen_id


class TestChatProjectCreation:
    """Test chat-based project creation functionality"""
    
    def setup_method(self):
        """Setup test environment"""
        self.test_dir = Path(tempfile.mkdtemp())
        # Mock the PROJECTS_DIR for testing
        import core.project_service
        self.original_projects_dir = core.project_service.PROJECTS_DIR
        core.project_service.PROJECTS_DIR = self.test_dir
    
    def teardown_method(self):
        """Cleanup test environment"""
        import shutil
        import core.project_service
        core.project_service.PROJECTS_DIR = self.original_projects_dir
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
    
    def test_autogen_id_is_unique(self):
        """Test that auto-generated IDs are unique even within same second"""
        # Generate multiple IDs quickly
        ids = []
        for _ in range(5):
            ids.append(_autogen_id())
            # Small delay to ensure different microseconds
            time.sleep(0.001)
        
        # All IDs should be unique
        assert len(set(ids)) == len(ids), f"Duplicate IDs found: {ids}"
        
        # All IDs should follow the expected format
        for id_str in ids:
            assert id_str.startswith("proj-"), f"ID {id_str} doesn't start with 'proj-'"
            assert len(id_str.split("-")) >= 3, f"ID {id_str} doesn't have expected format"
    
    def test_create_project_with_none_identifier(self):
        """Test project creation with None identifier triggers auto-generation"""
        overview = "Auto-generated test project"
        created_by = "test_user"
        
        project = create_project(None, overview, created_by)
        
        # Should have auto-generated identifier
        assert project.identifier is not None
        assert project.identifier.startswith("proj-")
        assert project.overview == overview
        assert project.created_by == created_by
        assert project.status == "DRAFT"
    
    def test_set_status_functionality(self):
        """Test set_status function updates project status"""
        # Create a project first
        project = create_project("test-status", "Test status change", "test_user")
        original_updated_at = project.updated_at
        
        # Wait a bit to ensure timestamp difference
        time.sleep(0.01)
        
        # Update status
        set_status("test-status", "ACTIVE")
        
        # Verify status was updated
        project_file = self.test_dir / "test-status.json"
        with open(project_file, 'r') as f:
            data = json.load(f)
        
        assert data["status"] == "ACTIVE"
        assert data["updated_at"] != original_updated_at
    
    def test_set_status_nonexistent_project(self):
        """Test set_status raises error for nonexistent project"""
        with pytest.raises(FileNotFoundError, match="Project nonexistent not found"):
            set_status("nonexistent", "ACTIVE")
    
    def test_chat_flow_simulation(self):
        """Test simulated chat flow: プロジェクト作成 → 概要 → はい"""
        # Simulate chat flow state
        class MockChatState:
            def __init__(self):
                self.awaiting_project_overview = False
                self.awaiting_activate_confirm = False
                self.created_project_id = None
        
        chat_state = MockChatState()
        
        # Step 1: User says "プロジェクト作成"
        user_input1 = "プロジェクト作成"
        assert "プロジェクト作成" in user_input1
        chat_state.awaiting_project_overview = True
        
        # Step 2: User provides overview
        user_input2 = "新しいWebアプリケーションの開発"
        if chat_state.awaiting_project_overview:
            project = create_project(None, user_input2, "human_user")
            chat_state.created_project_id = project.identifier
            chat_state.awaiting_project_overview = False
            chat_state.awaiting_activate_confirm = True
            
            # Verify project was created
            assert project.identifier.startswith("proj-")
            assert project.overview == user_input2
            assert project.status == "DRAFT"
        
        # Step 3: User says "はい" to activate
        user_input3 = "はい"
        if chat_state.awaiting_activate_confirm:
            user_lower = user_input3.lower().strip()
            if any(word in user_lower for word in ["はい", "yes", "する", "active", "アクティブ"]):
                set_status(chat_state.created_project_id, "ACTIVE")
                
                # Verify status was updated
                project_file = self.test_dir / f"{chat_state.created_project_id}.json"
                with open(project_file, 'r') as f:
                    data = json.load(f)
                assert data["status"] == "ACTIVE"
            
            # Reset flow state
            chat_state.awaiting_activate_confirm = False
            chat_state.created_project_id = None
    
    def test_chat_flow_decline_activation(self):
        """Test chat flow when user declines activation"""
        # Create project
        project = create_project(None, "Test decline activation", "human_user")
        
        # Simulate declining activation
        user_input = "いいえ"
        user_lower = user_input.lower().strip()
        activated = any(word in user_lower for word in ["はい", "yes", "する", "active", "アクティブ"])
        
        # Should not activate
        assert not activated
        
        # Status should remain DRAFT
        project_file = self.test_dir / f"{project.identifier}.json"
        with open(project_file, 'r') as f:
            data = json.load(f)
        assert data["status"] == "DRAFT"
    
    def test_autogen_id_format(self):
        """Test auto-generated ID format matches expected pattern"""
        id_str = _autogen_id()
        
        # Should start with "proj-"
        assert id_str.startswith("proj-")
        
        # Should have format: proj-YYYYMMDD-HHMMSS-XXX
        parts = id_str.split("-")
        assert len(parts) == 4, f"Expected 4 parts, got {len(parts)}: {parts}"
        
        # Date part should be 8 digits
        date_part = parts[1]
        assert len(date_part) == 8 and date_part.isdigit()
        
        # Time part should be 6 digits
        time_part = parts[2]
        assert len(time_part) == 6 and time_part.isdigit()
        
        # Microsecond part should be 3 digits
        microsec_part = parts[3]
        assert len(microsec_part) == 3 and microsec_part.isdigit()
    
    def test_multiple_project_creation_unique_ids(self):
        """Test creating multiple projects with None ID generates unique identifiers"""
        projects = []
        for i in range(3):
            project = create_project(None, f"Test project {i}", "test_user")
            projects.append(project)
        
        # All projects should have unique identifiers
        identifiers = [p.identifier for p in projects]
        assert len(set(identifiers)) == len(identifiers)
        
        # All should start with proj-
        for identifier in identifiers:
            assert identifier.startswith("proj-")