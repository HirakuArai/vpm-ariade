# --- tests/test_conversation_engine.py ---
"""
Test PhaseAwareConversationEngine functionality
"""

import pytest
import tempfile
import json
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.conversation_engine import PhaseAwareConversationEngine, ConversationResponse
from core.models import ProjectPhase
from core.project_service import create_project, update_project_field


class TestPhaseAwareConversationEngine:
    """Test phase-aware conversation engine functionality"""
    
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
    
    def create_test_project(self, phase: ProjectPhase = ProjectPhase.INCEPTION) -> str:
        """テスト用プロジェクトを作成"""
        project = create_project(None, "テストプロジェクト", "test_user")
        if phase != ProjectPhase.INCEPTION:
            update_project_field(project.identifier, "phase", phase.value, self.test_dir)
        return project.identifier
    
    def test_engine_initialization(self):
        """会話エンジンの初期化"""
        project_id = self.create_test_project()
        engine = PhaseAwareConversationEngine(project_id, self.test_dir)
        
        assert engine.project_id == project_id
        assert engine.current_phase == ProjectPhase.INCEPTION
        assert engine.project_data is not None
    
    def test_engine_initialization_with_nonexistent_project(self):
        """存在しないプロジェクトでの初期化エラー"""
        with pytest.raises(ValueError, match="Project non-existent not found"):
            PhaseAwareConversationEngine("non-existent", self.test_dir)
    
    def test_inception_phase_conversation(self):
        """INCEPTIONフェーズでの会話応答"""
        project_id = self.create_test_project(ProjectPhase.INCEPTION)
        engine = PhaseAwareConversationEngine(project_id, self.test_dir)
        
        response = engine.generate_response("Webアプリを作りたい")
        
        # 基本的な応答構造の確認
        assert isinstance(response, ConversationResponse)
        assert response.phase == ProjectPhase.INCEPTION
        assert response.content is not None
        assert isinstance(response.suggested_actions, list)
        assert isinstance(response.next_actions, list)
        
        # INCEPTION特有の要素確認
        assert len(response.suggested_actions) > 0
        assert any("目的" in action.get("description", "") for action in response.suggested_actions)
        assert any("目的" in action for action in response.next_actions)
    
    def test_definition_phase_conversation(self):
        """DEFINITIONフェーズでの会話応答"""
        project_id = self.create_test_project(ProjectPhase.DEFINITION)
        engine = PhaseAwareConversationEngine(project_id, self.test_dir)
        
        response = engine.generate_response("ユーザー登録機能が必要")
        
        assert response.phase == ProjectPhase.DEFINITION
        assert len(response.suggested_actions) > 0
        
        # DEFINITION特有の要素確認
        action_types = [action.get("type") for action in response.suggested_actions]
        assert "create_charter" in action_types or "define_scope" in action_types
    
    def test_planning_phase_conversation(self):
        """PLANNINGフェーズでの会話応答"""
        project_id = self.create_test_project(ProjectPhase.PLANNING)
        engine = PhaseAwareConversationEngine(project_id, self.test_dir)
        
        response = engine.generate_response("タスクの工数を見積もりたい")
        
        assert response.phase == ProjectPhase.PLANNING
        
        # PLANNING特有の要素確認
        action_types = [action.get("type") for action in response.suggested_actions]
        assert "create_wbs" in action_types or "schedule_planning" in action_types
    
    def test_execution_phase_conversation(self):
        """EXECUTIONフェーズでの会話応答"""
        project_id = self.create_test_project(ProjectPhase.EXECUTION)
        
        # テスト用タスクを追加
        from core.project_service import add_task
        add_task(project_id, "テストタスク", "2024-12-31", "test_user", self.test_dir)
        
        engine = PhaseAwareConversationEngine(project_id, self.test_dir)
        response = engine.generate_response("ログイン機能でエラーが発生している")
        
        assert response.phase == ProjectPhase.EXECUTION
        
        # EXECUTION特有の要素確認
        action_types = [action.get("type") for action in response.suggested_actions]
        assert "track_progress" in action_types or "resolve_issues" in action_types
        
        # 課題関連の更新提案があることを確認
        assert len(response.project_updates) > 0
    
    def test_monitoring_phase_conversation(self):
        """MONITORINGフェーズでの会話応答"""
        project_id = self.create_test_project(ProjectPhase.MONITORING)
        engine = PhaseAwareConversationEngine(project_id, self.test_dir)
        
        response = engine.generate_response("品質レビューの結果について")
        
        assert response.phase == ProjectPhase.MONITORING
        
        # MONITORING特有の要素確認
        action_types = [action.get("type") for action in response.suggested_actions]
        assert "quality_review" in action_types
    
    def test_closure_phase_conversation(self):
        """CLOSUREフェーズでの会話応答"""
        project_id = self.create_test_project(ProjectPhase.CLOSURE)
        engine = PhaseAwareConversationEngine(project_id, self.test_dir)
        
        response = engine.generate_response("プロジェクトの完了報告")
        
        assert response.phase == ProjectPhase.CLOSURE
        
        # CLOSURE特有の要素確認
        action_types = [action.get("type") for action in response.suggested_actions]
        assert "final_review" in action_types or "documentation" in action_types
    
    def test_system_prompt_generation(self):
        """システムプロンプトの生成"""
        project_id = self.create_test_project(ProjectPhase.EXECUTION)
        engine = PhaseAwareConversationEngine(project_id, self.test_dir)
        
        system_prompt = engine.get_system_prompt()
        
        assert isinstance(system_prompt, str)
        assert len(system_prompt) > 0
        assert "プロジェクトマネージャー" in system_prompt
        assert "EXECUTION" in system_prompt
        assert "日本語" in system_prompt
    
    def test_project_context_in_system_prompt(self):
        """システムプロンプトにプロジェクトコンテキストが含まれる"""
        project_id = self.create_test_project()
        engine = PhaseAwareConversationEngine(project_id, self.test_dir)
        
        system_prompt = engine.get_system_prompt()
        
        # プロジェクト情報が含まれているか確認
        assert project_id in system_prompt
        assert "テストプロジェクト" in system_prompt
        assert "INCEPTION" in system_prompt
    
    def test_conversation_response_structure(self):
        """会話応答の構造確認"""
        project_id = self.create_test_project()
        engine = PhaseAwareConversationEngine(project_id, self.test_dir)
        
        response = engine.generate_response("プロジェクトの進捗は？")
        
        # ConversationResponseの必須フィールド確認
        assert hasattr(response, 'content')
        assert hasattr(response, 'phase')
        assert hasattr(response, 'suggested_actions')
        assert hasattr(response, 'project_updates')
        assert hasattr(response, 'next_actions')
        assert hasattr(response, 'confidence')
        
        # データ型確認
        assert isinstance(response.content, str)
        assert isinstance(response.phase, ProjectPhase)
        assert isinstance(response.suggested_actions, list)
        assert isinstance(response.project_updates, list)
        assert isinstance(response.next_actions, list)
        assert isinstance(response.confidence, float)
    
    def test_project_updates_extraction_inception(self):
        """INCEPTION段階でのプロジェクト更新抽出"""
        project_id = self.create_test_project(ProjectPhase.INCEPTION)
        engine = PhaseAwareConversationEngine(project_id, self.test_dir)
        
        response = engine.generate_response("このプロジェクトの目的は売上向上です")
        
        # 目的に関する更新提案があることを確認
        updates = response.project_updates
        assert len(updates) > 0
        
        purpose_update = next((u for u in updates if u.get("field") == "purpose"), None)
        assert purpose_update is not None
        assert "売上向上" in purpose_update.get("value", "")
    
    def test_project_updates_extraction_execution(self):
        """EXECUTION段階でのプロジェクト更新抽出"""
        project_id = self.create_test_project(ProjectPhase.EXECUTION)
        engine = PhaseAwareConversationEngine(project_id, self.test_dir)
        
        response = engine.generate_response("ログイン機能の実装が完了しました")
        
        # 完了に関する更新提案があることを確認
        updates = response.project_updates
        completion_update = next((u for u in updates if u.get("field") == "task_completion"), None)
        assert completion_update is not None
    
    def test_phase_specific_action_suggestions(self):
        """フェーズ特化型アクション提案"""
        phases_and_expected_actions = [
            (ProjectPhase.INCEPTION, ["clarify_purpose", "identify_stakeholders"]),
            (ProjectPhase.DEFINITION, ["create_charter", "define_scope"]),
            (ProjectPhase.PLANNING, ["create_wbs", "schedule_planning"]),
            (ProjectPhase.EXECUTION, ["track_progress", "resolve_issues"]),
            (ProjectPhase.MONITORING, ["quality_review"]),
            (ProjectPhase.CLOSURE, ["final_review", "documentation"])
        ]
        
        for phase, expected_action_types in phases_and_expected_actions:
            project_id = self.create_test_project(phase)
            engine = PhaseAwareConversationEngine(project_id, self.test_dir)
            
            response = engine.generate_response("進捗を教えて")
            suggested_types = [action.get("type") for action in response.suggested_actions]
            
            # 少なくとも1つの期待されるアクションタイプが含まれている
            assert any(expected_type in suggested_types for expected_type in expected_action_types), \
                f"Phase {phase.value} should include actions from {expected_action_types}, got {suggested_types}"


class TestConversationIntegration:
    """Test conversation engine integration with lifecycle manager"""
    
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
    
    def test_engine_updates_with_phase_changes(self):
        """フェーズ変更に対する会話エンジンの対応"""
        project = create_project("test-phase-change", "フェーズ変更テスト", "test_user")
        
        # INCEPTIONフェーズでエンジン作成
        engine1 = PhaseAwareConversationEngine(project.identifier, self.test_dir)
        response1 = engine1.generate_response("進捗は？")
        assert response1.phase == ProjectPhase.INCEPTION
        
        # フェーズを変更
        update_project_field(project.identifier, "phase", ProjectPhase.EXECUTION.value, self.test_dir)
        
        # 新しいエンジンインスタンスで確認
        engine2 = PhaseAwareConversationEngine(project.identifier, self.test_dir)
        response2 = engine2.generate_response("進捗は？")
        assert response2.phase == ProjectPhase.EXECUTION
        
        # 応答内容が異なることを確認
        assert response1.content != response2.content
    
    def test_conversation_adapts_to_project_data(self):
        """プロジェクトデータに応じた会話適応"""
        project = create_project("test-adaptation", "適応テスト", "test_user")
        
        # タスクなしの状態
        engine = PhaseAwareConversationEngine(project.identifier, self.test_dir)
        response_no_tasks = engine.generate_response("現在の状況は？")
        
        # タスクを追加
        from core.project_service import add_task
        add_task(project.identifier, "テストタスク1", "2024-12-31", "test_user", self.test_dir)
        add_task(project.identifier, "テストタスク2", "2025-01-15", "test_user", self.test_dir)
        
        # EXECUTIONフェーズに変更
        update_project_field(project.identifier, "phase", ProjectPhase.EXECUTION.value, self.test_dir)
        
        # 新しいエンジンで確認
        engine_with_tasks = PhaseAwareConversationEngine(project.identifier, self.test_dir)
        response_with_tasks = engine_with_tasks.generate_response("現在の状況は？")
        
        # EXECUTIONフェーズでタスクがある場合の応答であることを確認
        assert response_with_tasks.phase == ProjectPhase.EXECUTION
        assert len(response_with_tasks.suggested_actions) > 0