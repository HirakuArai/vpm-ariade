"""
Test task addition functionality
"""

import pytest
import tempfile
import json
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.project_service import create_project, add_task
from core.models import DEFAULT_UNDEF


class TestTaskAddition:
    """Test task addition functionality"""
    
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
    
    def test_add_task_basic(self):
        """Test basic task addition"""
        # Create a project first
        project = create_project("test-project", "Test project for tasks", "test_user")
        
        # Add a task
        task = add_task("test-project", "テストタスクの実行", "2024-12-31")
        
        # Verify task structure
        assert task["id"] == 1
        assert task["description"] == "テストタスクの実行"
        assert task["due_date"] == "2024-12-31"
        assert task["owner"] == DEFAULT_UNDEF
        assert task["status"] == DEFAULT_UNDEF
        
        # Verify task was saved to project file
        project_file = self.test_dir / "test-project.json"
        with open(project_file, 'r') as f:
            data = json.load(f)
        
        assert "tasks" in data
        assert len(data["tasks"]) == 1
        assert data["tasks"][0] == task
    
    def test_add_task_unique_id(self):
        """Test that task IDs are unique and sequential"""
        # Create a project first
        create_project("test-sequential", "Test sequential IDs", "test_user")
        
        # Add multiple tasks
        task1 = add_task("test-sequential", "第一のタスク", "2024-12-31")
        task2 = add_task("test-sequential", "第二のタスク", "2025-01-15")
        task3 = add_task("test-sequential", "第三のタスク", "2025-02-28")
        
        # Verify sequential IDs
        assert task1["id"] == 1
        assert task2["id"] == 2
        assert task3["id"] == 3
        
        # Verify all tasks are saved
        project_file = self.test_dir / "test-sequential.json"
        with open(project_file, 'r') as f:
            data = json.load(f)
        
        assert len(data["tasks"]) == 3
        assert data["tasks"][0]["id"] == 1
        assert data["tasks"][1]["id"] == 2
        assert data["tasks"][2]["id"] == 3
    
    def test_add_task_with_owner(self):
        """Test adding task with specified owner"""
        # Create a project first
        create_project("test-owner", "Test task with owner", "test_user")
        
        # Add a task with owner
        task = add_task("test-owner", "担当者付きタスク", "2024-12-31", "田中太郎")
        
        # Verify owner is set
        assert task["owner"] == "田中太郎"
        assert task["status"] == DEFAULT_UNDEF
    
    def test_add_task_nonexistent_project(self):
        """Test adding task to nonexistent project raises error"""
        with pytest.raises(FileNotFoundError, match="Project nonexistent not found"):
            add_task("nonexistent", "存在しないプロジェクトのタスク", "2024-12-31")
    
    def test_add_task_to_project_without_tasks_field(self):
        """Test adding task to project that doesn't have tasks field yet"""
        # Create project manually without tasks field
        project_file = self.test_dir / "manual-project.json"
        project_data = {
            "identifier": "manual-project",
            "overview": "Manually created project",
            "status": "DRAFT"
        }
        with open(project_file, 'w') as f:
            json.dump(project_data, f)
        
        # Add task should work and create tasks field
        task = add_task("manual-project", "新規タスクフィールド", "2024-12-31")
        
        # Verify task was added and tasks field was created
        with open(project_file, 'r') as f:
            data = json.load(f)
        
        assert "tasks" in data
        assert len(data["tasks"]) == 1
        assert data["tasks"][0] == task
    
    def test_chat_add_task_flow(self):
        """Test simulated chat flow for adding tasks"""
        # Create a project first
        project = create_project(None, "チャットテストプロジェクト", "human_user")
        project_id = project.identifier
        
        # Simulate chat command parsing
        user_input = "タスク UIのデザイン作成 2024-12-31"
        
        # Parse command (simulating chat handler logic)
        if user_input.startswith("タスク "):
            import re
            parts = user_input[3:].strip().split()
            due_date = parts[-1]
            description = " ".join(parts[:-1])
            
            # Validate date format
            assert re.match(r'\d{4}-\d{2}-\d{2}', due_date)
            
            # Add task
            task = add_task(project_id, description, due_date)
            
            # Verify task was created correctly
            assert task["description"] == "UIのデザイン作成"
            assert task["due_date"] == "2024-12-31"
            assert task["id"] == 1
    
    def test_chat_add_multiple_tasks(self):
        """Test adding multiple tasks via chat commands"""
        # Create a project
        project = create_project(None, "マルチタスクプロジェクト", "human_user")
        project_id = project.identifier
        
        # Add multiple tasks via simulated chat commands
        commands = [
            "タスク データベース設計 2024-12-15",
            "タスク APIエンドポイント実装 2024-12-20", 
            "タスク フロントエンド開発 2024-12-25"
        ]
        
        for i, command in enumerate(commands, 1):
            parts = command[3:].strip().split()
            due_date = parts[-1]
            description = " ".join(parts[:-1])
            
            task = add_task(project_id, description, due_date)
            assert task["id"] == i
        
        # Verify all tasks are saved
        project_file = self.test_dir / f"{project_id}.json"
        with open(project_file, 'r') as f:
            data = json.load(f)
        
        assert len(data["tasks"]) == 3
        assert data["tasks"][0]["description"] == "データベース設計"
        assert data["tasks"][1]["description"] == "APIエンドポイント実装"
        assert data["tasks"][2]["description"] == "フロントエンド開発"
    
    def test_task_timestamp_update(self):
        """Test that adding tasks updates project timestamp"""
        # Create a project
        project = create_project("test-timestamp", "Timestamp test", "test_user")
        original_updated_at = project.updated_at
        
        # Wait a bit to ensure timestamp difference
        import time
        time.sleep(0.01)
        
        # Add a task
        add_task("test-timestamp", "タイムスタンプテスト", "2024-12-31")
        
        # Verify timestamp was updated
        project_file = self.test_dir / "test-timestamp.json"
        with open(project_file, 'r') as f:
            data = json.load(f)
        
        assert data["updated_at"] != original_updated_at