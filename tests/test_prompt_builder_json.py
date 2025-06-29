"""
Tests for core.prompt_builder JSON functionality
"""

import pytest
import json
from unittest.mock import patch, Mock
from pathlib import Path

from core.prompt_builder import PromptBuilder, create_prompt_builder


class TestPromptBuilder:
    """Test PromptBuilder class"""
    
    def test_initialization(self):
        """Test PromptBuilder initialization"""
        builder = PromptBuilder()
        assert builder is not None
        assert builder.rules_cache is not None
    
    def test_factory_function(self):
        """Test create_prompt_builder factory function"""
        builder = create_prompt_builder()
        assert isinstance(builder, PromptBuilder)
    
    def test_estimate_tokens(self):
        """Test token estimation"""
        builder = PromptBuilder()
        
        # Test basic estimation
        text = "This is a test"  # 14 characters
        tokens = builder.estimate_tokens(text)
        assert tokens == 14 // 4  # TOKEN_ESTIMATE_RATIO = 4
        
        # Test empty text
        assert builder.estimate_tokens("") == 0
        
        # Test longer text
        long_text = "A" * 400  # 400 characters
        assert builder.estimate_tokens(long_text) == 100
    
    def test_truncate_conversation_summary(self):
        """Test conversation summary truncation"""
        builder = PromptBuilder()
        
        # Test short summary (no truncation needed)
        short_summary = "Short conversation"
        result = builder.truncate_conversation_summary(short_summary, max_tokens=50)
        assert result == short_summary
        
        # Test long summary (truncation needed)
        long_lines = ["Line " + str(i) for i in range(100)]
        long_summary = "\n".join(long_lines)
        
        result = builder.truncate_conversation_summary(long_summary, max_tokens=10)
        assert len(result) < len(long_summary)
        assert "切り詰めました" in result
    
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.read_text')
    def test_load_prompt_rules_success(self, mock_read_text, mock_exists):
        """Test successful loading of prompt rules"""
        mock_exists.return_value = True
        mock_read_text.return_value = "# Test Rules\nThis is a test rule file."
        
        builder = PromptBuilder()
        builder.rules_cache = None  # Reset cache
        
        rules = builder._load_prompt_rules()
        assert rules == "# Test Rules\nThis is a test rule file."
        assert builder.rules_cache == rules
    
    @patch('pathlib.Path.exists')
    def test_load_prompt_rules_file_not_found(self, mock_exists):
        """Test handling of missing prompt rules file"""
        mock_exists.return_value = False
        
        builder = PromptBuilder()
        builder.rules_cache = None  # Reset cache
        
        rules = builder._load_prompt_rules()
        assert "Rules file not found" in rules
    
    def test_build_system_prompt(self):
        """Test system prompt building"""
        builder = PromptBuilder()
        
        # Mock rules content
        builder.rules_cache = "Test rules content"
        
        prompt = builder.build_system_prompt()
        assert "バーチャルプロジェクトマネージャー" in prompt
        assert "Test rules content" in prompt
        assert "<RULES>" not in prompt  # Should be replaced
    
    def test_build_unified_prompt(self):
        """Test unified prompt building"""
        builder = PromptBuilder()
        
        user_input = "Create a new project"
        project_context = {
            "identifier": "test-project",
            "status": "ACTIVE",
            "tasks": [
                {"description": "Task 1", "due_date": "2024-12-31"},
                {"description": "Task 2", "due_date": "2024-12-31"}
            ]
        }
        conversation_history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"}
        ]
        
        prompt = builder.build_unified_prompt(user_input, project_context, conversation_history)
        
        assert user_input in prompt
        assert "test-project" in prompt
        assert "ACTIVE" in prompt
        assert "Task 1" in prompt
        assert "Hello" in prompt
    
    def test_build_unified_prompt_token_limit(self):
        """Test prompt building with token limit enforcement"""
        builder = PromptBuilder()
        
        # Create a very long conversation history to trigger truncation
        long_history = []
        for i in range(100):
            long_history.append({
                "role": "user", 
                "content": f"This is a very long message number {i} " * 50
            })
        
        user_input = "Test"
        project_context = {}
        
        # Mock estimate_tokens to return high values
        with patch.object(builder, 'estimate_tokens') as mock_estimate:
            # First call (for full prompt) returns high value, second call (for conversation) returns normal
            mock_estimate.side_effect = [1500, 200]
            
            prompt = builder.build_unified_prompt(user_input, project_context, long_history)
            
            # Should have called estimate_tokens
            assert mock_estimate.called
            assert user_input in prompt
    
    def test_safe_json_response_valid(self):
        """Test safe JSON response generation with valid data"""
        builder = PromptBuilder()
        
        response_dict = {
            "intent": "project_management",
            "action_type": "create_project",
            "reasoning": "ユーザーがプロジェクト作成を要求",
            "confidence": 0.9,
            "target_items": [],
            "response_content": "プロジェクトを作成します",
            "suggested_follow_ups": ["次のステップは？"]
        }
        
        json_str = builder.safe_json_response(response_dict)
        
        # Should be valid JSON
        parsed = json.loads(json_str)
        assert parsed == response_dict
        
        # Should preserve Japanese characters
        assert "ユーザーがプロジェクト作成を要求" in json_str
    
    def test_safe_json_response_invalid(self):
        """Test safe JSON response generation with invalid data"""
        builder = PromptBuilder()
        
        # Create an object that can't be serialized
        class UnserializableClass:
            pass
        
        response_dict = {
            "invalid": UnserializableClass()
        }
        
        json_str = builder.safe_json_response(response_dict)
        
        # Should return error response
        parsed = json.loads(json_str)
        assert parsed["intent"] == "error"
        assert parsed["action_type"] == "processing_error"
        assert "JSON serialization failed" in parsed["reasoning"]
    
    def test_summarize_project_context(self):
        """Test project context summarization"""
        builder = PromptBuilder()
        
        # Test with full context
        context = {
            "identifier": "test-project",
            "status": "ACTIVE",
            "tasks": [
                {"description": "Task 1", "due_date": "2024-12-31"},
                {"description": "Task 2", "due_date": "2024-12-31"},
                {"description": "Task 3", "due_date": "2024-12-31"},
                {"description": "Task 4", "due_date": "2024-12-31"}
            ]
        }
        
        summary = builder._summarize_project_context(context)
        assert "test-project" in summary
        assert "ACTIVE" in summary
        assert "4件" in summary
        assert "Task 2" in summary  # Should include recent tasks
        assert "Task 4" in summary  # Should include recent tasks
        assert "Task 1" not in summary  # Should not include old tasks (only last 3)
        
        # Test with empty context
        empty_summary = builder._summarize_project_context({})
        assert "プロジェクトが選択されていません" in empty_summary
    
    def test_summarize_conversation_history(self):
        """Test conversation history summarization"""
        builder = PromptBuilder()
        
        # Test with conversation history
        history = [
            {"role": "user", "content": "Hello there!"},
            {"role": "assistant", "content": "Hi! How can I help you?"},
            {"role": "user", "content": "I want to create a project"},
            {"role": "assistant", "content": "Sure! What kind of project?"}
        ]
        
        summary = builder._summarize_conversation_history(history)
        assert "Hello there!" in summary
        assert "ユーザー" in summary
        assert "AI" in summary
        
        # Test with empty history
        empty_summary = builder._summarize_conversation_history([])
        assert "新しい会話です" in empty_summary
        
        # Test with long conversation (should limit to 6 messages)
        long_history = []
        for i in range(10):
            long_history.append({"role": "user", "content": f"Message {i}"})
        
        long_summary = builder._summarize_conversation_history(long_history)
        assert "Message 9" in long_summary  # Should include recent messages
        assert "Message 0" not in long_summary  # Should not include old messages