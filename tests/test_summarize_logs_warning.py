"""
Tests for scripts.summarize_logs warning functionality
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch, Mock
from datetime import datetime

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.log_schema import LogEntry, RequestKind
from scripts.summarize_logs import summarize_by_kind, generate_html_report


class TestSummarizeLogsWarning:
    """Test summarize_logs warning functionality"""
    
    def create_mock_log_entry(self, prompt_tokens=100, completion_tokens=50, error=None):
        """Create a mock log entry for testing"""
        return LogEntry(
            ts=datetime.now().isoformat(),
            agent="kai",
            model="gpt-4.1",
            kind=RequestKind.UI_CHAT,
            task_id="test-task-123",
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            error=error,
            request={"messages": [{"role": "user", "content": "Test message"}]},
            response={"choices": [{"message": {"content": "Test response"}}]} if not error else None
        )
    
    def test_warning_flag_under_threshold(self):
        """Test that warnings are not added for entries under 1000 prompt tokens"""
        entry = self.create_mock_log_entry(prompt_tokens=500)
        entries = [entry]
        
        summary = summarize_by_kind(entries)
        
        # Check that no warning is added
        ui_chat_summary = summary[RequestKind.UI_CHAT]
        assert len(ui_chat_summary['samples']) == 1
        
        sample = ui_chat_summary['samples'][0]
        assert sample['warning'] == ""  # No warning for under threshold
        assert sample['tokens'] == "500/50"
    
    def test_warning_flag_over_threshold(self):
        """Test that warnings are added for entries over 1000 prompt tokens"""
        entry = self.create_mock_log_entry(prompt_tokens=1500)
        entries = [entry]
        
        summary = summarize_by_kind(entries)
        
        # Check that warning is added
        ui_chat_summary = summary[RequestKind.UI_CHAT]
        assert len(ui_chat_summary['samples']) == 1
        
        sample = ui_chat_summary['samples'][0]
        assert sample['warning'] == "⚠️ "  # Warning for over threshold
        assert sample['tokens'] == "1500/50"
    
    def test_warning_flag_exactly_threshold(self):
        """Test behavior at exactly 1000 prompt tokens"""
        entry = self.create_mock_log_entry(prompt_tokens=1000)
        entries = [entry]
        
        summary = summarize_by_kind(entries)
        
        # At exactly 1000, should not trigger warning (> 1000 triggers warning)
        ui_chat_summary = summary[RequestKind.UI_CHAT]
        sample = ui_chat_summary['samples'][0]
        assert sample['warning'] == ""  # No warning at exact threshold
    
    def test_warning_flag_just_over_threshold(self):
        """Test behavior just over 1000 prompt tokens"""
        entry = self.create_mock_log_entry(prompt_tokens=1001)
        entries = [entry]
        
        summary = summarize_by_kind(entries)
        
        # Just over 1000 should trigger warning
        ui_chat_summary = summary[RequestKind.UI_CHAT]
        sample = ui_chat_summary['samples'][0]
        assert sample['warning'] == "⚠️ "  # Warning for just over threshold
    
    def test_mixed_entries_warnings(self):
        """Test mixed entries with some over and some under threshold"""
        entries = [
            self.create_mock_log_entry(prompt_tokens=500),   # No warning
            self.create_mock_log_entry(prompt_tokens=1200),  # Warning
            self.create_mock_log_entry(prompt_tokens=800),   # No warning
        ]
        
        summary = summarize_by_kind(entries)
        
        ui_chat_summary = summary[RequestKind.UI_CHAT]
        samples = ui_chat_summary['samples']
        
        assert len(samples) == 3
        assert samples[0]['warning'] == ""      # 500 tokens
        assert samples[1]['warning'] == "⚠️ "   # 1200 tokens
        assert samples[2]['warning'] == ""      # 800 tokens
    
    def test_html_generation_includes_warnings(self):
        """Test that HTML generation properly includes warning prefixes"""
        entry_with_warning = self.create_mock_log_entry(prompt_tokens=1500)
        entry_without_warning = self.create_mock_log_entry(prompt_tokens=500)
        entries = [entry_with_warning, entry_without_warning]
        
        summary = summarize_by_kind(entries)
        html_report = generate_html_report(summary, since_hours=24, total_entries=2)
        
        # Check that warning emoji appears in HTML
        assert "⚠️" in html_report
        
        # Check that both token counts appear
        assert "1500/50" in html_report
        assert "500/50" in html_report
        
        # Basic HTML structure validation
        assert "<!DOCTYPE html>" in html_report
        assert "<title>Kai VPM LLM Call Summary</title>" in html_report
        assert "</html>" in html_report
    
    def test_warning_css_class_exists(self):
        """Test that warning CSS class is defined in HTML"""
        entry = self.create_mock_log_entry(prompt_tokens=1500)
        entries = [entry]
        
        summary = summarize_by_kind(entries)
        html_report = generate_html_report(summary, since_hours=24, total_entries=1)
        
        # Check that warning CSS class is defined
        assert ".warning" in html_report
        assert "color: #ff6b35" in html_report  # Warning color
    
    def test_multiple_request_kinds_warnings(self):
        """Test warnings across different request kinds"""
        entries = [
            LogEntry(
                ts=datetime.now().isoformat(),
                agent="kai",
                model="gpt-4.1",
                kind=RequestKind.UI_CHAT,
                task_id="ui-task",
                prompt_tokens=1200,
                completion_tokens=50,
                error=None,
                request={"messages": [{"role": "user", "content": "UI test"}]},
                response={"choices": [{"message": {"content": "UI response"}}]}
            ),
            LogEntry(
                ts=datetime.now().isoformat(),
                agent="kai",
                model="gpt-4.1",
                kind=RequestKind.SPEC_SCAN,
                task_id="spec-task",
                prompt_tokens=800,
                completion_tokens=100,
                error=None,
                request={"messages": [{"role": "user", "content": "Spec test"}]},
                response={"choices": [{"message": {"content": "Spec response"}}]}
            )
        ]
        
        summary = summarize_by_kind(entries)
        
        # UI_CHAT should have warning
        ui_samples = summary[RequestKind.UI_CHAT]['samples']
        assert ui_samples[0]['warning'] == "⚠️ "
        
        # SPEC_SCAN should not have warning
        spec_samples = summary[RequestKind.SPEC_SCAN]['samples']
        assert spec_samples[0]['warning'] == ""
    
    def test_error_entries_no_warning_interference(self):
        """Test that error entries don't interfere with warning logic"""
        entries = [
            self.create_mock_log_entry(prompt_tokens=1500, error="rate_limit"),
            self.create_mock_log_entry(prompt_tokens=1200, error=None)
        ]
        
        summary = summarize_by_kind(entries)
        
        ui_chat_summary = summary[RequestKind.UI_CHAT]
        
        # Should have 2 samples despite one being an error
        assert len(ui_chat_summary['samples']) == 2
        
        # Non-error entry should have warning
        non_error_sample = next(s for s in ui_chat_summary['samples'] if 'rate_limit' not in str(s))
        assert non_error_sample['warning'] == "⚠️ "
    
    def test_zero_token_entries(self):
        """Test handling of entries with zero tokens"""
        entry = self.create_mock_log_entry(prompt_tokens=0, completion_tokens=0)
        entries = [entry]
        
        summary = summarize_by_kind(entries)
        
        ui_chat_summary = summary[RequestKind.UI_CHAT]
        sample = ui_chat_summary['samples'][0]
        
        # Zero tokens should not trigger warning
        assert sample['warning'] == ""
        assert sample['tokens'] == "0/0"
    
    def test_warning_threshold_documentation(self):
        """Test that warning threshold is properly documented in constants"""
        # The warning threshold should be 1000 tokens
        # This is implicitly tested in the above tests, but we verify the logic
        
        # Test the exact boundary conditions
        test_cases = [
            (999, False),   # Just under - no warning
            (1000, False),  # Exactly at - no warning
            (1001, True),   # Just over - warning
            (1500, True),   # Well over - warning
        ]
        
        for tokens, should_warn in test_cases:
            entry = self.create_mock_log_entry(prompt_tokens=tokens)
            entries = [entry]
            summary = summarize_by_kind(entries)
            
            ui_chat_summary = summary[RequestKind.UI_CHAT]
            sample = ui_chat_summary['samples'][0]
            
            if should_warn:
                assert sample['warning'] == "⚠️ ", f"Expected warning for {tokens} tokens"
            else:
                assert sample['warning'] == "", f"Expected no warning for {tokens} tokens"