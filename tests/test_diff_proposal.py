"""
Test diff proposal functionality
"""

import pytest
import tempfile
import json
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.project_diff import (
    generate_update_candidates, 
    extract_new_data_from_chat, 
    generate_diff_summary,
    validate_update_candidate
)
from core.project_service import create_project, apply_updates, merge_updates
from core.models import DEFAULT_UNDEF


class TestDiffProposal:
    """Test diff proposal functionality"""
    
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
    
    def test_generate_update_candidates(self):
        """Test basic update candidates generation"""
        # Create a project first
        project = create_project("test-diff", "Test project for diff", "test_user")
        
        # Define new data to compare
        new_data = {
            "repository_url": "https://github.com/example/test-repo",
            "due_date": "2024-12-31",
            "status": "ACTIVE"
        }
        
        # Generate update candidates
        candidates = generate_update_candidates("test-diff", new_data, projects_dir=self.test_dir)
        
        # Should have 3 candidates (all fields are new)
        assert len(candidates) == 3
        
        # Check repository_url candidate
        repo_candidate = next(c for c in candidates if c["field"] == "repository_url")
        assert repo_candidate["old"] is None
        assert repo_candidate["new"] == "https://github.com/example/test-repo"
        
        # Check due_date candidate
        due_date_candidate = next(c for c in candidates if c["field"] == "due_date")
        assert due_date_candidate["old"] is None
        assert due_date_candidate["new"] == "2024-12-31"
        
        # Check status candidate
        status_candidate = next(c for c in candidates if c["field"] == "status")
        assert status_candidate["old"] == "DRAFT"  # Default status
        assert status_candidate["new"] == "ACTIVE"
    
    def test_generate_update_candidates_no_changes(self):
        """Test update candidates generation when no changes exist"""
        # Create a project
        project = create_project("test-no-change", "Test project", "test_user")
        
        # Define same data as existing
        new_data = {
            "overview": "Test project",
            "status": "DRAFT"
        }
        
        # Generate update candidates
        candidates = generate_update_candidates("test-no-change", new_data, projects_dir=self.test_dir)
        
        # Should have no candidates since values are the same
        assert len(candidates) == 0
    
    def test_generate_update_candidates_partial_changes(self):
        """Test update candidates generation with partial changes"""
        # Create a project
        project = create_project("test-partial", "Original overview", "test_user")
        
        # Define mixed data (some same, some different)
        new_data = {
            "overview": "Updated overview",  # Changed
            "status": "DRAFT",              # Same
            "budget": "100000"              # New
        }
        
        # Generate update candidates
        candidates = generate_update_candidates("test-partial", new_data, projects_dir=self.test_dir)
        
        # Should have 2 candidates (overview changed, budget new)
        assert len(candidates) == 2
        
        # Check overview change
        overview_candidate = next(c for c in candidates if c["field"] == "overview")
        assert overview_candidate["old"] == "Original overview"
        assert overview_candidate["new"] == "Updated overview"
        
        # Check budget addition
        budget_candidate = next(c for c in candidates if c["field"] == "budget")
        assert budget_candidate["old"] is None
        assert budget_candidate["new"] == "100000"
    
    def test_extract_new_data_from_chat(self):
        """Test extracting structured data from chat content"""
        # Test repository URL extraction
        chat_content = "プロジェクトのリポジトリは https://github.com/test/project です。"
        extracted = extract_new_data_from_chat(chat_content, "test-project")
        assert "repository_url" in extracted
        assert extracted["repository_url"] == "https://github.com/test/project"
        
        # Test due date extraction
        chat_content = "期日は2024-12-31に設定してください。"
        extracted = extract_new_data_from_chat(chat_content, "test-project")
        assert "due_date" in extracted
        assert extracted["due_date"] == "2024-12-31"
        
        # Test status extraction
        chat_content = "プロジェクトをアクティブにしましょう。"
        extracted = extract_new_data_from_chat(chat_content, "test-project")
        assert "status" in extracted
        assert extracted["status"] == "ACTIVE"
        
        # Test multiple extractions
        chat_content = "repository: https://github.com/multi/test deadline 2025-01-15 status: active"
        extracted = extract_new_data_from_chat(chat_content, "test-project")
        assert len(extracted) == 3
        assert extracted["repository_url"] == "https://github.com/multi/test"
        assert extracted["due_date"] == "2025-01-15"
        assert extracted["status"] == "ACTIVE"
    
    def test_generate_diff_summary(self):
        """Test generating human-readable diff summary"""
        # Empty candidates
        candidates = []
        summary = generate_diff_summary(candidates)
        assert summary == "変更候補はありません。"
        
        # Single candidate
        candidates = [
            {"field": "repository_url", "old": None, "new": "https://github.com/test/repo"}
        ]
        summary = generate_diff_summary(candidates)
        assert "1 件の更新候補があります" in summary
        assert "リポジトリURL" in summary
        assert "（未設定）" in summary
        assert "https://github.com/test/repo" in summary
        
        # Multiple candidates
        candidates = [
            {"field": "repository_url", "old": None, "new": "https://github.com/test/repo"},
            {"field": "due_date", "old": "2024-12-01", "new": "2024-12-31"},
            {"field": "status", "old": "DRAFT", "new": "ACTIVE"}
        ]
        summary = generate_diff_summary(candidates)
        assert "3 件の更新候補があります" in summary
        assert "リポジトリURL" in summary
        assert "期日" in summary
        assert "ステータス" in summary
    
    def test_validate_update_candidate(self):
        """Test update candidate validation"""
        # Valid candidates
        valid_repo = {
            "field": "repository_url",
            "old": None,
            "new": "https://github.com/test/repo"
        }
        assert validate_update_candidate(valid_repo) == True
        
        valid_date = {
            "field": "due_date",
            "old": "2024-12-01",
            "new": "2024-12-31"
        }
        assert validate_update_candidate(valid_date) == True
        
        valid_status = {
            "field": "status",
            "old": "DRAFT",
            "new": "ACTIVE"
        }
        assert validate_update_candidate(valid_status) == True
        
        # Invalid candidates
        invalid_repo = {
            "field": "repository_url",
            "old": None,
            "new": "not-a-url"
        }
        assert validate_update_candidate(invalid_repo) == False
        
        invalid_date = {
            "field": "due_date",
            "old": None,
            "new": "invalid-date"
        }
        assert validate_update_candidate(invalid_date) == False
        
        invalid_status = {
            "field": "status",
            "old": "DRAFT",
            "new": "INVALID_STATUS"
        }
        assert validate_update_candidate(invalid_status) == False
        
        # Missing fields
        incomplete = {
            "field": "repository_url",
            "new": "https://github.com/test/repo"
            # Missing "old"
        }
        assert validate_update_candidate(incomplete) == False
    
    def test_apply_updates(self):
        """Test applying updates to project"""
        # Create a project
        project = create_project("test-apply", "Test project", "test_user")
        
        # Define update candidates
        update_candidates = [
            {"field": "repository_url", "old": None, "new": "https://github.com/test/apply"},
            {"field": "status", "old": "DRAFT", "new": "ACTIVE"}
        ]
        
        # Apply updates
        result = apply_updates("test-apply", update_candidates, projects_dir=self.test_dir)
        
        # Check result
        assert result["success"] == True
        assert result["updates_applied"] == 2
        
        # Verify updates were actually applied
        project_file = self.test_dir / "test-apply.json"
        with open(project_file, 'r', encoding='utf-8') as f:
            updated_data = json.load(f)
        
        assert updated_data["repository_url"] == "https://github.com/test/apply"
        assert updated_data["status"] == "ACTIVE"
        assert "change_log" in updated_data
        assert len(updated_data["change_log"]) > 0
        
        # Check change log entry
        log_entry = updated_data["change_log"][-1]
        assert log_entry["type"] == "update_candidates_applied"
        assert "repository_url" in log_entry["fields_updated"]
        assert "status" in log_entry["fields_updated"]
    
    def test_merge_updates(self):
        """Test merge_updates function directly"""
        # Create a project
        project = create_project("test-merge", "Test project", "test_user")
        
        # Define update candidates
        update_candidates = [
            {"field": "budget", "old": None, "new": "50000"},
            {"field": "overview", "old": "Test project", "new": "Updated test project"}
        ]
        
        # Apply merge_updates
        result = merge_updates("test-merge", update_candidates, projects_dir=self.test_dir)
        
        # Check result
        assert result == True
        
        # Verify updates in file
        project_file = self.test_dir / "test-merge.json"
        with open(project_file, 'r', encoding='utf-8') as f:
            updated_data = json.load(f)
        
        assert updated_data["budget"] == "50000"
        assert updated_data["overview"] == "Updated test project"
    
    def test_merge_updates_value_mismatch(self):
        """Test merge_updates with value mismatches"""
        # Create a project
        project = create_project("test-mismatch", "Test project", "test_user")
        
        # Manually update the project first
        project_file = self.test_dir / "test-mismatch.json"
        with open(project_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        data["overview"] = "Manually changed overview"
        with open(project_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        
        # Define update candidates with wrong old value
        update_candidates = [
            {"field": "overview", "old": "Test project", "new": "Updated overview"}  # old value is wrong
        ]
        
        # Apply merge_updates
        result = merge_updates("test-mismatch", update_candidates, projects_dir=self.test_dir)
        
        # Should still succeed but skip the mismatched field
        assert result == True
        
        # Verify the field was not updated due to mismatch
        with open(project_file, 'r', encoding='utf-8') as f:
            updated_data = json.load(f)
        
        assert updated_data["overview"] == "Manually changed overview"  # Should remain unchanged
    
    def test_apply_updates_nonexistent_project(self):
        """Test applying updates to nonexistent project"""
        update_candidates = [
            {"field": "status", "old": "DRAFT", "new": "ACTIVE"}
        ]
        
        # Should handle FileNotFoundError gracefully
        result = apply_updates("nonexistent-project", update_candidates, projects_dir=self.test_dir)
        
        assert result["success"] == False
        assert "error" in result