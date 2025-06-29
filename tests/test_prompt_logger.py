"""
Tests for core.prompt_logger module
"""

import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock

from core.prompt_logger import PromptLogger, log_call
from core.log_schema import RequestKind, LogEntry, from_jsonl


class TestPromptLogger:
    """Test PromptLogger class"""
    
    def test_ensure_log_directory(self):
        """Test that log directory is created"""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('core.prompt_logger.Path') as mock_path:
                mock_log_dir = MagicMock()
                mock_path.return_value = mock_log_dir
                
                logger = PromptLogger()
                
                mock_path.assert_called_with("logs/llm_calls")
                mock_log_dir.mkdir.assert_called_once_with(parents=True, exist_ok=True)
    
    def test_get_current_log_file(self):
        """Test log file path generation"""
        logger = PromptLogger()
        
        with patch('core.prompt_logger.datetime') as mock_datetime:
            mock_now = datetime(2024, 1, 15, 10, 30, 45)
            mock_datetime.now.return_value = mock_now
            
            # First call should create new file
            log_file = logger._get_current_log_file()
            assert "20240115" in str(log_file)
            
            # Same day should return same file
            log_file2 = logger._get_current_log_file()
            assert log_file == log_file2
            
            # New day should create new file
            mock_datetime.now.return_value = datetime(2024, 1, 16, 10, 30, 45)
            log_file3 = logger._get_current_log_file()
            assert "20240116" in str(log_file3)
            assert log_file3 != log_file


class TestLogCall:
    """Test log_call context manager"""
    
    def test_basic_logging(self):
        """Test basic request/response logging"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test.jsonl"
            
            with patch('core.prompt_logger.PromptLogger._get_current_log_file') as mock_get_file:
                mock_get_file.return_value = log_file
                
                # Use the context manager
                with log_call("kai", RequestKind.UI_CHAT) as log:
                    # Log request
                    request_data = {
                        "messages": [
                            {"role": "user", "content": "Hello"}
                        ]
                    }
                    log['log_request'](request_data)
                    
                    # Simulate LLM response
                    response_data = {
                        "choices": [
                            {"message": {"content": "Hi there!"}}
                        ]
                    }
                    log['log_response'](response_data, 10, 15)
                
                # Verify log was written
                entries = from_jsonl(log_file)
                assert len(entries) == 1
                
                entry = entries[0]
                assert entry.agent == "kai"
                assert entry.kind == "ui_chat"
                assert entry.prompt_tokens == 10
                assert entry.completion_tokens == 15
                assert entry.request == request_data
                assert entry.response == response_data
                assert entry.error is None
    
    def test_logging_with_error(self):
        """Test logging when an error occurs"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test.jsonl"
            
            with patch('core.prompt_logger.PromptLogger._get_current_log_file') as mock_get_file:
                mock_get_file.return_value = log_file
                
                # Use context manager with error
                with log_call("claude", RequestKind.SPEC_SCAN, model="gpt-4.1") as log:
                    request_data = {"messages": []}
                    log['log_request'](request_data)
                    
                    # Log error
                    log['log_error']("rate_limit_exceeded")
                    log['log_response'](None, 50, 0)
                
                # Verify error was logged
                entries = from_jsonl(log_file)
                assert len(entries) == 1
                
                entry = entries[0]
                assert entry.agent == "claude"
                assert entry.error == "rate_limit_exceeded"
                assert entry.response is None
                assert entry.completion_tokens == 0
    
    def test_logging_with_exception(self):
        """Test logging when an exception is raised"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test.jsonl"
            
            with patch('core.prompt_logger.PromptLogger._get_current_log_file') as mock_get_file:
                mock_get_file.return_value = log_file
                
                # Use context manager that raises exception
                with pytest.raises(ValueError):
                    with log_call("kai", RequestKind.TICKET_GEN) as log:
                        request_data = {"test": "data"}
                        log['log_request'](request_data)
                        
                        # Simulate exception during LLM call
                        raise ValueError("Test exception")
                
                # Verify exception was logged
                entries = from_jsonl(log_file)
                assert len(entries) == 1
                
                entry = entries[0]
                assert entry.error == "unhandled_exception: ValueError"
                assert entry.response is None
    
    def test_custom_task_id(self):
        """Test using custom task ID"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test.jsonl"
            
            with patch('core.prompt_logger.PromptLogger._get_current_log_file') as mock_get_file:
                mock_get_file.return_value = log_file
                
                custom_task_id = "custom-task-123"
                
                with log_call("kai", RequestKind.REVIEW_GEN, task_id=custom_task_id) as log:
                    assert log['task_id'] == custom_task_id
                    log['log_request']({"test": "request"})
                    log['log_response']({"test": "response"}, 5, 10)
                
                entries = from_jsonl(log_file)
                assert entries[0].task_id == custom_task_id
    
    def test_auto_generated_task_id(self):
        """Test auto-generated task ID"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test.jsonl"
            
            with patch('core.prompt_logger.PromptLogger._get_current_log_file') as mock_get_file:
                mock_get_file.return_value = log_file
                
                with log_call("kai", RequestKind.UI_CHAT) as log:
                    task_id = log['task_id']
                    assert task_id is not None
                    assert len(task_id) == 36  # UUID format
                    
                    log['log_request']({"test": "request"})
                    log['log_response']({"test": "response"}, 5, 10)
                
                entries = from_jsonl(log_file)
                assert entries[0].task_id == task_id
    
    def test_no_logging_without_request(self):
        """Test that nothing is logged if request is not captured"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test.jsonl"
            
            with patch('core.prompt_logger.PromptLogger._get_current_log_file') as mock_get_file:
                mock_get_file.return_value = log_file
                
                with log_call("kai", RequestKind.UI_CHAT) as log:
                    # Don't log any request
                    pass
                
                # Verify nothing was logged
                assert not log_file.exists()
    
    def test_multiple_calls_same_file(self):
        """Test multiple calls append to same file"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test.jsonl"
            
            with patch('core.prompt_logger.PromptLogger._get_current_log_file') as mock_get_file:
                mock_get_file.return_value = log_file
                
                # First call
                with log_call("kai", RequestKind.UI_CHAT) as log:
                    log['log_request']({"msg": "request1"})
                    log['log_response']({"msg": "response1"}, 10, 20)
                
                # Second call
                with log_call("claude", RequestKind.SPEC_SCAN) as log:
                    log['log_request']({"msg": "request2"})
                    log['log_response']({"msg": "response2"}, 30, 40)
                
                # Verify both entries
                entries = from_jsonl(log_file)
                assert len(entries) == 2
                assert entries[0].agent == "kai"
                assert entries[1].agent == "claude"
                assert entries[0].request["msg"] == "request1"
                assert entries[1].request["msg"] == "request2"