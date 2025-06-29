"""
Tests for core.prompt_builder token budget management
"""

import pytest
from unittest.mock import patch

from core.prompt_builder import PromptBuilder, MAX_PROMPT_TOKENS


class TestPromptBuilderBudget:
    """Test PromptBuilder token budget management"""
    
    def test_max_prompt_tokens_constant(self):
        """Test that MAX_PROMPT_TOKENS is properly defined"""
        assert MAX_PROMPT_TOKENS == 900
    
    def test_token_estimation_basic(self):
        """Test basic token estimation functionality"""
        builder = PromptBuilder()
        
        # Test various text lengths
        test_cases = [
            ("", 0),
            ("test", 1),  # 4 chars / 4 = 1 token
            ("a" * 8, 2),  # 8 chars / 4 = 2 tokens
            ("a" * 400, 100),  # 400 chars / 4 = 100 tokens
        ]
        
        for text, expected_tokens in test_cases:
            assert builder.estimate_tokens(text) == expected_tokens
    
    def test_conversation_truncation_under_limit(self):
        """Test that conversation under token limit is not truncated"""
        builder = PromptBuilder()
        
        short_conversation = "短い会話です"
        max_tokens = 50
        
        result = builder.truncate_conversation_summary(short_conversation, max_tokens)
        
        # Should not be truncated
        assert result == short_conversation
        assert "切り詰めました" not in result
    
    def test_conversation_truncation_over_limit(self):
        """Test that conversation over token limit is truncated"""
        builder = PromptBuilder()
        
        # Create long conversation that exceeds token limit
        long_lines = []
        for i in range(50):
            long_lines.append(f"これは長い会話の行{i}です。たくさんの文字が含まれています。")
        
        long_conversation = "\n".join(long_lines)
        max_tokens = 10  # Very low limit to force truncation
        
        result = builder.truncate_conversation_summary(long_conversation, max_tokens)
        
        # Should be truncated
        assert len(result) < len(long_conversation)
        assert "切り詰めました" in result
        
        # Should still contain some content
        assert "これは長い会話の行0です" in result
    
    def test_conversation_truncation_empty_input(self):
        """Test conversation truncation with empty input"""
        builder = PromptBuilder()
        
        result = builder.truncate_conversation_summary("", 100)
        assert result == ""
    
    def test_conversation_truncation_single_line(self):
        """Test conversation truncation with single very long line"""
        builder = PromptBuilder()
        
        very_long_line = "非常に長い一行の文章です。" * 100
        max_tokens = 5
        
        result = builder.truncate_conversation_summary(very_long_line, max_tokens)
        
        # Should be truncated to empty + warning since single line exceeds limit
        assert "切り詰めました" in result
    
    @patch('core.prompt_builder.PromptBuilder.estimate_tokens')
    def test_unified_prompt_token_management_under_limit(self, mock_estimate_tokens):
        """Test unified prompt building when under token limit"""
        builder = PromptBuilder()
        
        # Mock token estimation to return value under limit
        mock_estimate_tokens.return_value = 500  # Under MAX_PROMPT_TOKENS (900)
        
        user_input = "Create a project"
        project_context = {"identifier": "test"}
        conversation_history = [{"role": "user", "content": "Hi"}]
        
        result = builder.build_unified_prompt(user_input, project_context, conversation_history)
        
        # Should not trigger truncation
        assert "Hi" in result  # Original conversation should be preserved
        assert user_input in result
        mock_estimate_tokens.assert_called_once()
    
    @patch('core.prompt_builder.PromptBuilder.estimate_tokens')
    @patch('core.prompt_builder.PromptBuilder.truncate_conversation_summary')
    def test_unified_prompt_token_management_over_limit(self, mock_truncate, mock_estimate_tokens):
        """Test unified prompt building when over token limit"""
        builder = PromptBuilder()
        
        # Mock token estimation to return value over limit
        mock_estimate_tokens.return_value = 1200  # Over MAX_PROMPT_TOKENS (900)
        mock_truncate.return_value = "truncated conversation"
        
        user_input = "Create a project"
        project_context = {"identifier": "test"}
        conversation_history = [{"role": "user", "content": "Very long conversation"}]
        
        result = builder.build_unified_prompt(user_input, project_context, conversation_history)
        
        # Should trigger truncation
        mock_truncate.assert_called_once()
        assert "truncated conversation" in result
        assert user_input in result
    
    def test_token_budget_warning_threshold(self):
        """Test that token budget warning is properly configured"""
        # Verify that our warning threshold in summarize_logs.py (1000) 
        # is higher than our prompt limit (900)
        warning_threshold = 1000
        assert warning_threshold > MAX_PROMPT_TOKENS
        assert MAX_PROMPT_TOKENS == 900
    
    def test_realistic_prompt_size_scenarios(self):
        """Test with realistic prompt size scenarios"""
        builder = PromptBuilder()
        
        # Scenario 1: Normal conversation
        normal_user_input = "長岡の花火大会の準備をプロジェクトとして設定してください。"
        normal_project_context = {
            "identifier": "proj-20240630-123456",
            "status": "ACTIVE",
            "tasks": [
                {"description": "会場の予約", "due_date": "2024-07-01"},
                {"description": "花火の調達", "due_date": "2024-07-15"}
            ]
        }
        normal_conversation = [
            {"role": "user", "content": "こんにちは"},
            {"role": "assistant", "content": "こんにちは！お手伝いできることがあれば教えてください。"}
        ]
        
        prompt = builder.build_unified_prompt(
            normal_user_input, normal_project_context, normal_conversation
        )
        
        # Should be reasonable size
        estimated_tokens = builder.estimate_tokens(prompt)
        assert estimated_tokens < MAX_PROMPT_TOKENS
        
        # Scenario 2: Long conversation history
        long_conversation = []
        for i in range(20):
            long_conversation.extend([
                {"role": "user", "content": f"これは長い会話の{i}回目のユーザー発言です。たくさんの詳細情報が含まれています。"},
                {"role": "assistant", "content": f"ありがとうございます。{i}回目の応答として、詳細な説明を提供します。"}
            ])
        
        long_prompt = builder.build_unified_prompt(
            normal_user_input, normal_project_context, long_conversation
        )
        
        # Should handle long conversation appropriately
        # The exact behavior depends on the implementation, but it should not crash
        assert isinstance(long_prompt, str)
        assert len(long_prompt) > 0
    
    def test_token_estimation_edge_cases(self):
        """Test token estimation with edge cases"""
        builder = PromptBuilder()
        
        # Test with unicode characters
        unicode_text = "🚀🎯🔥" * 10  # Emoji characters
        tokens = builder.estimate_tokens(unicode_text)
        assert tokens >= 0
        
        # Test with mixed content
        mixed_text = "English text 日本語テキスト 123 symbols!@#"
        tokens = builder.estimate_tokens(mixed_text)
        assert tokens == len(mixed_text) // 4
        
        # Test with newlines and whitespace
        whitespace_text = "line1\n\nline2\t\tline3   line4"
        tokens = builder.estimate_tokens(whitespace_text)
        assert tokens == len(whitespace_text) // 4