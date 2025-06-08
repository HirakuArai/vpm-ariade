"""
Test conversational charter generation mode
"""

import pytest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from libs.openai_helper import ask_gpt, extract_charter_json, get_system_prompt, check_openai_key


class TestOpenAIHelper:
    """Test OpenAI helper functions"""
    
    def test_system_prompt_contains_charter_complete(self):
        """Test that system prompt contains <charter_complete/> instruction"""
        prompt = get_system_prompt()
        assert "<charter_complete/>" in prompt
        assert "JSON block" in prompt
        assert "Ask ONE question at a time in Japanese" in prompt
    
    @patch('libs.openai_helper.os.getenv')
    def test_check_openai_key_with_key(self, mock_getenv):
        """Test OpenAI key check when key is available"""
        mock_getenv.return_value = "test-api-key"
        result = check_openai_key()
        assert result is True
    
    @patch('libs.openai_helper.os.getenv')
    def test_check_openai_key_without_key(self, mock_getenv):
        """Test OpenAI key check when key is missing"""
        mock_getenv.return_value = None
        result = check_openai_key()
        assert result is False
    
    def test_extract_charter_json_valid(self):
        """Test extracting valid charter JSON from response"""
        response = """質問ありがとうございます！
        
<charter_complete/>
```json
{
  "name": "テストプロジェクト",
  "purpose": "テスト目的",
  "outcomes": ["成果1", "成果2"],
  "scope": {
    "in": ["含まれるもの"],
    "out": ["除外されるもの"]
  },
  "stakeholders": [
    {"name": "田中太郎", "role": "プロジェクトマネージャー"}
  ],
  "constraints": {
    "budget": "100万円",
    "deadline": "2024-12-31"
  },
  "milestones": [
    {"date": "2024-06-30", "title": "中間報告"}
  ],
  "risks": [
    {"risk": "スケジュール遅延", "mitigation": "週次進捗確認"}
  ],
  "success_metrics": ["品質向上", "コスト削減"]
}
```"""
        
        result = extract_charter_json(response)
        assert result is not None
        assert result["name"] == "テストプロジェクト"
        assert result["purpose"] == "テスト目的"
        assert len(result["outcomes"]) == 2
        assert len(result["stakeholders"]) == 1
        assert result["stakeholders"][0]["name"] == "田中太郎"
    
    def test_extract_charter_json_without_complete_token(self):
        """Test extracting JSON when no <charter_complete/> token"""
        response = "まだ質問を続けます。プロジェクトの目的は何ですか？"
        
        result = extract_charter_json(response)
        assert result is None
    
    def test_extract_charter_json_invalid_json(self):
        """Test extracting invalid JSON"""
        response = """<charter_complete/>
```json
{
  "name": "テストプロジェクト",
  "purpose": // invalid comment
}
```"""
        
        result = extract_charter_json(response)
        assert result is None
    
    @patch('libs.openai_helper.openai.OpenAI')
    @patch('libs.openai_helper.check_openai_key')
    def test_ask_gpt_successful(self, mock_check_key, mock_openai_class):
        """Test successful OpenAI API call"""
        # Setup mocks
        mock_check_key.return_value = True
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        
        # Mock response
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "AIからの応答です"
        mock_client.chat.completions.create.return_value = mock_response
        
        # Test
        messages = [{"role": "user", "content": "テストメッセージ"}]
        result = ask_gpt(messages)
        
        assert result == "AIからの応答です"
        mock_client.chat.completions.create.assert_called_once()
    
    @patch('libs.openai_helper.check_openai_key')
    def test_ask_gpt_no_api_key(self, mock_check_key):
        """Test OpenAI API call without API key"""
        mock_check_key.return_value = False
        
        messages = [{"role": "user", "content": "テストメッセージ"}]
        
        with pytest.raises(Exception) as exc_info:
            ask_gpt(messages)
        
        assert "OPENAI_API_KEY environment variable is required" in str(exc_info.value)


class TestConversationalFlow:
    """Test conversational charter generation flow"""
    
    def test_two_turn_conversation_simulation(self):
        """Test simulated 2-turn conversation that completes charter"""
        
        # Simulate conversation without actual API calls
        conversation = []
        
        # Simulate first exchange
        conversation.append({
            "role": "user", 
            "content": "新しいプロジェクトを始めたいのですが、チャーターを作成するのを手伝ってください。"
        })
        conversation.append({
            "role": "assistant", 
            "content": "こんにちは！プロジェクトの名前を教えてください。"
        })
        
        # Simulate second exchange with completion
        conversation.append({
            "role": "user", 
            "content": "Webサイトリニューアルプロジェクトです"
        })
        
        completion_response = """ありがとうございます！十分な情報が集まりました。

<charter_complete/>
```json
{
  "name": "Webサイトリニューアル",
  "purpose": "ユーザー体験の向上とコンバージョン率の改善",
  "outcomes": ["新しいWebサイト", "ユーザー満足度向上"],
  "scope": {
    "in": ["UIデザイン", "フロントエンド開発"],
    "out": ["バックエンド機能追加"]
  },
  "stakeholders": [
    {"name": "佐藤花子", "role": "プロダクトマネージャー"}
  ],
  "constraints": {
    "budget": "500万円",
    "deadline": "2024-09-30"
  },
  "milestones": [
    {"date": "2024-07-31", "title": "デザイン完成"}
  ],
  "risks": [
    {"risk": "技術的課題", "mitigation": "専門家コンサルテーション"}
  ],
  "success_metrics": ["コンバージョン率20%向上"]
}
```"""
        
        conversation.append({
            "role": "assistant", 
            "content": completion_response
        })
        
        # Extract and verify charter
        charter_data = extract_charter_json(completion_response)
        
        assert charter_data is not None
        assert charter_data["name"] == "Webサイトリニューアル"
        assert charter_data["purpose"] == "ユーザー体験の向上とコンバージョン率の改善"
        assert len(charter_data["outcomes"]) == 2
        assert charter_data["constraints"]["budget"] == "500万円"
        
        # Verify conversation flow
        assert len(conversation) == 4
        assert conversation[0]["role"] == "user"
        assert conversation[1]["role"] == "assistant"
        assert conversation[2]["role"] == "user"
        assert conversation[3]["role"] == "assistant"
        assert "<charter_complete/>" in conversation[3]["content"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])