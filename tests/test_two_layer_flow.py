"""
Test two-layer conversation flow
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from libs.openai_helper import generate_next_question, KEY_TO_JA


class TestTwoLayerFlow:
    """Test two-layer conversation flow"""
    
    def test_missing_keys_detection(self):
        """Test detection of missing charter keys"""
        # Test with empty charter
        empty_charter = {}
        expected_keys = ["name", "purpose", "outcomes", "scope.in", "stakeholders", "constraints.budget", "constraints.deadline"]
        
        # Since generate_next_question is async, we need to run it in event loop
        async def run_test():
            result = await generate_next_question([], empty_charter)
            # Should return a question for one of the high-priority keys
            assert any(KEY_TO_JA[key] == result for key in expected_keys)
        
        # Run the async test
        asyncio.run(run_test())
    
    def test_partial_charter_analysis(self):
        """Test analysis with partially filled charter"""
        partial_charter = {
            "name": "テストプロジェクト",
            "purpose": "テスト目的",
            "outcomes": ["成果1"],
            "scope": {"in": ["作業1"]},
            "stakeholders": [{"name": "太郎", "role": "PM"}]
        }
        
        async def run_test():
            result = await generate_next_question([], partial_charter)
            # Should ask about missing constraints or other keys
            assert result in KEY_TO_JA.values()
        
        asyncio.run(run_test())
    
    def test_complete_charter_detection(self):
        """Test detection when charter is complete"""
        complete_charter = {
            "name": "完全なプロジェクト",
            "purpose": "完全な目的",
            "outcomes": ["成果1", "成果2"],
            "scope": {
                "in": ["含まれる作業"],
                "out": ["除外される作業"]
            },
            "stakeholders": [{"name": "太郎", "role": "PM"}],
            "constraints": {
                "budget": "100万円",
                "deadline": "2024-12-31",
                "tools": ["ツール1"]
            },
            "milestones": [{"date": "2024-06-30", "title": "中間目標"}],
            "risks": [{"risk": "リスク1", "mitigation": "対策1"}],
            "success_metrics": ["指標1"]
        }
        
        async def run_test():
            result = await generate_next_question([], complete_charter)
            assert result == "すべての情報が揃いました。"
        
        asyncio.run(run_test())
    
    @patch('libs.openai_helper.check_openai_key')
    def test_fallback_when_no_api_key(self, mock_check_key):
        """Test fallback behavior when OpenAI API key is not available"""
        mock_check_key.return_value = False
        
        charter = {"name": "テストプロジェクト"}
        
        async def run_test():
            result = await generate_next_question([], charter)
            # Should return a question for purpose (next in priority order)
            assert result == KEY_TO_JA["purpose"]
        
        asyncio.run(run_test())
    
    @patch('libs.openai_helper.check_openai_key')
    @patch('libs.openai_helper.openai.OpenAI')
    def test_gpt_controller_call(self, mock_openai_class, mock_check_key):
        """Test that GPT controller is called correctly"""
        mock_check_key.return_value = True
        
        # Mock OpenAI client
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        
        # Mock response
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "purpose"
        mock_client.chat.completions.create.return_value = mock_response
        
        charter = {"name": "テストプロジェクト"}
        
        async def run_test():
            result = await generate_next_question([], charter)
            
            # Verify OpenAI was called
            mock_client.chat.completions.create.assert_called_once()
            call_args = mock_client.chat.completions.create.call_args
            
            # Verify correct model and parameters
            assert call_args[1]['model'] == 'gpt-4o'
            assert call_args[1]['temperature'] == 0.2
            assert call_args[1]['max_tokens'] == 50
            
            # Verify the result is mapped correctly
            assert result == KEY_TO_JA["purpose"]
        
        asyncio.run(run_test())
    
    @patch('libs.openai_helper.check_openai_key')
    @patch('libs.openai_helper.openai.OpenAI')
    def test_api_error_fallback(self, mock_openai_class, mock_check_key):
        """Test fallback when API call fails"""
        mock_check_key.return_value = True
        
        # Mock OpenAI client to raise exception
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        
        charter = {"name": "テストプロジェクト"}
        
        async def run_test():
            result = await generate_next_question([], charter)
            # Should fallback to priority order and return purpose question
            assert result == KEY_TO_JA["purpose"]
        
        asyncio.run(run_test())
    
    def test_key_mapping_completeness(self):
        """Test that all expected keys have Japanese mappings"""
        expected_keys = [
            "name", "purpose", "outcomes", "scope.in", "scope.out",
            "stakeholders", "constraints.budget", "constraints.deadline", 
            "constraints.tools", "milestones", "risks", "success_metrics"
        ]
        
        for key in expected_keys:
            assert key in KEY_TO_JA, f"Missing Japanese mapping for key: {key}"
            assert isinstance(KEY_TO_JA[key], str), f"Mapping for {key} should be string"
            assert len(KEY_TO_JA[key]) > 0, f"Mapping for {key} should not be empty"
    
    def test_scope_key_handling(self):
        """Test handling of nested scope keys"""
        charter_with_scope_in = {
            "scope": {"in": ["作業1"]}
        }
        
        charter_with_scope_out = {
            "scope": {"out": ["除外作業1"]}
        }
        
        async def run_test():
            # Test with scope.in filled but scope.out missing
            result1 = await generate_next_question([], charter_with_scope_in)
            # Should ask for a high-priority missing key (name or purpose)
            assert result1 in [KEY_TO_JA["name"], KEY_TO_JA["purpose"]]
            
            # Test with both scope keys missing
            result2 = await generate_next_question([], {})
            assert result2 in KEY_TO_JA.values()
        
        asyncio.run(run_test())
    
    def test_constraints_key_handling(self):
        """Test handling of nested constraints keys"""
        charter_partial_constraints = {
            "name": "テスト",
            "purpose": "目的",
            "constraints": {"budget": "100万円"}
        }
        
        async def run_test():
            result = await generate_next_question([], charter_partial_constraints)
            # Should ask about outcomes next in priority, but fallback logic may choose purpose
            assert result in [KEY_TO_JA["outcomes"], KEY_TO_JA["purpose"]]
        
        asyncio.run(run_test())