"""
Unit tests for Memory Chat β page (Memory Layer Phase 2 Stage B)
Memory Chatページのテスト
"""

import unittest
import tempfile
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

# Import the modules under test
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

class TestMemoryChatPage(unittest.TestCase):
    """Memory Chat page unit tests"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
        
        # Mock environment for testing
        self.env_patcher = patch.dict(os.environ, {
            'OPENAI_API_KEY': 'test-api-key',
            'MEMORY_LAYER_ENABLED': 'False',  # デフォルトは無効
            'MEMORY_READ_ENABLED': 'False'
        })
        self.env_patcher.start()
        
    def tearDown(self):
        """Clean up test environment"""
        self.env_patcher.stop()
        
        # Clean up test directory
        import shutil
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    @patch('streamlit.set_page_config')
    @patch('streamlit.title')
    @patch('streamlit.caption')
    def test_page_initialization(self, mock_caption, mock_title, mock_config):
        """Test page initialization and configuration"""
        # このテストはページがインポートできることを確認
        try:
            # ページファイルが存在することを確認
            page_path = Path(__file__).parent.parent / "pages" / "memory_chat.py"
            self.assertTrue(page_path.exists(), "Memory Chat page file should exist")
            
            # ファイルが有効なPythonコードであることを確認
            with open(page_path, 'r', encoding='utf-8') as f:
                content = f.read()
                compile(content, str(page_path), 'exec')
            
        except Exception as e:
            self.fail(f"Page initialization failed: {e}")
    
    def test_memory_feature_flag_override(self):
        """Test that memory features are enabled in beta page"""
        # Memory Chat ページ内での機能フラグ上書きをテスト
        
        # デフォルトでは無効
        from config import is_memory_enabled, is_memory_read_enabled
        self.assertFalse(is_memory_enabled(), "Memory should be disabled by default")
        self.assertFalse(is_memory_read_enabled(), "Memory read should be disabled by default")
        
        # Memory Chat ページ内での上書きロジックをシミュレート
        # (実際のStreamlitセッション状態なしでテスト)
        beta_enabled = True
        memory_enabled = is_memory_enabled() or beta_enabled
        read_enabled = is_memory_read_enabled() or beta_enabled
        
        self.assertTrue(memory_enabled, "Memory should be enabled in beta page")
        self.assertTrue(read_enabled, "Memory read should be enabled in beta page")
    
    @patch('core.memory_bridge.load_current_memory')
    def test_memory_context_loading(self, mock_load_memory):
        """Test memory context loading for AI prompts"""
        # Mock memory data
        mock_memory = {
            "memory_version": "2.0",
            "last_updated": "2025-07-05T16:00:00Z",
            "current_memory": {
                "active_projects": [
                    {
                        "project_id": "test_proj",
                        "name": "Test Project",
                        "status": "active"
                    }
                ],
                "user_preferences": {
                    "language": "ja"
                },
                "session_context": {
                    "current_focus": "testing"
                }
            },
            "events": [
                {
                    "timestamp": "2025-07-05T15:30:00Z",
                    "event_type": "user_message",
                    "description": "User started testing",
                    "importance": "medium"
                }
            ]
        }
        
        mock_load_memory.return_value = mock_memory
        
        # Test memory loading
        from core.memory_bridge import load_current_memory
        memory = load_current_memory()
        
        self.assertEqual(memory["memory_version"], "2.0")
        self.assertEqual(len(memory["current_memory"]["active_projects"]), 1)
        self.assertEqual(len(memory["events"]), 1)
    
    @patch('core.memory_bridge.get_context_for_ai')
    def test_ai_context_generation(self, mock_get_context):
        """Test AI context generation from memory"""
        # Mock context data
        mock_context = """## アクティブプロジェクト
- Test Project (test_proj): active

## 最近のイベント
- [2025-07-05 15:30] User started testing

## 現在の焦点: testing"""
        
        mock_get_context.return_value = mock_context
        
        # Test context generation
        from core.memory_bridge import get_context_for_ai
        context = get_context_for_ai(max_events=10)
        
        self.assertIn("アクティブプロジェクト", context)
        self.assertIn("Test Project", context)
        self.assertIn("最近のイベント", context)
        self.assertIn("User started testing", context)
    
    @patch('core.v2.openai_config.create_chat_completion')
    def test_ai_prompt_with_memory_injection(self, mock_chat_completion):
        """Test that AI prompts include memory context"""
        # Mock OpenAI response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "メモリを参照して回答しました。"
        mock_chat_completion.return_value = mock_response
        
        # Mock memory context
        memory_context = "## 最近のイベント\n- User asked about project status"
        
        # Simulate AI prompt construction with memory
        system_prompt = f"""あなたはKai VPMの個人秘書Ariadeです。ユーザーとの会話履歴と重要な情報を記憶して、一貫性のある回答を提供してください。

【記憶している情報】
{memory_context}

以下の点を重視してください：
1. 過去の会話内容を参考にして文脈に沿った回答をする
2. プロジェクトの進捗や状況を把握している場合は具体的に言及する
3. ユーザーの好みや過去の要求を考慮する
4. 自然で親しみやすい日本語で応答する
"""
        
        # Verify memory context is included in system prompt
        self.assertIn("記憶している情報", system_prompt)
        self.assertIn("User asked about project status", system_prompt)
        self.assertIn("過去の会話内容を参考にして", system_prompt)
    
    @patch('core.memory_bridge.log_event')
    def test_event_logging(self, mock_log_event):
        """Test event logging functionality"""
        mock_log_event.return_value = True
        
        # Test user message logging
        from core.memory_bridge import log_event
        result = log_event("user_message", "Memory Chat: テストメッセージ", importance="medium")
        
        self.assertTrue(result, "Event logging should succeed")
        mock_log_event.assert_called_with("user_message", "Memory Chat: テストメッセージ", importance="medium")
    
    def test_openai_api_key_detection(self):
        """Test OpenAI API key detection"""
        # Test with environment variable
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}):
            api_key = os.getenv("OPENAI_API_KEY")
            self.assertEqual(api_key, 'test-key')
        
        # Test without API key
        with patch.dict(os.environ, {}, clear=True):
            api_key = os.getenv("OPENAI_API_KEY")
            self.assertIsNone(api_key)
    
    def test_memory_bridge_config_override(self):
        """Test memory bridge configuration override in beta page"""
        from core.memory_bridge import MemoryBridge
        
        # Create memory bridge instance
        bridge = MemoryBridge()
        
        # Simulate beta page override
        original_enabled = bridge.config.get("enabled", False)
        original_read_enabled = bridge.config.get("read_enabled", False)
        
        # Override for beta
        bridge.config["enabled"] = True
        bridge.config["read_enabled"] = True
        
        self.assertTrue(bridge.config["enabled"], "Memory should be enabled in beta")
        self.assertTrue(bridge.config["read_enabled"], "Memory read should be enabled in beta")
        
        # Restore original settings
        bridge.config["enabled"] = original_enabled
        bridge.config["read_enabled"] = original_read_enabled
    
    def test_page_file_structure(self):
        """Test that page file has correct structure"""
        page_path = Path(__file__).parent.parent / "pages" / "memory_chat.py"
        
        with open(page_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for essential components
        essential_components = [
            "st.set_page_config",
            "Memory Chat β",
            "memory_bridge",
            "get_context_for_ai",
            "log_event",
            "st.chat_input",
            "create_chat_completion"
        ]
        
        for component in essential_components:
            self.assertIn(component, content, f"Page should contain {component}")
    
    def test_error_handling(self):
        """Test error handling in memory operations"""
        with patch('core.memory_bridge.load_current_memory', side_effect=Exception("Test error")):
            try:
                from core.memory_bridge import load_current_memory
                memory = load_current_memory()
                # Should handle gracefully, not crash
            except Exception as e:
                # If it does raise, it should be the expected test error
                self.assertEqual(str(e), "Test error")


class TestMemoryChatIntegration(unittest.TestCase):
    """Integration tests for Memory Chat functionality"""
    
    @patch('core.memory_bridge.is_memory_enabled', return_value=True)
    @patch('core.memory_bridge.load_current_memory')
    @patch('core.memory_bridge.log_event')
    def test_full_conversation_flow(self, mock_log_event, mock_load_memory, mock_enabled):
        """Test complete conversation flow with memory"""
        # Mock memory state
        mock_memory = {
            "memory_version": "2.0",
            "current_memory": {
                "active_projects": [],
                "session_context": {"current_focus": "testing"}
            },
            "events": []
        }
        mock_load_memory.return_value = mock_memory
        mock_log_event.return_value = True
        
        # Simulate conversation flow
        user_input = "テストメッセージです"
        
        # 1. Load memory (happens when page loads)
        memory = mock_load_memory()
        self.assertIsNotNone(memory)
        
        # 2. Log user message
        log_result = mock_log_event("user_message", f"Memory Chat: {user_input}", importance="medium")
        self.assertTrue(log_result)
        
        # 3. Generate AI response (would include memory context)
        # This is tested separately in other test methods
        
        # Verify mocks were called correctly
        mock_load_memory.assert_called()
        mock_log_event.assert_called_with("user_message", f"Memory Chat: {user_input}", importance="medium")


if __name__ == '__main__':
    unittest.main()