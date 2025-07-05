"""
Unit tests for LLM Logger
LLMコールログ機能のテスト
"""

import unittest
import tempfile
import os
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

# Import the module under test
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.llm_logger import (
    log_llm_call, count_today_calls, get_today_stats, 
    estimate_cost, render_llm_stats_for_memory_chat,
    get_recent_llm_calls, format_messages_for_display, rotate_log_if_needed
)


class TestLLMLogger(unittest.TestCase):
    """LLM Logger unit tests"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
        
        # Mock the LLM_LOGS_DIR to use test directory
        self.logs_dir_patcher = patch('core.llm_logger.LLM_LOGS_DIR', Path(self.test_dir))
        self.logs_dir_patcher.start()
        
    def tearDown(self):
        """Clean up test environment"""
        self.logs_dir_patcher.stop()
        
        # Clean up test directory
        import shutil
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_log_llm_call(self):
        """Test LLM call logging (仕様書準拠版)"""
        # テストデータ
        test_messages = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Hello!"}
        ]
        test_response = "Hi there!"
        
        # Log a test call
        log_llm_call(
            model="gpt-4.1",
            prompt_tokens=100,
            completion_tokens=50,
            latency_ms=1500.5,
            messages=test_messages,
            response=test_response
        )
        
        # Check if file was created
        log_files = list(Path(self.test_dir).glob("*.jsonl"))
        self.assertEqual(len(log_files), 1, "Should create one log file")
        
        # Check file content
        with open(log_files[0], 'r', encoding='utf-8') as f:
            content = f.read().strip()
            self.assertTrue(content, "Log file should not be empty")
            
            # Parse JSON
            log_entry = json.loads(content)
            self.assertEqual(log_entry["model"], "gpt-4.1")
            self.assertEqual(log_entry["prompt_tokens"], 100)
            self.assertEqual(log_entry["completion_tokens"], 50)
            self.assertEqual(log_entry["latency_ms"], 1500.5)
            self.assertEqual(log_entry["messages"], test_messages)
            self.assertEqual(log_entry["response"], test_response)
            self.assertIn("ts", log_entry)
            self.assertIn("task_id", log_entry)
    
    def test_estimate_cost(self):
        """Test cost estimation"""
        # Test GPT-4 pricing
        cost = estimate_cost("gpt-4", 1000, 500)
        expected = (1000/1000 * 0.03) + (500/1000 * 0.06)  # $0.03 + $0.03 = $0.06
        self.assertAlmostEqual(cost, expected, places=6)
        
        # Test GPT-4 Turbo pricing
        cost = estimate_cost("gpt-4-turbo", 1000, 500)
        expected = (1000/1000 * 0.01) + (500/1000 * 0.03)  # $0.01 + $0.015 = $0.025
        self.assertAlmostEqual(cost, expected, places=6)
        
        # Test GPT-3.5 pricing
        cost = estimate_cost("gpt-3.5-turbo", 1000, 500)
        expected = (1000/1000 * 0.001) + (500/1000 * 0.002)  # $0.001 + $0.001 = $0.002
        self.assertAlmostEqual(cost, expected, places=6)
    
    def test_count_today_calls(self):
        """Test call counting"""
        # Initially should be 0
        count = count_today_calls()
        self.assertEqual(count, 0)
        
        # Log some calls
        for i in range(3):
            log_llm_call(
                model="gpt-4",
                prompt_tokens=100,
                completion_tokens=50,
                latency_ms=1000.0
            )
        
        # Count should be 3
        count = count_today_calls()
        self.assertEqual(count, 3)
    
    def test_get_today_stats(self):
        """Test statistics gathering"""
        # Log some test calls
        log_llm_call("gpt-4", 100, 50, 1000.0)
        log_llm_call("gpt-4", 200, 100, 2000.0)
        
        stats = get_today_stats()
        
        self.assertEqual(stats["calls"], 2)
        self.assertEqual(stats["total_tokens"], 450)  # (100+50) + (200+100)
        self.assertEqual(stats["avg_latency"], 1500.0)  # (1000+2000)/2
        self.assertGreater(stats["total_cost"], 0)
    
    def test_render_llm_stats_for_memory_chat(self):
        """Test Memory Chat stats rendering"""
        # Log a test call
        log_llm_call("gpt-4", 100, 50, 1000.0)
        
        stats = render_llm_stats_for_memory_chat()
        
        self.assertIn("calls_today", stats)
        self.assertIn("total_tokens", stats)
        self.assertIn("estimated_cost", stats)
        self.assertIn("avg_latency", stats)
        
        self.assertEqual(stats["calls_today"], 1)
        self.assertEqual(stats["total_tokens"], 150)
        self.assertTrue(stats["estimated_cost"].startswith("$"))
        self.assertTrue(stats["avg_latency"].endswith("ms"))
    
    def test_empty_stats(self):
        """Test stats when no calls have been made"""
        stats = get_today_stats()
        
        self.assertEqual(stats["calls"], 0)
        self.assertEqual(stats["total_tokens"], 0)
        self.assertEqual(stats["total_cost"], 0.0)
        self.assertEqual(stats["avg_latency"], 0.0)
    
    def test_multiple_calls_same_day(self):
        """Test multiple calls on the same day"""
        # Log multiple calls
        models = ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"]
        for i, model in enumerate(models):
            log_llm_call(
                model=model,
                prompt_tokens=100 * (i + 1),
                completion_tokens=50 * (i + 1),
                latency_ms=1000.0 * (i + 1)
            )
        
        count = count_today_calls()
        self.assertEqual(count, 3)
        
        stats = get_today_stats()
        self.assertEqual(stats["calls"], 3)
        # Total tokens: (100+50) + (200+100) + (300+150) = 900
        self.assertEqual(stats["total_tokens"], 900)
    
    def test_get_recent_llm_calls(self):
        """Test recent LLM calls retrieval (仕様書準拠)"""
        # Log some test calls
        test_data = [
            {
                "model": "gpt-4.1",
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "latency_ms": 1000.0,
                "messages": [{"role": "user", "content": f"Test {i}"}],
                "response": f"Response {i}"
            }
            for i in range(3)
        ]
        
        for data in test_data:
            log_llm_call(**data)
        
        # Get recent calls
        recent_calls = get_recent_llm_calls(limit=2)
        
        # Check results
        self.assertEqual(len(recent_calls), 2)
        self.assertIn("timestamp", recent_calls[0])
        self.assertIn("messages", recent_calls[0])
        self.assertIn("response", recent_calls[0])
        self.assertEqual(recent_calls[0]["model"], "gpt-4.1")
    
    def test_format_messages_for_display(self):
        """Test message formatting for display"""
        test_messages = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Hello!"},
            {"role": "assistant", "content": "Hi there!"}
        ]
        
        formatted = format_messages_for_display(test_messages)
        
        self.assertIn("**System**: You are helpful.", formatted)
        self.assertIn("**User**: Hello!", formatted)
        self.assertIn("**Assistant**: Hi there!", formatted)
    
    def test_format_long_messages(self):
        """Test truncation of long messages"""
        long_content = "x" * 300  # Longer than 200 char limit
        test_messages = [{"role": "user", "content": long_content}]
        
        formatted = format_messages_for_display(test_messages)
        
        self.assertIn("...", formatted)  # Should be truncated
        self.assertLess(len(formatted), len(long_content))


class TestLLMLoggerErrorHandling(unittest.TestCase):
    """Test error handling in LLM logger"""
    
    def test_invalid_directory(self):
        """Test behavior with invalid log directory"""
        with patch('core.llm_logger.LLM_LOGS_DIR', Path("/invalid/path")):
            # Should not crash even with invalid directory
            try:
                count = count_today_calls()
                self.assertEqual(count, 0)
            except Exception as e:
                self.fail(f"Should handle invalid directory gracefully: {e}")
    
    def test_file_permission_error(self):
        """Test behavior with file permission errors"""
        with patch('builtins.open', side_effect=PermissionError("Access denied")):
            # Should not crash on permission errors
            try:
                log_llm_call("gpt-4", 100, 50, 1000.0)
                # Should complete without raising exception
            except Exception as e:
                self.fail(f"Should handle permission errors gracefully: {e}")


if __name__ == '__main__':
    unittest.main()