# --- tests/test_lifecycle_manager.py ---
"""
Test ProjectLifecycleManager functionality
"""

import pytest
import tempfile
import json
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.lifecycle_manager import ProjectLifecycleManager, PhaseRequirements
from core.models import ProjectPhase, Project
from core.project_service import create_project


class TestProjectLifecycleManager:
    """Test project lifecycle management functionality"""
    
    def setup_method(self):
        """Setup test environment"""
        self.test_dir = Path(tempfile.mkdtemp())
        # Mock the PROJECTS_DIR for testing
        import core.project_service
        import core.lifecycle_manager
        self.original_projects_dir = core.project_service.PROJECTS_DIR
        core.project_service.PROJECTS_DIR = self.test_dir
    
    def teardown_method(self):
        """Cleanup test environment"""
        import shutil
        import core.project_service
        core.project_service.PROJECTS_DIR = self.original_projects_dir
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
    
    def test_initial_phase_is_inception(self):
        """新規プロジェクトはINCEPTIONフェーズで開始"""
        project = create_project(None, "テストプロジェクト", "test_user")
        manager = ProjectLifecycleManager(self.test_dir)
        
        current_phase = manager.get_current_phase(project.identifier)
        assert current_phase == ProjectPhase.INCEPTION
    
    def test_phase_advancement_with_requirements_met(self):
        """要件満たした場合のフェーズ進行"""
        project = create_project("test-project-001", "テストプロジェクト", "test_user")
        manager = ProjectLifecycleManager(self.test_dir)
        
        # INCEPTION → DEFINITION への進行テスト
        # INCEPTIONの要件: overview が設定されている（既に満たされている）
        
        can_advance, requirements = manager.can_advance_to_next_phase(project.identifier)
        assert can_advance == True
        assert len(requirements) == 0
        
        success = manager.advance_phase(project.identifier)
        assert success == True
        assert manager.get_current_phase(project.identifier) == ProjectPhase.DEFINITION
    
    def test_phase_advancement_blocked_by_requirements(self):
        """要件不足時のフェーズ進行ブロック"""
        project = create_project("test-project-002", "テストプロジェクト", "test_user")
        manager = ProjectLifecycleManager(self.test_dir)
        
        # DEFINITIONフェーズに手動で設定
        from core.project_service import update_project_field
        update_project_field(project.identifier, "phase", ProjectPhase.DEFINITION.value, self.test_dir)
        
        # DEFINITION → PLANNING への進行をテスト（チャーター未作成状態）
        can_advance, requirements = manager.can_advance_to_next_phase(project.identifier)
        assert can_advance == False
        assert any("charter_created" in req for req in requirements)
    
    def test_get_phase_progress(self):
        """フェーズ進捗情報の取得"""
        project = create_project("test-progress", "進捗テストプロジェクト", "test_user")
        manager = ProjectLifecycleManager(self.test_dir)
        
        progress = manager.get_phase_progress(project.identifier)
        
        assert progress["current_phase"] == ProjectPhase.INCEPTION.value
        assert progress["completion_percentage"] >= 0.0
        assert "can_advance" in progress
        assert "missing_requirements" in progress
        assert progress["next_phase"] == ProjectPhase.DEFINITION.value
    
    def test_phase_requirements_checklist(self):
        """フェーズ要件チェックリストの取得"""
        project = create_project("test-checklist", "チェックリストテスト", "test_user")
        manager = ProjectLifecycleManager(self.test_dir)
        
        checklist = manager.get_phase_requirements_checklist(project.identifier)
        
        assert checklist["phase"] == ProjectPhase.INCEPTION.value
        assert "requirements" in checklist
        assert "status" in checklist
        assert isinstance(checklist["status"], list)
    
    def test_closure_phase_cannot_advance(self):
        """CLOSUREフェーズからは進行不可"""
        project = create_project("test-closure", "完了テストプロジェクト", "test_user")
        manager = ProjectLifecycleManager(self.test_dir)
        
        # CLOSUREフェーズに手動設定
        from core.project_service import update_project_field
        update_project_field(project.identifier, "phase", ProjectPhase.CLOSURE.value, self.test_dir)
        
        can_advance, requirements = manager.can_advance_to_next_phase(project.identifier)
        assert can_advance == False
        assert "既に完了フェーズです" in requirements[0]
    
    def test_phase_transition_history_recording(self):
        """フェーズ遷移履歴の記録"""
        project = create_project("test-history", "履歴テストプロジェクト", "test_user")
        manager = ProjectLifecycleManager(self.test_dir)
        
        # フェーズ進行
        success = manager.advance_phase(project.identifier)
        assert success == True
        
        # 履歴確認
        progress = manager.get_phase_progress(project.identifier)
        phase_history = progress.get("phase_history", [])
        
        assert len(phase_history) == 1
        assert phase_history[0]["from_phase"] == ProjectPhase.INCEPTION.value
        assert phase_history[0]["to_phase"] == ProjectPhase.DEFINITION.value
        assert "timestamp" in phase_history[0]
    
    def test_completion_percentage_calculation(self):
        """完了率計算の確認"""
        project = create_project("test-completion", "完了率テスト", "test_user")
        manager = ProjectLifecycleManager(self.test_dir)
        
        # 各フェーズでの完了率確認
        phase_completions = {
            ProjectPhase.INCEPTION: 10.0,
            ProjectPhase.DEFINITION: 25.0,
            ProjectPhase.PLANNING: 40.0,
            ProjectPhase.EXECUTION: 70.0,
            ProjectPhase.MONITORING: 90.0,
            ProjectPhase.CLOSURE: 100.0
        }
        
        for phase, expected_completion in phase_completions.items():
            from core.project_service import update_project_field
            update_project_field(project.identifier, "phase", phase.value, self.test_dir)
            
            progress = manager.get_phase_progress(project.identifier)
            actual_completion = progress.get("completion_percentage", 0.0)
            
            assert actual_completion == expected_completion


class TestPhaseRequirements:
    """Test phase requirements functionality"""
    
    def test_get_requirements_for_all_phases(self):
        """全フェーズの要件定義確認"""
        for phase in ProjectPhase:
            if phase != ProjectPhase.CLOSURE:  # CLOSUREは次フェーズがない
                requirements = PhaseRequirements.get_requirements(phase)
                
                assert "name" in requirements
                assert "required_fields" in requirements
                assert "required_actions" in requirements
                assert "description" in requirements
    
    def test_inception_phase_requirements(self):
        """INCEPTIONフェーズの要件確認"""
        requirements = PhaseRequirements.get_requirements(ProjectPhase.INCEPTION)
        
        assert "overview" in requirements["required_fields"]
        assert len(requirements["required_actions"]) == 0  # アクション要件なし
    
    def test_definition_phase_requirements(self):
        """DEFINITIONフェーズの要件確認"""
        requirements = PhaseRequirements.get_requirements(ProjectPhase.DEFINITION)
        
        assert "charter_created" in requirements["required_actions"]
    
    def test_planning_phase_requirements(self):
        """PLANNINGフェーズの要件確認"""
        requirements = PhaseRequirements.get_requirements(ProjectPhase.PLANNING)
        
        assert "tasks" in requirements["required_fields"]
        assert "wbs_created" in requirements["required_actions"]
        assert "timeline_defined" in requirements["required_actions"]


class TestLifecycleIntegration:
    """Test lifecycle integration with project service"""
    
    def setup_method(self):
        """Setup test environment"""
        self.test_dir = Path(tempfile.mkdtemp())
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
    
    def test_phase_data_persistence(self):
        """フェーズ情報の永続化"""
        project = create_project("test-persistence", "永続化テスト", "test_user")
        manager = ProjectLifecycleManager(self.test_dir)
        
        # フェーズ変更
        manager.advance_phase(project.identifier)
        
        # 新しいマネージャーインスタンスで確認（再起動をシミュレート）
        new_manager = ProjectLifecycleManager(self.test_dir)
        phase = new_manager.get_current_phase(project.identifier)
        
        assert phase == ProjectPhase.DEFINITION  # 変更が保持されている
    
    def test_phase_change_audit_log(self):
        """フェーズ変更の監査ログ"""
        project = create_project("test-audit", "監査テスト", "test_user")
        manager = ProjectLifecycleManager(self.test_dir)
        
        from core.project_service import get_project
        initial_project = get_project(project.identifier, self.test_dir)
        initial_log_count = len(initial_project.get("change_log", []))
        
        manager.advance_phase(project.identifier)
        
        updated_project = get_project(project.identifier, self.test_dir)
        updated_log_count = len(updated_project.get("change_log", []))
        
        # Should have 2 new entries: field update + phase advancement
        assert updated_log_count >= initial_log_count + 1
        
        latest_log = updated_project["change_log"][-1]
        assert latest_log["type"] == "phase_advancement"
        assert "INCEPTION" in latest_log["description"]
        assert "DEFINITION" in latest_log["description"]
    
    def test_invalid_phase_advancement(self):
        """不正なフェーズ進行の処理"""
        project = create_project("test-invalid", "不正テスト", "test_user")
        manager = ProjectLifecycleManager(self.test_dir)
        
        # CLOSUREフェーズに設定
        from core.project_service import update_project_field
        update_project_field(project.identifier, "phase", ProjectPhase.CLOSURE.value, self.test_dir)
        
        # さらに進行を試行
        success = manager.advance_phase(project.identifier)
        assert success == False
        
        # フェーズが変更されていないことを確認
        assert manager.get_current_phase(project.identifier) == ProjectPhase.CLOSURE
    
    def test_project_not_found_error(self):
        """存在しないプロジェクトでのエラー処理"""
        manager = ProjectLifecycleManager(self.test_dir)
        
        with pytest.raises(ValueError, match="Project non-existent not found"):
            manager.get_current_phase("non-existent")