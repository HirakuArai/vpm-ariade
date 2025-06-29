"""
Tests for core.log_schema module
"""

import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime
from unittest.mock import patch

from core.log_schema import (
    RequestKind, LogEntry, log_to_jsonl, from_jsonl, get_log_filepath
)


class TestRequestKind:
    """Test RequestKind enum"""
    
    def test_enum_values(self):
        """Test that all expected enum values exist"""
        assert RequestKind.SPEC_SCAN.value == "spec_scan"
        assert RequestKind.TICKET_GEN.value == "ticket_gen"
        assert RequestKind.REVIEW_GEN.value == "review_gen"
        assert RequestKind.UI_CHAT.value == "ui_chat"
    
    def test_enum_membership(self):
        """Test enum membership checks"""
        assert "spec_scan" in [k.value for k in RequestKind]
        assert "invalid_kind" not in [k.value for k in RequestKind]


class TestLogEntry:
    """Test LogEntry model"""
    
    def test_valid_entry_creation(self):
        """Test creating a valid LogEntry"""
        entry = LogEntry(
            ts="2024-01-15T10:30:00Z",
            agent="kai",
            model="gpt-4.1",
            kind=RequestKind.UI_CHAT,
            task_id="test-uuid-123",
            prompt_tokens=100,
            completion_tokens=50,
            error=None,
            request={"messages": [{"role": "user", "content": "test"}]},
            response={"choices": [{"message": {"content": "response"}}]}
        )
        
        assert entry.agent == "kai"
        assert entry.model == "gpt-4.1"
        assert entry.kind == "ui_chat"
        assert entry.prompt_tokens == 100
        assert entry.completion_tokens == 50
        assert entry.error is None
    
    def test_entry_with_error(self):
        """Test creating LogEntry with error"""
        entry = LogEntry(
            ts="2024-01-15T10:30:00Z",
            agent="claude",
            model="gpt-4.1",
            kind=RequestKind.SPEC_SCAN,
            task_id="test-uuid-456",
            prompt_tokens=200,
            completion_tokens=0,
            error="rate_limit_exceeded",
            request={"messages": []},
            response=None
        )
        
        assert entry.error == "rate_limit_exceeded"
        assert entry.response is None
        assert entry.completion_tokens == 0
    
    def test_invalid_agent(self):
        """Test that invalid agent raises validation error"""
        with pytest.raises(ValueError):
            LogEntry(
                ts="2024-01-15T10:30:00Z",
                agent="invalid_agent",  # Should only be 'kai' or 'claude'
                model="gpt-4.1",
                kind=RequestKind.UI_CHAT,
                task_id="test-uuid-789",
                prompt_tokens=100,
                completion_tokens=50,
                error=None,
                request={},
                response={}
            )
    
    def test_json_serialization(self):
        """Test JSON serialization of LogEntry"""
        entry = LogEntry(
            ts="2024-01-15T10:30:00Z",
            agent="kai",
            model="gpt-4.1",
            kind=RequestKind.REVIEW_GEN,
            task_id="test-uuid-999",
            prompt_tokens=150,
            completion_tokens=75,
            error=None,
            request={"test": "request"},
            response={"test": "response"}
        )
        
        json_str = entry.model_dump_json()
        parsed = json.loads(json_str)
        
        assert parsed["agent"] == "kai"
        assert parsed["kind"] == "review_gen"
        assert parsed["prompt_tokens"] == 150


class TestLogFunctions:
    """Test logging utility functions"""
    
    def test_log_to_jsonl(self):
        """Test appending LogEntry to JSONL file"""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "test.jsonl"
            
            entry1 = LogEntry(
                ts="2024-01-15T10:30:00Z",
                agent="kai",
                model="gpt-4.1",
                kind=RequestKind.UI_CHAT,
                task_id="uuid-1",
                prompt_tokens=100,
                completion_tokens=50,
                error=None,
                request={"msg": "test1"},
                response={"resp": "test1"}
            )
            
            entry2 = LogEntry(
                ts="2024-01-15T10:31:00Z",
                agent="claude",
                model="gpt-4.1",
                kind=RequestKind.TICKET_GEN,
                task_id="uuid-2",
                prompt_tokens=200,
                completion_tokens=100,
                error=None,
                request={"msg": "test2"},
                response={"resp": "test2"}
            )
            
            log_to_jsonl(entry1, filepath)
            log_to_jsonl(entry2, filepath)
            
            # Verify file contents
            with open(filepath, 'r') as f:
                lines = f.readlines()
            
            assert len(lines) == 2
            
            # Parse and verify first entry
            data1 = json.loads(lines[0])
            assert data1["task_id"] == "uuid-1"
            assert data1["agent"] == "kai"
            
            # Parse and verify second entry
            data2 = json.loads(lines[1])
            assert data2["task_id"] == "uuid-2"
            assert data2["agent"] == "claude"
    
    def test_from_jsonl(self):
        """Test reading LogEntry objects from JSONL file"""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "test.jsonl"
            
            # Create test data
            entries_data = [
                {
                    "ts": "2024-01-15T10:30:00Z",
                    "agent": "kai",
                    "model": "gpt-4.1",
                    "kind": "ui_chat",
                    "task_id": "uuid-1",
                    "prompt_tokens": 100,
                    "completion_tokens": 50,
                    "error": None,
                    "request": {"test": 1},
                    "response": {"result": 1}
                },
                {
                    "ts": "2024-01-15T10:31:00Z",
                    "agent": "claude",
                    "model": "gpt-4.1",
                    "kind": "spec_scan",
                    "task_id": "uuid-2",
                    "prompt_tokens": 200,
                    "completion_tokens": 100,
                    "error": None,
                    "request": {"test": 2},
                    "response": {"result": 2}
                }
            ]
            
            # Write test data
            with open(filepath, 'w') as f:
                for data in entries_data:
                    f.write(json.dumps(data) + '\n')
            
            # Test reading
            entries = from_jsonl(filepath)
            
            assert len(entries) == 2
            assert entries[0].task_id == "uuid-1"
            assert entries[0].agent == "kai"
            assert entries[1].task_id == "uuid-2"
            assert entries[1].agent == "claude"
    
    def test_from_jsonl_with_invalid_lines(self):
        """Test from_jsonl handles invalid lines gracefully"""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "test.jsonl"
            
            # Write mix of valid and invalid data
            with open(filepath, 'w') as f:
                # Valid entry
                f.write(json.dumps({
                    "ts": "2024-01-15T10:30:00Z",
                    "agent": "kai",
                    "model": "gpt-4.1",
                    "kind": "ui_chat",
                    "task_id": "uuid-1",
                    "prompt_tokens": 100,
                    "completion_tokens": 50,
                    "error": None,
                    "request": {},
                    "response": {}
                }) + '\n')
                
                # Invalid JSON
                f.write('invalid json{' + '\n')
                
                # Empty line
                f.write('\n')
                
                # Valid entry
                f.write(json.dumps({
                    "ts": "2024-01-15T10:31:00Z",
                    "agent": "claude",
                    "model": "gpt-4.1",
                    "kind": "spec_scan",
                    "task_id": "uuid-2",
                    "prompt_tokens": 200,
                    "completion_tokens": 100,
                    "error": None,
                    "request": {},
                    "response": {}
                }) + '\n')
            
            # Should parse valid entries and skip invalid ones
            entries = from_jsonl(filepath)
            assert len(entries) == 2
            assert entries[0].task_id == "uuid-1"
            assert entries[1].task_id == "uuid-2"
    
    def test_from_jsonl_nonexistent_file(self):
        """Test from_jsonl returns empty list for nonexistent file"""
        entries = from_jsonl("nonexistent/file.jsonl")
        assert entries == []
    
    def test_log_to_jsonl_creates_directory(self):
        """Test that log_to_jsonl creates parent directories"""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "logs" / "llm_calls" / "test.jsonl"
            
            entry = LogEntry(
                ts="2024-01-15T10:30:00Z",
                agent="kai",
                model="gpt-4.1",
                kind=RequestKind.UI_CHAT,
                task_id="uuid-1",
                prompt_tokens=100,
                completion_tokens=50,
                error=None,
                request={},
                response={}
            )
            
            log_to_jsonl(entry, filepath)
            
            assert filepath.exists()
            assert filepath.parent.exists()
    
    def test_get_log_filepath(self):
        """Test get_log_filepath generates correct paths"""
        # Test with specific timestamp
        ts = datetime(2024, 1, 15, 10, 30, 45)
        filepath = get_log_filepath(ts)
        
        assert str(filepath) == "logs/llm_calls/20240115-103045.jsonl"
        
        # Test default (current time)
        with patch('core.log_schema.datetime') as mock_datetime:
            mock_now = datetime(2024, 12, 25, 15, 45, 30)
            mock_datetime.now.return_value = mock_now
            
            filepath = get_log_filepath()
            assert str(filepath) == "logs/llm_calls/20241225-154530.jsonl"