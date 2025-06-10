"""
Test project creation functionality
"""

import pytest
import tempfile
import json
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.project_service import create_project
from core.models import Project, DEFAULT_UNDEF
from core.self_checker import compare_snapshots, check_project_changes


class TestProjectCreation:
    """Test project creation functionality"""
    
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
    
    def test_create_project_basic(self):
        """Test basic project creation"""
        identifier = "test-project"
        overview = "A test project"
        created_by = "test_user"
        
        project = create_project(identifier, overview, created_by)
        
        # Verify project object
        assert project.identifier == identifier
        assert project.overview == overview
        assert project.created_by == created_by
        assert project.status == "DRAFT"
        assert project.schema_version == "1.0"
        assert project.uuid is not None
        assert project.created_at is not None
        assert project.updated_at is not None
        assert isinstance(project.change_log, list)
    
    def test_create_project_idempotency(self):
        """Test that creating the same project twice returns the same result"""
        identifier = "test-project-idem"
        overview = "A test project for idempotency"
        created_by = "test_user"
        
        # Create project first time
        project1 = create_project(identifier, overview, created_by)
        
        # Create project second time (should load existing)
        project2 = create_project(identifier, overview, created_by)
        
        # Should be identical
        assert project1.identifier == project2.identifier
        assert project1.overview == project2.overview
        assert project1.created_by == project2.created_by
        assert project1.uuid == project2.uuid
        assert project1.created_at == project2.created_at
    
    def test_project_to_dict(self):
        """Test project serialization"""
        project = Project(
            identifier="test",
            overview="test overview",
            created_by="user"
        )
        
        data = project.to_dict()
        
        # Verify all fields present
        assert data["identifier"] == "test"
        assert data["overview"] == "test overview"
        assert data["created_by"] == "user"
        assert data["status"] == "DRAFT"
        assert data["schema_version"] == "1.0"
        assert "uuid" in data
        assert "created_at" in data
        assert "updated_at" in data
        assert "change_log" in data
    
    def test_project_file_creation(self):
        """Test that project files are created correctly"""
        identifier = "test-file-creation"
        overview = "Test file creation"
        created_by = "test_user"
        
        project = create_project(identifier, overview, created_by)
        
        # Verify file exists
        project_file = self.test_dir / f"{identifier}.json"
        assert project_file.exists()
        
        # Verify file content
        with open(project_file, 'r') as f:
            data = json.load(f)
        
        assert data["identifier"] == identifier
        assert data["overview"] == overview
        assert data["created_by"] == created_by
        assert data["status"] == "DRAFT"
    
    def test_undefined_field_handling(self):
        """Test handling of undefined fields"""
        project = Project(identifier="test", overview="test")
        data = project.to_dict()
        
        # created_by should be __UNDEFINED__ if not provided
        assert data["created_by"] == DEFAULT_UNDEF
    
    def test_compare_snapshots_ignore_undefined(self):
        """Test that snapshot comparison ignores __UNDEFINED__ values"""
        old_snapshot = {
            "identifier": "test",
            "overview": "old overview",
            "created_by": DEFAULT_UNDEF
        }
        
        new_snapshot = {
            "identifier": "test", 
            "overview": "new overview",
            "created_by": "actual_user"
        }
        
        differences = compare_snapshots(old_snapshot, new_snapshot)
        
        # Should only detect overview change, not created_by since old was undefined
        assert "overview" in differences
        assert "created_by" not in differences
        assert differences["overview"]["old"] == "old overview"
        assert differences["overview"]["new"] == "new overview"
    
    def test_check_project_changes(self):
        """Test project change checking functionality"""
        identifier = "test-changes"
        overview = "Test changes"
        created_by = "test_user"
        
        # Create project
        create_project(identifier, overview, created_by)
        
        # Check changes
        report = check_project_changes(identifier, self.test_dir)
        
        assert report["project_id"] == identifier
        assert report["status"] == "valid"
        assert report["snapshot_valid"] is True
    
    def test_check_nonexistent_project(self):
        """Test checking changes for nonexistent project"""
        report = check_project_changes("nonexistent", self.test_dir)
        
        assert "error" in report
        assert "not found" in report["error"]
    
    def test_project_with_empty_fields(self):
        """Test project creation with empty optional fields"""
        project = Project(
            identifier="test-empty",
            overview="test with empty fields"
        )
        
        data = project.to_dict()
        
        # Empty fields should become __UNDEFINED__
        assert data["created_by"] == DEFAULT_UNDEF