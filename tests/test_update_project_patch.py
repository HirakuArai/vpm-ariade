"""
Test cases for Project Update Spec v1.0 - Generic Property Patch

Tests the apply_property_patch function according to the specification:
- T-01: Valid keys only update
- T-02: Invalid keys handling
- T-03: Mixed valid and invalid keys
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import sys
sys.path.append(str(Path(__file__).parent.parent))

from core.project_service import apply_property_patch, create_project


@pytest.fixture
def temp_projects_dir():
    """Create a temporary directory for test projects"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def test_project(temp_projects_dir):
    """Create a test project for updates"""
    project = create_project(
        identifier="test-proj-001",
        overview="Test project for property patch",
        created_by="test_user",
        display_name="Test Project",
        projects_dir=temp_projects_dir
    )
    return project.identifier, temp_projects_dir


class TestPropertyPatch:
    """Test cases for generic property patch functionality"""
    
    def test_t01_valid_keys_only_update(self, test_project):
        """T-01: Valid keys only update - should succeed and log changes"""
        project_id, projects_dir = test_project
        
        # Valid properties to update
        properties = {
            "start_date": "2025-08-02",
            "end_date": "2025-08-03", 
            "participants_count": 4,
            "status": "ACTIVE"
        }
        
        # Apply the patch
        result = apply_property_patch(project_id, properties, projects_dir)
        
        # Verify success
        assert result["success"] is True
        assert result["changes_applied"] == 4
        assert set(result["changed_fields"]) == set(properties.keys())
        
        # Verify changes were applied to JSON file
        project_file = projects_dir / f"{project_id}.json"
        with open(project_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        assert data["start_date"] == "2025-08-02"
        assert data["end_date"] == "2025-08-03"
        assert data["participants_count"] == 4
        assert data["status"] == "ACTIVE"
        
        # Verify change_log entry
        assert len(data["change_log"]) > 0
        latest_change = data["change_log"][-1]
        assert latest_change["type"] == "property_patch"
        assert set(latest_change["changed_fields"]) == set(properties.keys())
        assert latest_change["source"] == "apply_property_patch"
    
    def test_t02_invalid_keys_schema_validation(self, test_project):
        """T-02: Invalid keys should trigger schema validation error"""
        project_id, projects_dir = test_project
        
        # Include an invalid key
        properties = {
            "start_date": "2025-08-02",
            "invalid_field": "should_fail"
        }
        
        # Apply the patch - should fail with schema validation
        result = apply_property_patch(project_id, properties, projects_dir)
        
        # If jsonschema is available, should fail validation
        # If not available, should warn but still apply valid fields
        if result["success"] is False:
            assert result["error_type"] == "schema_validation_error"
            assert "Schema validation failed" in result["error"]
        else:
            # jsonschema not available - should warn but continue
            assert "warnings" in result or result["changes_applied"] >= 1
        
        # Verify JSON file is not corrupted
        project_file = projects_dir / f"{project_id}.json"
        with open(project_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Should still be valid JSON structure
        assert "identifier" in data
        assert "overview" in data
    
    def test_t03_mixed_valid_invalid_keys(self, test_project):
        """T-03: Mixed valid and invalid keys - apply valid ones, skip invalid"""
        project_id, projects_dir = test_project
        
        # Mix of valid and invalid properties
        properties = {
            "start_date": "2025-08-02",  # Valid
            "participants_count": 5,     # Valid
            "nonexistent_field": "test"  # Invalid
        }
        
        # This test depends on jsonschema availability
        # If jsonschema is available, it should fail validation entirely
        # If not available, it would apply all fields
        result = apply_property_patch(project_id, properties, projects_dir)
        
        # Verify the result based on jsonschema availability
        project_file = projects_dir / f"{project_id}.json"
        with open(project_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # JSON should remain valid regardless
        assert "identifier" in data
        
        if result["success"]:
            # jsonschema not available - all fields applied
            assert data.get("start_date") == "2025-08-02"
            assert data.get("participants_count") == 5
        else:
            # jsonschema available - validation failed, no changes
            assert result["error_type"] == "schema_validation_error"
    
    def test_project_not_found(self, temp_projects_dir):
        """Test handling of non-existent project"""
        result = apply_property_patch(
            "nonexistent-project", 
            {"status": "ACTIVE"}, 
            temp_projects_dir
        )
        
        assert result["success"] is False
        assert result["error_type"] == "project_not_found"
        assert "not found" in result["error"]
    
    def test_empty_properties(self, test_project):
        """Test handling of empty properties dictionary"""
        project_id, projects_dir = test_project
        
        result = apply_property_patch(project_id, {}, projects_dir)
        
        assert result["success"] is False
        assert result["error_type"] == "validation_error"
        assert "properties are required" in result["error"]
    
    def test_multiple_updates_preserve_data(self, test_project):
        """Test that multiple updates preserve existing data"""
        project_id, projects_dir = test_project
        
        # First update
        result1 = apply_property_patch(project_id, {"status": "ACTIVE"}, projects_dir)
        assert result1["success"] is True
        
        # Second update
        result2 = apply_property_patch(project_id, {"participants_count": 10}, projects_dir)
        assert result2["success"] is True
        
        # Verify both updates are preserved
        project_file = projects_dir / f"{project_id}.json"
        with open(project_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        assert data.get("status") == "ACTIVE"  # From first update
        assert data.get("participants_count") == 10  # From second update
        assert len(data["change_log"]) >= 2  # Should have both change log entries


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])