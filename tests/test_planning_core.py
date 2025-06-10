"""
Tests for planning_core.py
"""

import unittest
from datetime import datetime, timedelta
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.v2.planning_core import generate_wbs


class TestPlanningCore(unittest.TestCase):
    
    def setUp(self):
        """Set up test data"""
        self.sample_persona_result = {
            "project_name": "テストプロジェクト",
            "high_priority_goals": [
                "【重要】ユーザー登録システムの完成",
                "【重要】商品検索機能の実装",
                "【中優先】モバイル対応の完了",
                "【警告】関係者の明確化が必要",
                "【警告】使用ツールの決定が必要"
            ],
            "potential_risks": [
                {"risk": "スケジュール遅延", "impact": "高", "suggested_mitigation": "バッファ時間確保"}
            ],
            "recommended_milestones": [
                {"title": "プロジェクト計画完成", "due": "2025-06-19"},
                {"title": "初期プロトタイプ/MVP完成", "due": "2025-07-10"},
                {"title": "プロトタイプ完成", "due": "2025-07-15"},
                {"title": "最終成果物完成", "due": "2025-08-21"}
            ],
            "persona_comment": "テストプロジェクトの分析結果です。"
        }
        
    def test_generate_wbs_basic(self):
        """Test basic WBS generation"""
        wbs = generate_wbs(self.sample_persona_result)
        
        # Should return a list
        self.assertIsInstance(wbs, list)
        
        # Should have tasks
        self.assertGreater(len(wbs), 0)
        
        # Each task should have required fields
        for task in wbs:
            self.assertIn('name', task)
            self.assertIn('description', task)
            self.assertIn('depends_on', task)
            self.assertIn('suggested_due_date', task)
            
            # Check data types
            self.assertIsInstance(task['name'], str)
            self.assertIsInstance(task['description'], str)
            self.assertIsInstance(task['depends_on'], list)
            self.assertIsInstance(task['suggested_due_date'], str)
            
            # Check date format (should be YYYY-MM-DD)
            try:
                datetime.strptime(task['suggested_due_date'], '%Y-%m-%d')
            except ValueError:
                self.fail(f"Invalid date format: {task['suggested_due_date']}")
    
    def test_setup_tasks_generated(self):
        """Test that setup tasks are generated"""
        wbs = generate_wbs(self.sample_persona_result)
        
        # Should include setup tasks
        setup_task_names = [task['name'] for task in wbs]
        
        self.assertIn("プロジェクト環境セットアップ", setup_task_names)
        self.assertIn("要件定義書作成", setup_task_names)
        self.assertIn("技術設計書作成", setup_task_names)
    
    def test_goal_specific_tasks(self):
        """Test that tasks are generated for each goal"""
        wbs = generate_wbs(self.sample_persona_result)
        
        task_names = [task['name'] for task in wbs]
        
        # Should have tasks related to user registration system
        user_reg_tasks = [name for name in task_names if "ユーザー登録システム" in name]
        self.assertGreater(len(user_reg_tasks), 0)
        
        # Should have tasks related to search functionality
        search_tasks = [name for name in task_names if "商品検索機能" in name]
        self.assertGreater(len(search_tasks), 0)
        
        # Should have stakeholder analysis task for warning
        stakeholder_tasks = [name for name in task_names if "ステークホルダー" in name or "関係者" in name]
        self.assertGreater(len(stakeholder_tasks), 0)
    
    def test_dependencies_logical(self):
        """Test that task dependencies make logical sense"""
        wbs = generate_wbs(self.sample_persona_result)
        
        # Create a mapping of task names
        task_names = [task['name'] for task in wbs]
        
        for task in wbs:
            # All dependencies should reference existing tasks
            for dep in task['depends_on']:
                self.assertIn(dep, task_names, 
                    f"Task '{task['name']}' depends on non-existent task '{dep}'")
    
    def test_date_progression(self):
        """Test that task dates progress logically"""
        wbs = generate_wbs(self.sample_persona_result)
        
        # Parse dates and check progression
        task_dates = []
        for task in wbs:
            date_obj = datetime.strptime(task['suggested_due_date'], '%Y-%m-%d')
            task_dates.append((task['name'], date_obj))
        
        # Setup tasks should come first
        setup_task = next((task for task in wbs if task['name'] == "プロジェクト環境セットアップ"), None)
        self.assertIsNotNone(setup_task)
        
        setup_date = datetime.strptime(setup_task['suggested_due_date'], '%Y-%m-%d')
        
        # Final tasks should come last
        final_task = next((task for task in wbs if "プロジェクト完了" in task['name']), None)
        if final_task:
            final_date = datetime.strptime(final_task['suggested_due_date'], '%Y-%m-%d')
            self.assertGreater(final_date, setup_date)
    
    def test_empty_input(self):
        """Test handling of empty input"""
        empty_result = {}
        wbs = generate_wbs(empty_result)
        
        # Should return empty list for empty input
        self.assertEqual(wbs, [])
    
    def test_minimal_input(self):
        """Test handling of minimal input"""
        minimal_result = {
            "project_name": "Minimal Project",
            "high_priority_goals": ["【重要】単純なタスク"],
            "recommended_milestones": [],
            "persona_comment": "最小限のテスト"
        }
        
        wbs = generate_wbs(minimal_result)
        
        # Should still generate some tasks
        self.assertGreater(len(wbs), 0)
        
        # Should include setup tasks even with minimal input
        task_names = [task['name'] for task in wbs]
        self.assertIn("プロジェクト環境セットアップ", task_names)
    
    def test_warning_tasks_prioritized(self):
        """Test that warning tasks are scheduled early"""
        wbs = generate_wbs(self.sample_persona_result)
        
        # Find warning-related tasks
        warning_tasks = [task for task in wbs if 
                        "ステークホルダー" in task['name'] or 
                        "技術調査" in task['name']]
        
        if warning_tasks:
            # Warning tasks should have early dates
            warning_dates = [datetime.strptime(task['suggested_due_date'], '%Y-%m-%d') 
                           for task in warning_tasks]
            
            # Should be scheduled soon
            today = datetime.now()
            for date in warning_dates:
                days_diff = (date - today).days
                self.assertLessEqual(days_diff, 7, "Warning tasks should be scheduled within a week")
    
    def test_task_descriptions_meaningful(self):
        """Test that task descriptions are meaningful"""
        wbs = generate_wbs(self.sample_persona_result)
        
        for task in wbs:
            description = task['description']
            
            # Should not be empty
            self.assertTrue(description.strip(), f"Empty description for task: {task['name']}")
            
            # Should be at least a reasonable length
            self.assertGreaterEqual(len(description), 10, 
                f"Too short description for task: {task['name']}")
            
            # Should end with period (Japanese style)
            self.assertTrue(description.endswith('。'), 
                f"Description should end with period: {task['name']}")


if __name__ == '__main__':
    unittest.main()