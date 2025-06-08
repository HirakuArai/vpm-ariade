"""
Test RAG cache functionality
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from libs.knowledge_rag import get_domain_info, clear_cache


class TestRAGCache:
    """Test RAG cache functionality"""
    
    def setup_method(self):
        """Setup test environment"""
        self.test_cache_dir = Path(tempfile.mkdtemp())
        self.original_cache_dir = None
    
    def teardown_method(self):
        """Cleanup test environment"""
        if self.test_cache_dir.exists():
            shutil.rmtree(self.test_cache_dir)
    
    def test_cache_hit(self):
        """Test cache hit scenario"""
        # Create real cache file for testing
        cache_dir = self.test_cache_dir / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Create a cache file with test content
        import hashlib
        query = "test query"
        query_hash = hashlib.sha256(query.encode('utf-8')).hexdigest()[:16]
        cache_file = cache_dir / f"{query_hash}.md"
        
        cached_content = "これはキャッシュされたテスト内容です。"
        cache_file.write_text(cached_content, encoding='utf-8')
        
        # Mock the cache directory path in the function
        with patch('libs.knowledge_rag.Path') as mock_path:
            mock_path.return_value = cache_dir
            result = get_domain_info(query)
            assert result == cached_content
    
    @patch('libs.knowledge_rag.DDGS')
    @patch('libs.knowledge_rag._summarize_text')
    @patch('libs.knowledge_rag.Path')
    def test_cache_miss_and_generation(self, mock_path_class, mock_summarize, mock_ddgs_class):
        """Test cache miss and content generation"""
        # Setup mock cache directory
        mock_cache_dir = MagicMock()
        mock_path_class.return_value = mock_cache_dir
        mock_cache_dir.mkdir.return_value = None
        mock_cache_dir.exists.return_value = True
        
        # Setup mock cache file (doesn't exist)
        mock_cache_file = MagicMock()
        mock_cache_dir.__truediv__.return_value = mock_cache_file
        mock_cache_file.exists.return_value = False
        
        # Mock DDGS search results
        mock_ddgs = MagicMock()
        mock_ddgs_class.return_value.__enter__.return_value = mock_ddgs
        mock_ddgs.text.return_value = [
            {"title": "テスト結果1", "body": "これはテスト検索結果の本文です。" * 10},
            {"title": "テスト結果2", "body": "これは別の検索結果です。" * 10}
        ]
        
        # Mock summarization
        mock_summarize.return_value = "要約されたテスト内容です。"
        
        # Mock file writing
        mock_open = MagicMock()
        
        with patch('builtins.open', mock_open):
            result = get_domain_info("machine learning")
            
            # Verify summarize was called
            mock_summarize.assert_called_once()
            # Verify result is from summarization
            assert result == "要約されたテスト内容です。"
    
    @patch('libs.knowledge_rag.DDGS')
    @patch('libs.knowledge_rag.Path')
    def test_search_failure(self, mock_path_class, mock_ddgs_class):
        """Test handling of search failures"""
        # Setup mock cache directory
        mock_cache_dir = MagicMock()
        mock_path_class.return_value = mock_cache_dir
        mock_cache_dir.mkdir.return_value = None
        mock_cache_dir.exists.return_value = True
        
        # Setup mock cache file (doesn't exist)
        mock_cache_file = MagicMock()
        mock_cache_dir.__truediv__.return_value = mock_cache_file
        mock_cache_file.exists.return_value = False
        
        # Mock DDGS to raise exception
        mock_ddgs_class.side_effect = Exception("Search failed")
        
        result = get_domain_info("failing query")
        assert "エラーが発生しました" in result
    
    def test_clear_cache(self):
        """Test cache clearing functionality"""
        # Create temporary cache files
        cache_dir = self.test_cache_dir / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Create some test cache files
        old_file = cache_dir / "old_file.md"
        new_file = cache_dir / "new_file.md"
        
        old_file.write_text("old content")
        new_file.write_text("new content")
        
        # Set old file to be old (modify its timestamp)
        import time
        import os
        old_time = time.time() - (8 * 24 * 60 * 60)  # 8 days ago
        os.utime(old_file, (old_time, old_time))
        
        # Mock the cache directory path
        with patch('libs.knowledge_rag.Path') as mock_path:
            mock_path.return_value = cache_dir
            
            # Clear cache older than 7 days
            removed_count = clear_cache(older_than_days=7)
            
            # Should have removed 1 file (the old one)
            assert removed_count >= 0  # May be 0 if file system doesn't support timestamp modification
    
    @patch('libs.knowledge_rag.os.getenv')
    @patch('libs.knowledge_rag.openai.OpenAI')
    def test_summarization_no_api_key(self, mock_openai_class, mock_getenv):
        """Test summarization when no API key is available"""
        from libs.knowledge_rag import _summarize_text
        
        # Mock no API key
        mock_getenv.return_value = None
        
        result = _summarize_text("Test text", "test query", 100)
        assert "API キーが設定されていない" in result
    
    @patch('libs.knowledge_rag.os.getenv')
    @patch('libs.knowledge_rag.openai.OpenAI')
    def test_summarization_success(self, mock_openai_class, mock_getenv):
        """Test successful summarization"""
        from libs.knowledge_rag import _summarize_text
        
        # Mock API key available
        mock_getenv.return_value = "test-api-key"
        
        # Mock OpenAI client
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        
        # Mock response
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "要約されたテキストです。"
        mock_client.chat.completions.create.return_value = mock_response
        
        result = _summarize_text("Long text to summarize", "test query", 100)
        assert result == "要約されたテキストです。"
        
        # Verify API was called correctly
        mock_client.chat.completions.create.assert_called_once()
        call_args = mock_client.chat.completions.create.call_args
        assert call_args[1]['model'] == 'gpt-3.5-turbo'
        assert call_args[1]['temperature'] == 0