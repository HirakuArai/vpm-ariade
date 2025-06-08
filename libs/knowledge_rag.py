"""
Knowledge RAG module for dynamic domain information retrieval
"""

import hashlib
import json
import os
from pathlib import Path
from typing import Optional
import openai
from duckduckgo_search import DDGS


def get_domain_info(query: str, max_tokens: int = 300) -> str:
    """
    Get domain information for a query using cached results or web search + summarization
    
    Args:
        query: The domain query to search for
        max_tokens: Maximum tokens for the summary
        
    Returns:
        Summarized domain information as string
    """
    # Create cache directory
    cache_dir = Path("data/cache")
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate cache key from query hash
    query_hash = hashlib.sha256(query.encode('utf-8')).hexdigest()[:16]
    cache_file = cache_dir / f"{query_hash}.md"
    
    # Return cached result if exists
    if cache_file.exists():
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception:
            # If cache file is corrupted, continue to regenerate
            pass
    
    # Perform web search and summarization
    try:
        # Search with DuckDuckGo
        search_results = []
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=3))
            for result in results:
                # Truncate each result to ~250 chars
                body = result.get('body', '')[:250]
                title = result.get('title', '')
                search_results.append(f"**{title}**: {body}")
        
        if not search_results:
            return "関連情報が見つかりませんでした。"
        
        # Combine search results
        combined_text = "\n\n".join(search_results)
        
        # Summarize using OpenAI
        summary = _summarize_text(combined_text, query, max_tokens)
        
        # Cache the result
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                f.write(summary)
        except Exception:
            # Cache write failure is not critical
            pass
        
        return summary
        
    except Exception as e:
        return f"情報取得中にエラーが発生しました: {str(e)}"


def _summarize_text(text: str, original_query: str, max_tokens: int) -> str:
    """
    Summarize text using OpenAI API
    
    Args:
        text: Text to summarize
        original_query: Original query for context
        max_tokens: Maximum tokens for summary
        
    Returns:
        Summarized text
    """
    try:
        # Check if OpenAI key is available
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return "OpenAI API キーが設定されていないため、要約できませんでした。"
        
        client = openai.OpenAI()
        
        prompt = f"""以下のテキストを、「{original_query}」というクエリに関連する重要な情報を中心に、{max_tokens}トークン以内で日本語で要約してください。

テキスト:
{text}

要約:"""
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens,
            temperature=0
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        return f"要約中にエラーが発生しました: {str(e)}"


def clear_cache(older_than_days: int = 7) -> int:
    """
    Clear cache files older than specified days
    
    Args:
        older_than_days: Remove files older than this many days
        
    Returns:
        Number of files removed
    """
    cache_dir = Path("data/cache")
    if not cache_dir.exists():
        return 0
    
    import time
    current_time = time.time()
    cutoff_time = current_time - (older_than_days * 24 * 60 * 60)
    
    removed_count = 0
    for cache_file in cache_dir.glob("*.md"):
        try:
            if cache_file.stat().st_mtime < cutoff_time:
                cache_file.unlink()
                removed_count += 1
        except Exception:
            continue
    
    return removed_count