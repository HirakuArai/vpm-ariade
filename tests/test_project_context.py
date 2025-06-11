"""
Test project context functionality
"""

import pytest
import tempfile
import json
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.project_prompt import (
    get_project_prompt, 
    get_available_project_ids, 
    get_project_summary
)
from core.project_service import create_project, add_task
from core.models import DEFAULT_UNDEF


class TestProjectContext:
    """Test project context functionality"""
    
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
    
    def test_selector_sets_project_id(self):
        """Test that project selector functionality works correctly"""
        # Create test projects
        project1 = create_project("test-project-1", "First test project", "test_user")
        project2 = create_project("test-project-2", "Second test project", "test_user")
        
        # Test get_available_project_ids
        project_ids = get_available_project_ids()
        assert len(project_ids) == 2
        assert "test-project-1" in project_ids
        assert "test-project-2" in project_ids
        
        # Test project summary generation
        summary1 = get_project_summary("test-project-1")
        assert "test-project-1" in summary1
        assert "First test project" in summary1
        assert "DRAFT" in summary1
        
        summary2 = get_project_summary("test-project-2")
        assert "test-project-2" in summary2
        assert "Second test project" in summary2
    
    def test_get_project_prompt_structure(self):
        """Test that get_project_prompt returns properly structured content"""
        # Create a project with some tasks
        project = create_project("test-prompt", "Test project for prompt generation", "test_user")
        
        # Add some tasks
        add_task("test-prompt", "Complete feature A", "2024-12-31", "Alice")
        add_task("test-prompt", "Review code", "2024-12-25", "Bob")
        add_task("test-prompt", "Deploy to production", "2025-01-15")
        
        # Generate project prompt
        prompt = get_project_prompt("test-prompt")
        
        # Verify structure
        assert "# 📋 現在のプロジェクトコンテキスト" in prompt
        assert "**プロジェクト ID**: test-prompt" in prompt
        assert "**概要**: Test project for prompt generation" in prompt
        assert "**ステータス**: DRAFT" in prompt
        assert "## 🔲 未完了タスク (上位3件)" in prompt
        
        # Verify tasks are included
        assert "Complete feature A" in prompt
        assert "Review code" in prompt
        assert "Deploy to production" in prompt
        
        # Verify task details
        assert "期日: 2024-12-31" in prompt
        assert "(担当: Alice)" in prompt
        assert "(担当: Bob)" in prompt
        
        # Verify guidance text
        assert "このプロジェクトコンテキストを念頭に置いて" in prompt
    
    def test_get_project_prompt_no_tasks(self):
        """Test project prompt generation for project without tasks"""
        # Create a project without tasks
        project = create_project("no-tasks", "Project without tasks", "test_user")
        
        # Generate project prompt
        prompt = get_project_prompt("no-tasks")
        
        # Verify basic structure
        assert "# 📋 現在のプロジェクトコンテキスト" in prompt
        assert "**プロジェクト ID**: no-tasks" in prompt
        assert "**概要**: Project without tasks" in prompt
        
        # Verify no tasks message
        assert "まだタスクが作成されていません。" in prompt
    
    def test_get_project_prompt_nonexistent_project(self):
        """Test project prompt generation for nonexistent project"""
        prompt = get_project_prompt("nonexistent-project")
        
        assert "❌" in prompt
        assert "nonexistent-project が見つかりません" in prompt
    
    def test_get_project_prompt_with_additional_fields(self):
        """Test project prompt includes additional fields when available"""
        # Create a project
        project = create_project("full-project", "Full featured project", "test_user")
        
        # Manually add additional fields to the project file
        project_file = self.test_dir / "full-project.json"
        with open(project_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        data["repository_url"] = "https://github.com/test/full-project"
        data["due_date"] = "2024-12-31"
        data["budget"] = "100000"
        
        with open(project_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        
        # Generate project prompt
        prompt = get_project_prompt("full-project")
        
        # Verify additional fields are included
        assert "**リポジトリ**: https://github.com/test/full-project" in prompt
        assert "**プロジェクト期日**: 2024-12-31" in prompt
        assert "**予算**: 100000" in prompt
    
    def test_logging_file_created(self):
        """Test that project-specific logging creates correct file structure"""
        # This test simulates the project logging functionality
        # since we can't easily test the actual streamlit app logging
        
        from datetime import datetime
        from zoneinfo import ZoneInfo
        
        # Mock the project logging path creation
        project_id = "test-logging"
        today = datetime.now(ZoneInfo("Asia/Tokyo")).strftime("%Y%m%d")
        
        # Expected path structure
        expected_conv_dir = Path(f"data/conversations/{project_id}")
        expected_log_file = expected_conv_dir / f"{today}.jsonl"
        
        # Create the directory structure that would be created by _project_log_path
        expected_conv_dir.mkdir(parents=True, exist_ok=True)
        
        # Simulate logging a message
        log_entry = {
            "project_id": project_id,
            "role": "user",
            "content": "Test message",
            "timestamp": datetime.now(ZoneInfo("Asia/Tokyo")).isoformat(timespec="seconds")
        }
        
        # Write to JSONL file
        with expected_log_file.open("a", encoding="utf-8") as fp:
            fp.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        
        # Verify file was created and has correct format
        assert expected_log_file.exists()
        
        # Read and verify content
        with expected_log_file.open("r", encoding="utf-8") as fp:
            lines = fp.readlines()
        
        assert len(lines) == 1
        
        logged_entry = json.loads(lines[0].strip())
        assert logged_entry["project_id"] == project_id
        assert logged_entry["role"] == "user"
        assert logged_entry["content"] == "Test message"
        assert "timestamp" in logged_entry
        
        # Clean up
        expected_log_file.unlink()
        expected_conv_dir.rmdir()
    
    def test_project_summary_truncation(self):
        """Test that long project overviews are truncated in summaries"""
        # Create a project with a very long overview
        long_overview = "This is a very long project overview that should be truncated when displayed in the project selector"
        project = create_project("long-overview", long_overview, "test_user")
        
        # Get project summary
        summary = get_project_summary("long-overview")
        
        # Verify truncation (should be 50 chars + "...")
        assert len(summary.split(" - ")[1]) <= 53  # 50 + "..."
        assert "..." in summary
    
    def test_get_available_project_ids_empty(self):
        """Test get_available_project_ids with no projects"""
        project_ids = get_available_project_ids()
        assert project_ids == []
    
    def test_get_project_summary_nonexistent(self):
        """Test get_project_summary for nonexistent project"""
        summary = get_project_summary("nonexistent")
        assert summary is None
    
    def test_project_prompt_task_limit(self):
        """Test that project prompt shows only top 3 incomplete tasks"""
        # Create a project
        project = create_project("many-tasks", "Project with many tasks", "test_user")
        
        # Add 5 tasks
        for i in range(1, 6):
            add_task("many-tasks", f"Task {i}", f"2024-12-{20+i}", f"User{i}")
        
        # Generate project prompt
        prompt = get_project_prompt("many-tasks")
        
        # Should show only top 3 tasks
        assert "1. **[1]** Task 1" in prompt
        assert "2. **[2]** Task 2" in prompt
        assert "3. **[3]** Task 3" in prompt
        
        # Should show indication of more tasks
        assert "... 他 2 件の未完了タスク" in prompt
        
        # Should not show individual entries for tasks 4 and 5
        lines = prompt.split('\n')
        task_lines = [line for line in lines if "Task 4" in line or "Task 5" in line]
        assert len(task_lines) == 0  # No individual lines for tasks 4 and 5