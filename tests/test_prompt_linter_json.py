"""
Tests for linter.prompt_linter JSON validation functionality
"""

import pytest
import json
import sys
from pathlib import Path
from unittest.mock import patch, Mock
from datetime import datetime

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.log_schema import LogEntry, RequestKind
from linter.prompt_linter import (
    extract_json_from_response, validate_json_structure, lint_log_entries,
    REQUIRED_FIELDS, VALID_INTENTS, VALID_ACTION_TYPES
)


class TestPromptLinterJson:
    """Test prompt linter JSON validation functionality"""
    
    def create_mock_log_entry(self, response_content="", error=None):
        """Create a mock log entry for testing"""
        response = None
        if not error and response_content:
            response = {
                "choices": [
                    {
                        "message": {
                            "content": response_content
                        }
                    }
                ]
            }
        
        return LogEntry(
            ts=datetime.now().isoformat(),
            agent="kai",
            model="gpt-4.1",
            kind=RequestKind.UI_CHAT,
            task_id="test-task-123",
            prompt_tokens=100,
            completion_tokens=50,
            error=error,
            request={"messages": [{"role": "user", "content": "Test message"}]},
            response=response
        )
    
    def test_extract_json_from_markdown_block(self):
        """Test JSON extraction from markdown code block"""
        response_text = """Here is the response:

```json
{
  "intent": "project_management",
  "action_type": "create_project",
  "confidence": 0.9
}
```

That's the JSON response."""
        
        result = extract_json_from_response(response_text)
        
        assert result is not None
        assert result["intent"] == "project_management"
        assert result["action_type"] == "create_project"
        assert result["confidence"] == 0.9
    
    def test_extract_json_from_plain_text(self):
        """Test JSON extraction from plain text"""
        response_text = """
{
  "intent": "conversation",
  "action_type": "general_discussion",
  "confidence": 0.8
}
"""
        
        result = extract_json_from_response(response_text)
        
        assert result is not None
        assert result["intent"] == "conversation"
        assert result["action_type"] == "general_discussion"
        assert result["confidence"] == 0.8
    
    def test_extract_json_from_mixed_content(self):
        """Test JSON extraction from mixed content"""
        response_text = """Some text before JSON

{
  "intent": "clarification",
  "action_type": "information_request",
  "confidence": 0.7
}

Some text after JSON"""
        
        result = extract_json_from_response(response_text)
        
        assert result is not None
        assert result["intent"] == "clarification"
        assert result["action_type"] == "information_request"
    
    def test_extract_json_invalid_json(self):
        """Test JSON extraction with invalid JSON"""
        response_text = """This is not valid JSON:

{
  "intent": "broken"
  "missing_comma": true
}"""
        
        result = extract_json_from_response(response_text)
        assert result is None
    
    def test_extract_json_no_json(self):
        """Test JSON extraction with no JSON content"""
        response_text = "This is just plain text with no JSON content."
        
        result = extract_json_from_response(response_text)
        assert result is None
    
    def test_extract_json_empty_response(self):
        """Test JSON extraction with empty response"""
        result = extract_json_from_response("")
        assert result is None
        
        result = extract_json_from_response(None)
        assert result is None
    
    def test_validate_json_structure_valid(self):
        """Test validation of valid JSON structure"""
        valid_json = {
            "intent": "project_management",
            "action_type": "create_project",
            "reasoning": "User wants to create a project",
            "confidence": 0.9,
            "target_items": [],
            "response_content": "Creating project",
            "suggested_follow_ups": ["What's next?"]
        }
        
        issues = validate_json_structure(valid_json)
        assert len(issues) == 0
    
    def test_validate_json_structure_missing_fields(self):
        """Test validation with missing required fields"""
        incomplete_json = {
            "intent": "project_management",
            "action_type": "create_project",
            # Missing other required fields
        }
        
        issues = validate_json_structure(incomplete_json)
        assert len(issues) > 0
        assert any("Missing required fields" in issue for issue in issues)
    
    def test_validate_json_structure_invalid_intent(self):
        """Test validation with invalid intent"""
        json_with_bad_intent = {
            "intent": "invalid_intent",
            "action_type": "create_project",
            "reasoning": "Test",
            "confidence": 0.9,
            "target_items": [],
            "response_content": "Test",
            "suggested_follow_ups": []
        }
        
        issues = validate_json_structure(json_with_bad_intent)
        assert len(issues) > 0
        assert any("Invalid intent" in issue for issue in issues)
    
    def test_validate_json_structure_invalid_action_type(self):
        """Test validation with invalid action_type"""
        json_with_bad_action = {
            "intent": "project_management",
            "action_type": "invalid_action",
            "reasoning": "Test",
            "confidence": 0.9,
            "target_items": [],
            "response_content": "Test",
            "suggested_follow_ups": []
        }
        
        issues = validate_json_structure(json_with_bad_action)
        assert len(issues) > 0
        assert any("Invalid action_type" in issue for issue in issues)
    
    def test_validate_json_structure_invalid_confidence(self):
        """Test validation with invalid confidence values"""
        test_cases = [
            {"confidence": -0.1},  # Below 0
            {"confidence": 1.1},   # Above 1
            {"confidence": "high"}, # Wrong type
        ]
        
        base_json = {
            "intent": "project_management",
            "action_type": "create_project",
            "reasoning": "Test",
            "target_items": [],
            "response_content": "Test",
            "suggested_follow_ups": []
        }
        
        for test_case in test_cases:
            json_obj = {**base_json, **test_case}
            issues = validate_json_structure(json_obj)
            assert len(issues) > 0
            assert any("confidence" in issue.lower() for issue in issues)
    
    def test_validate_json_structure_invalid_array_types(self):
        """Test validation with invalid array field types"""
        base_json = {
            "intent": "project_management",
            "action_type": "create_project",
            "reasoning": "Test",
            "confidence": 0.9,
            "response_content": "Test"
        }
        
        # Test invalid target_items type
        json_with_bad_target_items = {
            **base_json,
            "target_items": "not an array",
            "suggested_follow_ups": []
        }
        
        issues = validate_json_structure(json_with_bad_target_items)
        assert any("target_items should be a list" in issue for issue in issues)
        
        # Test invalid suggested_follow_ups type
        json_with_bad_follow_ups = {
            **base_json,
            "target_items": [],
            "suggested_follow_ups": "not an array"
        }
        
        issues = validate_json_structure(json_with_bad_follow_ups)
        assert any("suggested_follow_ups should be a list" in issue for issue in issues)
    
    def test_lint_log_entries_empty(self):
        """Test linting with empty log entries"""
        result = lint_log_entries([])
        
        assert result["summary"]["total_entries"] == 0
        assert result["summary"]["successful_responses"] == 0
        assert result["summary"]["json_parse_errors"] == 0
        assert result["summary"]["schema_validation_errors"] == 0
        assert result["summary"]["perfect_responses"] == 0
    
    def test_lint_log_entries_error_entries(self):
        """Test linting with error entries (should be skipped)"""
        error_entry = self.create_mock_log_entry(error="rate_limit")
        entries = [error_entry]
        
        result = lint_log_entries(entries)
        
        # Error entries should be skipped
        assert result["summary"]["total_entries"] == 1
        assert result["summary"]["successful_responses"] == 0
    
    def test_lint_log_entries_no_response(self):
        """Test linting with entries that have no response"""
        no_response_entry = self.create_mock_log_entry()
        no_response_entry.response = None
        entries = [no_response_entry]
        
        result = lint_log_entries(entries)
        
        # No response entries should be skipped
        assert result["summary"]["successful_responses"] == 0
    
    def test_lint_log_entries_parse_error(self):
        """Test linting with JSON parse errors"""
        invalid_json_response = "This is not JSON at all"
        entry = self.create_mock_log_entry(response_content=invalid_json_response)
        entries = [entry]
        
        result = lint_log_entries(entries)
        
        assert result["summary"]["successful_responses"] == 1
        assert result["summary"]["json_parse_errors"] == 1
        assert result["summary"]["perfect_responses"] == 0
        assert len(result["samples"]["parse_errors"]) == 1
        assert result["error_breakdown"]["json_parse_error"] == 1
    
    def test_lint_log_entries_validation_error(self):
        """Test linting with schema validation errors"""
        # JSON that parses but fails validation
        invalid_structure = {
            "intent": "invalid_intent",  # Invalid intent
            "action_type": "create_project",
            # Missing required fields
        }
        
        response_content = f"```json\n{json.dumps(invalid_structure)}\n```"
        entry = self.create_mock_log_entry(response_content=response_content)
        entries = [entry]
        
        result = lint_log_entries(entries)
        
        assert result["summary"]["successful_responses"] == 1
        assert result["summary"]["json_parse_errors"] == 0
        assert result["summary"]["schema_validation_errors"] == 1
        assert result["summary"]["perfect_responses"] == 0
        assert len(result["samples"]["validation_errors"]) == 1
        assert len(result["issues"]) > 0
    
    def test_lint_log_entries_perfect_response(self):
        """Test linting with perfect responses"""
        perfect_json = {
            "intent": "project_management",
            "action_type": "create_project",
            "reasoning": "User wants to create a project",
            "confidence": 0.9,
            "target_items": [],
            "response_content": "Creating project",
            "suggested_follow_ups": ["What's next?"]
        }
        
        response_content = f"```json\n{json.dumps(perfect_json)}\n```"
        entry = self.create_mock_log_entry(response_content=response_content)
        entries = [entry]
        
        result = lint_log_entries(entries)
        
        assert result["summary"]["successful_responses"] == 1
        assert result["summary"]["json_parse_errors"] == 0
        assert result["summary"]["schema_validation_errors"] == 0
        assert result["summary"]["perfect_responses"] == 1
        assert len(result["samples"]["perfect_examples"]) == 1
        assert len(result["issues"]) == 0
    
    def test_lint_log_entries_mixed_results(self):
        """Test linting with mixed results"""
        entries = [
            # Perfect response
            self.create_mock_log_entry(
                response_content=f"```json\n{json.dumps({\n'intent': 'project_management',\n'action_type': 'create_project',\n'reasoning': 'Test',\n'confidence': 0.9,\n'target_items': [],\n'response_content': 'Test',\n'suggested_follow_ups': []\n})}\n```"
            ),
            # Parse error
            self.create_mock_log_entry(response_content="Not JSON"),
            # Validation error
            self.create_mock_log_entry(
                response_content=f"```json\n{json.dumps({'intent': 'invalid'})}\n```"
            ),
            # Error entry (should be skipped)
            self.create_mock_log_entry(error="timeout")
        ]
        
        result = lint_log_entries(entries)
        
        assert result["summary"]["total_entries"] == 4
        assert result["summary"]["successful_responses"] == 3  # Excludes error entry
        assert result["summary"]["json_parse_errors"] == 1
        assert result["summary"]["schema_validation_errors"] == 1
        assert result["summary"]["perfect_responses"] == 1
    
    def test_required_fields_constant(self):
        """Test that REQUIRED_FIELDS constant is properly defined"""
        expected_fields = {
            "intent", "action_type", "reasoning", "confidence", 
            "target_items", "response_content", "suggested_follow_ups"
        }
        assert REQUIRED_FIELDS == expected_fields
    
    def test_valid_constants(self):
        """Test that valid value constants are properly defined"""
        assert "project_management" in VALID_INTENTS
        assert "conversation" in VALID_INTENTS
        assert "clarification" in VALID_INTENTS
        assert "error" in VALID_INTENTS
        
        assert "create_project" in VALID_ACTION_TYPES
        assert "create_task" in VALID_ACTION_TYPES
        assert "remove_task" in VALID_ACTION_TYPES
        assert "general_discussion" in VALID_ACTION_TYPES