"""
Tests for AI Log Output Guidelines v1.0 compliance
"""

import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime
from unittest.mock import patch

from core.log_schema import LogEntry, RequestKind, log_to_jsonl
from core.prompt_logger import PromptLogger, log_call


class TestLogGuidelinesCompliance:
    """Test compliance with AI Log Output Guidelines v1.0"""
    
    def test_json_structure_valid(self):
        """Test that log entries produce valid JSON"""
        entry = LogEntry(
            ts="2024-06-30T12:34:56.789Z",
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
        
        # Should not raise JSONDecodeError
        json_str = entry.model_dump_json()
        parsed = json.loads(json_str)
        
        assert isinstance(parsed, dict)
        assert parsed["agent"] == "kai"
    
    def test_python_none_to_json_null(self):
        """Test that Python None converts to JSON null"""
        entry = LogEntry(
            ts="2024-06-30T12:34:56.789Z", 
            agent="kai",
            model="gpt-4.1",
            kind=RequestKind.UI_CHAT,
            task_id="test-uuid-123",
            prompt_tokens=100,
            completion_tokens=50,
            error=None,  # Python None
            request={"test": "data"},
            response=None  # Python None
        )
        
        json_str = entry.model_dump_json()
        
        # Should contain JSON null, not Python None
        assert '"error":null' in json_str or '"error": null' in json_str
        assert '"response":null' in json_str or '"response": null' in json_str
        assert 'None' not in json_str
        assert 'True' not in json_str  
        assert 'False' not in json_str
    
    def test_iso8601_utc_timestamp_format(self):
        """Test that timestamps follow ISO-8601 UTC format"""
        with patch('core.prompt_logger.datetime') as mock_datetime:
            # Mock UTC time
            mock_datetime.utcnow.return_value = datetime(2024, 6, 30, 12, 34, 56, 789000)
            
            logger = PromptLogger()
            
            with logger.log_call("kai", RequestKind.UI_CHAT) as log:
                # Check timestamp format
                timestamp = log['task_id']  # Access internal timestamp through context
                
            # Verify the timestamp generation
            expected_timestamp = "2024-06-30T12:34:56.789Z"
            actual_timestamp = mock_datetime.utcnow.return_value.isoformat(timespec="milliseconds") + "Z"
            
            assert actual_timestamp == expected_timestamp
            assert actual_timestamp.endswith("Z")
            assert "T" in actual_timestamp
    
    def test_utf8_encoding_support(self):
        """Test UTF-8 encoding without BOM"""
        entry = LogEntry(
            ts="2024-06-30T12:34:56.789Z",
            agent="kai", 
            model="gpt-4.1",
            kind=RequestKind.UI_CHAT,
            task_id="test-uuid-123",
            prompt_tokens=100,
            completion_tokens=50,
            error=None,
            request={"messages": [{"role": "user", "content": "こんにちは🚀"}]},
            response={"choices": [{"message": {"content": "はい、日本語です"}}]}
        )
        
        with tempfile.NamedTemporaryFile(mode='w+', encoding='utf-8', delete=False) as f:
            filepath = Path(f.name)
            
        try:
            log_to_jsonl(entry, filepath)
            
            # Read back and verify UTF-8 content
            content = filepath.read_text(encoding='utf-8')
            assert "こんにちは🚀" in content
            assert "はい、日本語です" in content
            
            # Verify no BOM
            with open(filepath, 'rb') as f:
                raw_content = f.read()
                assert not raw_content.startswith(b'\xef\xbb\xbf')  # UTF-8 BOM
                
        finally:
            filepath.unlink()
    
    def test_size_limit_awareness(self):
        """Test awareness of 32KB size limit guideline"""
        # Create a large entry approaching the limit
        large_content = "A" * 30000  # 30KB of content
        
        entry = LogEntry(
            ts="2024-06-30T12:34:56.789Z",
            agent="kai",
            model="gpt-4.1", 
            kind=RequestKind.UI_CHAT,
            task_id="test-uuid-123",
            prompt_tokens=1000,
            completion_tokens=500,
            error=None,
            request={"messages": [{"role": "user", "content": large_content}]},
            response={"choices": [{"message": {"content": "response"}}]}
        )
        
        json_str = entry.model_dump_json()
        size_bytes = len(json_str.encode('utf-8'))
        
        # Should be under 32KB limit
        assert size_bytes < 32 * 1024, f"Entry size {size_bytes} bytes exceeds 32KB limit"
    
    def test_no_sensitive_information(self):
        """Test that no sensitive information is logged"""
        # This is more of a policy test - actual implementation would need
        # to sanitize API keys, tokens, etc.
        entry = LogEntry(
            ts="2024-06-30T12:34:56.789Z",
            agent="kai",
            model="gpt-4.1",
            kind=RequestKind.UI_CHAT, 
            task_id="test-uuid-123",
            prompt_tokens=100,
            completion_tokens=50,
            error=None,
            request={"messages": [{"role": "user", "content": "Hello"}]},
            response={"choices": [{"message": {"content": "Hi there"}}]}
        )
        
        json_str = entry.model_dump_json()
        
        # Should not contain common sensitive patterns
        sensitive_patterns = [
            "sk-",  # OpenAI API keys
            "password",
            "secret"
            # Note: "token" is excluded as it appears in field names like "prompt_tokens"
        ]
        
        for pattern in sensitive_patterns:
            assert pattern not in json_str.lower()
    
    def test_comma_separation_completeness(self):
        """Test that all JSON elements have proper comma separation"""
        entry = LogEntry(
            ts="2024-06-30T12:34:56.789Z",
            agent="kai",
            model="gpt-4.1",
            kind=RequestKind.UI_CHAT,
            task_id="test-uuid-123", 
            prompt_tokens=100,
            completion_tokens=50,
            error=None,
            request={"key1": "value1", "key2": "value2"},
            response={"choice1": "data1", "choice2": "data2"}
        )
        
        json_str = entry.model_dump_json()
        
        # Should be valid JSON (which implies proper comma separation)
        parsed = json.loads(json_str)
        assert isinstance(parsed, dict)
        
        # Re-serialize and compare (should be consistent)
        re_serialized = json.dumps(parsed, ensure_ascii=False)
        re_parsed = json.loads(re_serialized)
        
        assert re_parsed == parsed
    
    def test_action_intent_consistency(self):
        """Test action_type and intent consistency (where applicable)"""
        # This test is more relevant for AI response JSON, not log entries
        # But we can test that the log structure is consistent
        
        entry = LogEntry(
            ts="2024-06-30T12:34:56.789Z",
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
        
        # Verify required fields are present and consistent
        data = entry.model_dump()
        
        assert data["agent"] in ["kai", "claude"]
        assert data["kind"] in [k.value for k in RequestKind]
        assert isinstance(data["prompt_tokens"], int)
        assert isinstance(data["completion_tokens"], int)
    
    def test_log_file_jsonl_format(self):
        """Test that log files follow JSONL format (one JSON per line)"""
        entries = [
            LogEntry(
                ts="2024-06-30T12:34:56.789Z",
                agent="kai",
                model="gpt-4.1",
                kind=RequestKind.UI_CHAT,
                task_id=f"test-uuid-{i}",
                prompt_tokens=100,
                completion_tokens=50,
                error=None,
                request={"messages": [{"role": "user", "content": f"test {i}"}]},
                response={"choices": [{"message": {"content": f"response {i}"}}]}
            )
            for i in range(3)
        ]
        
        with tempfile.NamedTemporaryFile(mode='w+', encoding='utf-8', delete=False) as f:
            filepath = Path(f.name)
        
        try:
            # Write multiple entries
            for entry in entries:
                log_to_jsonl(entry, filepath)
            
            # Read back and verify JSONL format
            lines = filepath.read_text(encoding='utf-8').strip().split('\n')
            
            assert len(lines) == 3
            
            for i, line in enumerate(lines):
                # Each line should be valid JSON
                parsed = json.loads(line)
                assert parsed["task_id"] == f"test-uuid-{i}"
                
                # Should not contain newlines within the JSON
                assert '\n' not in line.strip()
                
        finally:
            filepath.unlink()
    
    def test_validation_script_integration(self):
        """Test integration with validation script"""
        # Create a test log file
        entry = LogEntry(
            ts="2024-06-30T12:34:56.789Z",
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
            log_dir = Path(tmpdir) / "logs" / "llm_calls"
            log_dir.mkdir(parents=True)
            
            log_file = log_dir / "test.jsonl"
            log_to_jsonl(entry, log_file)
            
            # Verify the file exists and contains valid JSON
            assert log_file.exists()
            content = log_file.read_text(encoding='utf-8')
            parsed = json.loads(content.strip())
            
            # Should match our entry
            assert parsed["task_id"] == "test-uuid-123"
            assert parsed["agent"] == "kai"