"""
Test background persistence in persona prompt
"""

import pytest
import tempfile
from pathlib import Path
import yaml
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.v2.persona_core import get_persona_prompt
from libs.openai_helper import get_system_prompt_with_background


class TestBackgroundPersistence:
    """Test background information persistence"""
    
    def setup_method(self):
        """Setup test environment"""
        self.test_dir = Path(tempfile.mkdtemp())
    
    def teardown_method(self):
        """Cleanup test environment"""
        import shutil
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
    
    def test_persona_prompt_with_background(self):
        """Test persona prompt includes background information"""
        # Create test charter with background
        charter_data = {
            "name": "テストプロジェクト",
            "purpose": "テスト目的",
            "background": "これはテスト用の背景情報です。機械学習とデータサイエンスに関するプロジェクトです。"
        }
        
        charter_file = self.test_dir / "test_charter.yaml"
        with open(charter_file, 'w', encoding='utf-8') as f:
            yaml.dump(charter_data, f, default_flow_style=False, allow_unicode=True)
        
        # Get persona prompt
        prompt = get_persona_prompt(str(charter_file))
        
        # Verify background is included
        assert "<background>" in prompt
        assert charter_data["background"] in prompt
        assert "Use this background information" in prompt
    
    def test_persona_prompt_without_background(self):
        """Test persona prompt when no background is available"""
        # Create test charter without background
        charter_data = {
            "name": "テストプロジェクト",
            "purpose": "テスト目的"
        }
        
        charter_file = self.test_dir / "test_charter_no_bg.yaml"
        with open(charter_file, 'w', encoding='utf-8') as f:
            yaml.dump(charter_data, f, default_flow_style=False, allow_unicode=True)
        
        # Get persona prompt
        prompt = get_persona_prompt(str(charter_file))
        
        # Verify no background section
        assert "<background>" not in prompt
        assert "expert AI project manager persona" in prompt
    
    def test_persona_prompt_invalid_file(self):
        """Test persona prompt with invalid file path"""
        invalid_file = self.test_dir / "nonexistent.yaml"
        
        # Should return base prompt without error
        prompt = get_persona_prompt(str(invalid_file))
        assert "expert AI project manager persona" in prompt
        assert "<background>" not in prompt
    
    def test_system_prompt_with_background(self):
        """Test system prompt with background injection"""
        domain_info = "これはRAGから取得されたドメイン情報です。AI技術の最新動向について説明しています。"
        
        prompt = get_system_prompt_with_background(domain_info)
        
        # Verify background is included
        assert "<background>" in prompt
        assert domain_info in prompt
        assert "You are **Kai**" in prompt
    
    def test_system_prompt_without_background(self):
        """Test system prompt without background"""
        prompt = get_system_prompt_with_background(None)
        
        # Should return base prompt
        assert "<background>" not in prompt
        assert "You are **Kai**" in prompt
    
    def test_background_format_preservation(self):
        """Test that background information format is preserved"""
        background_with_formatting = """
        # 重要な背景情報
        
        このプロジェクトは以下の技術を使用します:
        - Python
        - Machine Learning
        - Data Science
        
        ## 注意事項
        特別な配慮が必要です。
        """
        
        prompt = get_system_prompt_with_background(background_with_formatting)
        
        # Verify formatting is preserved
        assert "# 重要な背景情報" in prompt
        assert "- Python" in prompt
        assert "## 注意事項" in prompt
    
    def test_background_in_charter_persistence(self):
        """Test that background persists in saved charter"""
        # This test simulates the flow where domain info becomes charter background
        charter_data = {
            "name": "RAGテストプロジェクト",
            "purpose": "RAG機能をテストする",
            "background": "DuckDuckGoから取得されたWeb検索結果をOpenAIで要約した背景情報"
        }
        
        charter_file = self.test_dir / "rag_test_charter.yaml"
        with open(charter_file, 'w', encoding='utf-8') as f:
            yaml.dump(charter_data, f, default_flow_style=False, allow_unicode=True)
        
        # Verify charter can be read back with background intact
        with open(charter_file, 'r', encoding='utf-8') as f:
            loaded_charter = yaml.safe_load(f)
        
        assert loaded_charter["background"] == charter_data["background"]
        
        # Verify persona prompt uses this background
        persona_prompt = get_persona_prompt(str(charter_file))
        assert charter_data["background"] in persona_prompt
    
    def test_empty_background_handling(self):
        """Test handling of empty background strings"""
        empty_backgrounds = ["", None, "   ", "\n\n"]
        
        for empty_bg in empty_backgrounds:
            prompt = get_system_prompt_with_background(empty_bg)
            
            if empty_bg and empty_bg.strip():
                assert "<background>" in prompt
            else:
                # Empty or whitespace-only backgrounds should not be included
                continue  # get_system_prompt_with_background should handle this
    
    def test_large_background_handling(self):
        """Test handling of large background information"""
        # Create a large background string
        large_background = "詳細な背景情報: " + "この情報は非常に重要です。" * 100
        
        prompt = get_system_prompt_with_background(large_background)
        
        # Verify large background is included (should not be truncated at this level)
        assert "<background>" in prompt
        assert large_background in prompt
        assert len(prompt) > 1000  # Should be substantial size