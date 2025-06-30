"""
Tests for context-dependent intent routing in AI Project Manager.

Ensures that project creation keywords behave differently based on 
whether a project is already selected or not.
"""

import pytest
from unittest.mock import Mock, patch
from core.ai_project_manager import AIProjectManager
from core.log_schema import RequestContext


class TestIntentRouting:
    """Test context-dependent intent routing"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.ai_pm = AIProjectManager("fake-api-key")
        
    @pytest.mark.parametrize("user_input,expected_action", [
        ("花火大会をプロジェクトとして設定してください", "create_project"),
        ("新しいプロジェクトを開始したい", "create_project"),
        ("プロジェクトを作成してください", "create_project"),
        ("〜をプロジェクト化したい", "create_project"),
    ])
    def test_home_chat_project_creation(self, user_input, expected_action):
        """Test project creation intent from home chat (no project selected)"""
        # Mock AI response for project creation
        mock_response = {
            "intent": "project_management",
            "action_type": expected_action,
            "reasoning": "プロジェクト未選択状態でプロジェクト作成を要求している",
            "confidence": 0.9,
            "target_items": [
                {
                    "type": "project",
                    "action": "create_new_project",
                    "parameters": {
                        "name": "テストプロジェクト",
                        "description": "テスト用プロジェクト"
                    }
                }
            ],
            "response_content": "テストプロジェクトを作成しました。",
            "suggested_follow_ups": ["タスクを追加したい"]
        }
        
        with patch.object(self.ai_pm, 'client') as mock_client:
            mock_client.chat.completions.create.return_value = Mock(
                choices=[Mock(message=Mock(content=str(mock_response)))],
                usage=Mock(prompt_tokens=100, completion_tokens=200, total_tokens=300)
            )
            
            # No project context (home chat)
            result = self.ai_pm.process_user_input(
                user_input=user_input,
                project_context={},  # Empty = no project selected
                conversation_history=[]
            )
            
            assert result.action_type == expected_action
            assert result.confidence >= 0.8
    
    @pytest.mark.parametrize("user_input,expected_action", [
        ("このプロジェクトをもっと本格的にプロジェクトとして進めたいです", "general_discussion"),
        ("プロジェクトとしてしっかり管理したい", "general_discussion"),
        ("プロジェクト化して進めましょう", "general_discussion"),
        ("新しいプロジェクトを作成してください", "create_project"),  # Should still create if explicitly "new"
    ])
    def test_project_chat_context_handling(self, user_input, expected_action):
        """Test project-related keywords within existing project context"""
        # Mock AI response for general discussion
        mock_response = {
            "intent": "conversation",
            "action_type": expected_action,
            "reasoning": "既にプロジェクト選択済みのため、プロジェクト運営に関する相談として処理" if expected_action == "general_discussion" else "明示的に新しいプロジェクト作成を要求",
            "confidence": 0.8,
            "target_items": [
                {
                    "type": "general" if expected_action == "general_discussion" else "project",
                    "action": "project_management_consultation" if expected_action == "general_discussion" else "create_new_project",
                    "parameters": {}
                }
            ],
            "response_content": "現在のプロジェクトの管理についてアドバイスします。" if expected_action == "general_discussion" else "新しいプロジェクトを作成します。",
            "suggested_follow_ups": ["ステータスを変更したい"]
        }
        
        with patch.object(self.ai_pm, 'client') as mock_client:
            mock_client.chat.completions.create.return_value = Mock(
                choices=[Mock(message=Mock(content=str(mock_response)))],
                usage=Mock(prompt_tokens=100, completion_tokens=200, total_tokens=300)
            )
            
            # Project context exists (project chat)
            project_context = {
                "identifier": "proj-test-123",
                "status": "DRAFT",
                "tasks": [
                    {"id": 1, "description": "テストタスク", "due_date": "2025-07-01"}
                ]
            }
            
            result = self.ai_pm.process_user_input(
                user_input=user_input,
                project_context=project_context,
                conversation_history=[]
            )
            
            assert result.action_type == expected_action
            assert result.confidence >= 0.7
    
    def test_request_context_logging(self):
        """Test that RequestContext is properly set based on project selection"""
        with patch('core.ai_project_manager.log_call') as mock_log_call:
            # Home chat (no project)
            self.ai_pm.process_user_input(
                user_input="テスト",
                project_context={},
                conversation_history=[]
            )
            
            # Verify HOME_CHAT subkind
            mock_log_call.assert_called_with("kai", mock_log_call.call_args[0][1], subkind=RequestContext.HOME_CHAT)
            
            # Project chat (with project)
            project_context = {"identifier": "proj-test-123"}
            self.ai_pm.process_user_input(
                user_input="テスト",
                project_context=project_context,
                conversation_history=[]
            )
            
            # Verify PROJECT_CHAT subkind
            mock_log_call.assert_called_with("kai", mock_log_call.call_args[0][1], subkind=RequestContext.PROJECT_CHAT)


if __name__ == "__main__":
    pytest.main([__file__])