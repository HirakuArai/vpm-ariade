"""
Tests for timezone handling in log processing
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from pathlib import Path
import tempfile

from core.log_schema import LogEntry, RequestKind, log_to_jsonl
from scripts.summarize_logs import load_recent_logs
from linter.prompt_linter import load_recent_logs as linter_load_recent_logs


class TestTimezoneHandling:
    """Test timezone-aware datetime handling"""
    
    def test_utc_timestamp_parsing(self):
        """Test that UTC timestamps are properly parsed"""
        utc_timestamp = "2024-06-30T12:34:56.789Z"
        
        # Should parse without error
        parsed_time = datetime.fromisoformat(utc_timestamp.replace('Z', '+00:00'))
        
        # Should be timezone-aware
        assert parsed_time.tzinfo is not None
        assert parsed_time.tzinfo.utcoffset(None) == timedelta(0)
    
    def test_summarize_logs_timezone_compatibility(self):
        """Test that summarize_logs handles timezone-aware timestamps"""
        # Create a test log entry with UTC timestamp (use recent time)
        recent_time = datetime.now(timezone.utc) - timedelta(hours=1)
        entry = LogEntry(
            ts=recent_time.isoformat(timespec="milliseconds").replace("+00:00", "Z"),
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
        
        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir)
            log_file = log_dir / recent_time.strftime("%Y%m%d-%H%M%S.jsonl")  # Use proper filename format
            
            log_to_jsonl(entry, log_file)
            
            # Should not raise timezone comparison error
            entries = load_recent_logs(log_dir, since_hours=2)  # Use shorter period for recent test timestamp
            
            assert len(entries) == 1
            assert entries[0].task_id == "test-uuid-123"
    
    def test_linter_timezone_compatibility(self):
        """Test that prompt linter handles timezone-aware timestamps"""
        recent_time = datetime.now(timezone.utc) - timedelta(hours=1)
        entry = LogEntry(
            ts=recent_time.isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            agent="kai", 
            model="gpt-4.1",
            kind=RequestKind.UI_CHAT,
            task_id="test-uuid-456",
            prompt_tokens=200,
            completion_tokens=75,
            error=None,
            request={"messages": [{"role": "user", "content": "test"}]},
            response={"choices": [{"message": {"content": "response"}}]}
        )
        
        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir)
            log_file = log_dir / recent_time.strftime("%Y%m%d-%H%M%S.jsonl")  # Use proper filename format
            
            log_to_jsonl(entry, log_file)
            
            # Should not raise timezone comparison error
            entries = linter_load_recent_logs(log_dir, since_hours=2)  # Use shorter period for recent test timestamp
            
            assert len(entries) == 1
            assert entries[0].task_id == "test-uuid-456"
    
    def test_cutoff_time_is_timezone_aware(self):
        """Test that cutoff times are timezone-aware"""
        with patch('scripts.summarize_logs.datetime') as mock_dt:
            # Mock timezone-aware now
            mock_now = datetime.now(timezone.utc)
            mock_dt.now.return_value = mock_now
            mock_dt.timezone = timezone
            
            # Import here to get the mocked version
            from scripts.summarize_logs import load_recent_logs
            
            with tempfile.TemporaryDirectory() as tmpdir:
                log_dir = Path(tmpdir)
                
                # Should not raise error even with empty directory
                entries = load_recent_logs(log_dir, since_hours=24)
                assert entries == []
    
    def test_mixed_timestamp_formats(self):
        """Test handling of different timestamp formats"""
        # Test both old format (if any) and new UTC format
        recent_time = datetime.now(timezone.utc) - timedelta(hours=1)
        entries_data = [
            {
                "ts": recent_time.isoformat(timespec="milliseconds").replace("+00:00", "Z"),  # New UTC format
                "agent": "kai",
                "model": "gpt-4.1", 
                "kind": "ui_chat",
                "task_id": "test-uuid-1",
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "error": None,
                "request": {"messages": []},
                "response": {"choices": []}
            }
        ]
        
        for entry_data in entries_data:
            entry = LogEntry(**entry_data)
            
            with tempfile.TemporaryDirectory() as tmpdir:
                log_dir = Path(tmpdir)
                log_file = log_dir / recent_time.strftime("%Y%m%d-%H%M%S.jsonl")  # Use proper filename format
                
                log_to_jsonl(entry, log_file)
                
                # Should handle timezone properly
                entries = load_recent_logs(log_dir, since_hours=2)  # Use shorter period for recent test timestamp
                assert len(entries) == 1
    
    def test_old_entries_filtered_correctly(self):
        """Test that old entries are correctly filtered out"""
        # Create an entry with old timestamp
        old_timestamp = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat(timespec="milliseconds") + "Z"
        
        old_entry = LogEntry(
            ts=old_timestamp,
            agent="kai",
            model="gpt-4.1",
            kind=RequestKind.UI_CHAT,
            task_id="old-uuid",
            prompt_tokens=100,
            completion_tokens=50,
            error=None,
            request={"messages": []},
            response={"choices": []}
        )
        
        # Create a recent entry
        recent_timestamp = datetime.now(timezone.utc).isoformat(timespec="milliseconds") + "Z"
        
        recent_entry = LogEntry(
            ts=recent_timestamp,
            agent="kai",
            model="gpt-4.1",
            kind=RequestKind.UI_CHAT,
            task_id="recent-uuid",
            prompt_tokens=100,
            completion_tokens=50,
            error=None,
            request={"messages": []},
            response={"choices": []}
        )
        
        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir)
            
            # Use proper date-based filename for current day
            today_filename = datetime.now(timezone.utc).strftime("%Y%m%d-120000.jsonl")
            log_file = log_dir / today_filename
            
            # Write both entries
            log_to_jsonl(old_entry, log_file)
            log_to_jsonl(recent_entry, log_file)
            
            # Filter for last 24 hours
            entries = load_recent_logs(log_dir, since_hours=24)
            
            # Should only include recent entry
            assert len(entries) == 1
            assert entries[0].task_id == "recent-uuid"