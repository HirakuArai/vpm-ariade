"""
Tests for scripts.summarize_logs module
"""

import pytest
import tempfile
import json
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.summarize_logs import (
    load_recent_logs, summarize_by_kind, generate_html_report
)
from core.log_schema import LogEntry, RequestKind, log_to_jsonl


class TestLoadRecentLogs:
    """Test load_recent_logs function"""
    
    def test_load_logs_within_time_range(self):
        """Test loading logs within specified time range"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir)
            
            # Create log entries with different timestamps
            now = datetime.now()
            
            # Recent entry (should be included)
            recent_entry = LogEntry(
                ts=(now - timedelta(hours=1)).isoformat(),
                agent="kai",
                model="gpt-4.1",
                kind=RequestKind.UI_CHAT,
                task_id="recent-1",
                prompt_tokens=100,
                completion_tokens=50,
                error=None,
                request={"test": "recent"},
                response={"result": "recent"}
            )
            
            # Old entry (should be excluded)
            old_entry = LogEntry(
                ts=(now - timedelta(hours=48)).isoformat(),
                agent="claude",
                model="gpt-4.1",
                kind=RequestKind.SPEC_SCAN,
                task_id="old-1",
                prompt_tokens=200,
                completion_tokens=100,
                error=None,
                request={"test": "old"},
                response={"result": "old"}
            )
            
            # Write to log file with today's date
            log_file = log_dir / now.strftime("%Y%m%d-%H%M%S.jsonl")
            log_to_jsonl(recent_entry, log_file)
            log_to_jsonl(old_entry, log_file)
            
            # Load logs from last 24 hours
            entries = load_recent_logs(log_dir, 24)
            
            # Should only include recent entry
            assert len(entries) == 1
            assert entries[0].task_id == "recent-1"
    
    def test_load_logs_from_multiple_files(self):
        """Test loading logs from multiple log files"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir)
            
            now = datetime.now()
            
            # Create entries in different files
            for i in range(3):
                entry = LogEntry(
                    ts=(now - timedelta(hours=i)).isoformat(),
                    agent="kai",
                    model="gpt-4.1",
                    kind=RequestKind.UI_CHAT,
                    task_id=f"entry-{i}",
                    prompt_tokens=100 + i,
                    completion_tokens=50 + i,
                    error=None,
                    request={"test": i},
                    response={"result": i}
                )
                
                # Different files for each hour
                file_time = now - timedelta(hours=i)
                log_file = log_dir / file_time.strftime("%Y%m%d-%H%M%S.jsonl")
                log_to_jsonl(entry, log_file)
            
            # Load all entries
            entries = load_recent_logs(log_dir, 24)
            
            assert len(entries) == 3
            # Should be sorted by timestamp
            assert entries[0].task_id == "entry-2"
            assert entries[1].task_id == "entry-1"
            assert entries[2].task_id == "entry-0"
    
    def test_empty_log_directory(self):
        """Test loading from non-existent log directory"""
        entries = load_recent_logs(Path("/nonexistent/dir"), 24)
        assert entries == []


class TestSummarizeByKind:
    """Test summarize_by_kind function"""
    
    def test_basic_summarization(self):
        """Test basic summarization by request kind"""
        entries = [
            LogEntry(
                ts="2024-01-15T10:00:00Z",
                agent="kai",
                model="gpt-4.1",
                kind=RequestKind.UI_CHAT,
                task_id="1",
                prompt_tokens=100,
                completion_tokens=50,
                error=None,
                request={"messages": [{"role": "user", "content": "Hello"}]},
                response={"result": "Hi"}
            ),
            LogEntry(
                ts="2024-01-15T10:01:00Z",
                agent="kai",
                model="gpt-4.1",
                kind=RequestKind.UI_CHAT,
                task_id="2",
                prompt_tokens=150,
                completion_tokens=75,
                error=None,
                request={"messages": [{"role": "user", "content": "How are you?"}]},
                response={"result": "Good"}
            ),
            LogEntry(
                ts="2024-01-15T10:02:00Z",
                agent="claude",
                model="gpt-4.1",
                kind=RequestKind.SPEC_SCAN,
                task_id="3",
                prompt_tokens=200,
                completion_tokens=100,
                error="rate_limit",
                request={"messages": [{"role": "user", "content": "Scan this"}]},
                response=None
            )
        ]
        
        summary = summarize_by_kind(entries)
        
        # Check UI_CHAT summary
        assert RequestKind.UI_CHAT in summary
        ui_chat = summary[RequestKind.UI_CHAT]
        assert ui_chat['total'] == 2
        assert ui_chat['success'] == 2
        assert ui_chat['errors'] == 0
        assert ui_chat['prompt_tokens'] == 250
        assert ui_chat['completion_tokens'] == 125
        assert len(ui_chat['samples']) == 2
        
        # Check SPEC_SCAN summary
        assert RequestKind.SPEC_SCAN in summary
        spec_scan = summary[RequestKind.SPEC_SCAN]
        assert spec_scan['total'] == 1
        assert spec_scan['success'] == 0
        assert spec_scan['errors'] == 1
        assert spec_scan['error_types']['rate_limit'] == 1
        assert len(spec_scan['samples']) == 1
    
    def test_sample_extraction(self):
        """Test extraction of sample prompts"""
        long_content = "This is a very long prompt " * 20  # > 200 chars
        
        entries = [
            LogEntry(
                ts="2024-01-15T10:00:00Z",
                agent="kai",
                model="gpt-4.1",
                kind=RequestKind.TICKET_GEN,
                task_id="1",
                prompt_tokens=100,
                completion_tokens=50,
                error=None,
                request={"messages": [
                    {"role": "system", "content": "System prompt"},
                    {"role": "user", "content": long_content}
                ]},
                response={"result": "ok"}
            )
        ]
        
        summary = summarize_by_kind(entries)
        samples = summary[RequestKind.TICKET_GEN]['samples']
        
        assert len(samples) == 1
        assert samples[0]['text'].endswith("...")
        assert len(samples[0]['text']) == 203  # 200 + "..."
    
    def test_max_samples_per_kind(self):
        """Test that only 3 samples are kept per kind"""
        entries = []
        for i in range(5):
            entries.append(LogEntry(
                ts=f"2024-01-15T10:{i:02d}:00Z",
                agent="kai",
                model="gpt-4.1",
                kind=RequestKind.REVIEW_GEN,
                task_id=str(i),
                prompt_tokens=100,
                completion_tokens=50,
                error=None,
                request={"messages": [{"role": "user", "content": f"Message {i}"}]},
                response={"result": f"Response {i}"}
            ))
        
        summary = summarize_by_kind(entries)
        samples = summary[RequestKind.REVIEW_GEN]['samples']
        
        # Should only keep first 3 samples
        assert len(samples) == 3
        assert samples[0]['text'] == "Message 0"
        assert samples[1]['text'] == "Message 1"
        assert samples[2]['text'] == "Message 2"


class TestGenerateHtmlReport:
    """Test generate_html_report function"""
    
    def test_html_generation(self):
        """Test basic HTML report generation"""
        summary = {
            RequestKind.UI_CHAT: {
                'total': 10,
                'success': 9,
                'errors': 1,
                'prompt_tokens': 1000,
                'completion_tokens': 500,
                'error_types': {'timeout': 1},
                'samples': [
                    {
                        'ts': '2024-01-15T10:00:00Z',
                        'task_id': 'task-1',
                        'agent': 'kai',
                        'text': 'Sample prompt text',
                        'tokens': '100/50'
                    }
                ]
            }
        }
        
        html = generate_html_report(summary, 24, 10)
        
        # Check basic structure
        assert '<!DOCTYPE html>' in html
        assert '<title>Kai VPM LLM Call Summary</title>' in html
        assert 'Last 24 hours' in html
        assert 'Total Calls:' in html
        assert '10' in html  # total entries
        
        # Check kind summary
        assert 'UI CHAT' in html
        assert 'Success Rate:' in html
        assert '90.0%' in html
        assert 'Sample prompt text' in html
        
        # Check error display
        assert 'timeout: 1' in html
    
    def test_empty_summary(self):
        """Test HTML generation with empty summary"""
        html = generate_html_report({}, 24, 0)
        
        assert '<!DOCTYPE html>' in html
        assert 'Total Calls:' in html
        assert '0' in html  # zero entries
    
    def test_multiple_kinds(self):
        """Test HTML generation with multiple request kinds"""
        summary = {}
        for kind in RequestKind:
            summary[kind] = {
                'total': 5,
                'success': 5,
                'errors': 0,
                'prompt_tokens': 500,
                'completion_tokens': 250,
                'error_types': {},
                'samples': []
            }
        
        html = generate_html_report(summary, 24, 20)
        
        # Check all kinds are present
        for kind in RequestKind:
            assert kind.value.upper().replace('_', ' ') in html