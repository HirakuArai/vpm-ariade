# -*- coding: utf-8 -*-
"""
AI Context Manager - 高度なAIコンテキスト管理システム
会話履歴の効率的な管理、要約、関連性分析を提供
"""

import json
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, asdict
import hashlib

try:
    import openai
except ImportError:
    openai = None

logger = logging.getLogger(__name__)

@dataclass
class ConversationContext:
    """会話コンテキストデータクラス"""
    project_id: Optional[str]
    conversation_id: str
    messages: List[Dict[str, str]]
    summary: Optional[str] = None
    key_points: List[str] = None
    last_updated: Optional[str] = None
    relevance_score: float = 1.0
    token_count: int = 0
    
    def __post_init__(self):
        if self.key_points is None:
            self.key_points = []
        if self.last_updated is None:
            self.last_updated = datetime.now().isoformat()

@dataclass
class ContextWindow:
    """AIへ送信するコンテキストウィンドウ"""
    system_prompt: str
    relevant_history: List[Dict[str, str]]
    current_conversation: List[Dict[str, str]]
    total_tokens: int
    context_summary: Optional[str] = None

class AIContextManager:
    """高度なAIコンテキスト管理システム"""
    
    def __init__(self, openai_api_key: str, max_context_tokens: int = 8000):
        """
        Initialize AI Context Manager
        
        Args:
            openai_api_key: OpenAI API key
            max_context_tokens: 最大コンテキストトークン数
        """
        self.api_key = openai_api_key
        self.max_context_tokens = max_context_tokens
        self.min_relevance_threshold = 0.3
        
        # Context storage
        self.contexts: Dict[str, ConversationContext] = {}
        self.summaries: Dict[str, str] = {}
        
        try:
            if openai:
                self.client = openai.OpenAI(api_key=openai_api_key)
                self.available = True
            else:
                logger.error("OpenAI package not available")
                self.available = False
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
            self.available = False
    
    def generate_conversation_id(self, project_id: Optional[str], timestamp: datetime) -> str:
        """会話IDを生成"""
        base_string = f"{project_id or 'global'}_{timestamp.strftime('%Y%m%d_%H%M%S')}"
        return hashlib.md5(base_string.encode()).hexdigest()[:12]
    
    def estimate_token_count(self, text: str) -> int:
        """テキストのトークン数を概算"""
        # 簡易的な推定（正確にはtiktokenを使用）
        return len(text.split()) * 1.3  # 大まかな目安
    
    def add_conversation(self, project_id: Optional[str], messages: List[Dict[str, str]]) -> str:
        """新しい会話をコンテキストに追加"""
        timestamp = datetime.now()
        conversation_id = self.generate_conversation_id(project_id, timestamp)
        
        # トークン数計算
        total_tokens = sum(self.estimate_token_count(msg.get('content', '')) for msg in messages)
        
        context = ConversationContext(
            project_id=project_id,
            conversation_id=conversation_id,
            messages=messages,
            last_updated=timestamp.isoformat(),
            token_count=total_tokens
        )
        
        self.contexts[conversation_id] = context
        
        # 長い会話の場合は要約を生成
        if total_tokens > 1000 and self.available:
            self._generate_conversation_summary(conversation_id)
        
        logger.info(f"Added conversation {conversation_id} with {len(messages)} messages")
        return conversation_id
    
    def _generate_conversation_summary(self, conversation_id: str) -> Optional[str]:
        """会話の要約を生成"""
        if not self.available:
            return None
        
        context = self.contexts.get(conversation_id)
        if not context:
            return None
        
        try:
            # メッセージを結合
            conversation_text = "\n".join([
                f"{msg.get('role', 'unknown')}: {msg.get('content', '')}"
                for msg in context.messages
            ])
            
            summary_prompt = f"""
以下の会話を簡潔に要約してください。重要なポイントと決定事項を含めてください：

{conversation_text[:2000]}  # 長すぎる場合は切り詰め

要約は以下の形式で：
- 主要トピック:
- 重要な決定/合意:
- 次のアクション:
- キーワード:
"""
            
            from core.v2.openai_config import create_chat_completion
            response = create_chat_completion(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "あなたは会話要約の専門家です。簡潔で有用な要約を作成してください。"},
                    {"role": "user", "content": summary_prompt}
                ],
                temperature=0.3,
                max_tokens=300
            )
            
            summary = response.choices[0].message.content.strip()
            context.summary = summary
            
            # キーポイントの抽出
            key_points = self._extract_key_points(summary)
            context.key_points = key_points
            
            logger.info(f"Generated summary for conversation {conversation_id}")
            return summary
            
        except Exception as e:
            logger.error(f"Failed to generate summary for {conversation_id}: {e}")
            return None
    
    def _extract_key_points(self, summary: str) -> List[str]:
        """要約からキーポイントを抽出"""
        # 簡易的な実装 - 改行区切りで箇条書きを抽出
        lines = summary.split('\n')
        key_points = []
        
        for line in lines:
            line = line.strip()
            if line and (line.startswith('-') or line.startswith('•') or line.startswith('*')):
                clean_point = line.lstrip('-•* ').strip()
                if clean_point:
                    key_points.append(clean_point)
        
        return key_points[:5]  # 最大5つまで
    
    def calculate_relevance_score(self, context: ConversationContext, current_query: str, project_id: Optional[str]) -> float:
        """コンテキストの関連性スコアを計算"""
        score = 0.0
        
        # プロジェクト一致度
        if context.project_id == project_id:
            score += 0.5
        elif context.project_id is None and project_id is None:
            score += 0.3
        
        # 時間的関連性（最近の会話ほど高スコア）
        if context.last_updated:
            try:
                last_time = datetime.fromisoformat(context.last_updated)
                time_diff = datetime.now() - last_time
                time_score = max(0, 1 - (time_diff.days / 30))  # 30日で0になる
                score += time_score * 0.3
            except:
                pass
        
        # キーワード関連性
        if context.summary and current_query:
            query_words = set(current_query.lower().split())
            summary_words = set(context.summary.lower().split())
            
            if query_words and summary_words:
                keyword_overlap = len(query_words.intersection(summary_words)) / len(query_words.union(summary_words))
                score += keyword_overlap * 0.2
        
        return min(score, 1.0)
    
    def build_context_window(self, current_messages: List[Dict[str, str]], 
                           current_query: str, project_id: Optional[str],
                           system_prompt: str) -> ContextWindow:
        """現在の状況に最適化されたコンテキストウィンドウを構築"""
        
        # 関連性スコアでコンテキストをソート
        relevant_contexts = []
        for context in self.contexts.values():
            relevance = self.calculate_relevance_score(context, current_query, project_id)
            if relevance >= self.min_relevance_threshold:
                relevant_contexts.append((context, relevance))
        
        relevant_contexts.sort(key=lambda x: x[1], reverse=True)
        
        # トークン制限内で最適なコンテキストを選択
        system_tokens = self.estimate_token_count(system_prompt)
        current_tokens = sum(self.estimate_token_count(msg.get('content', '')) for msg in current_messages)
        available_tokens = self.max_context_tokens - system_tokens - current_tokens - 500  # 応答用余裕
        
        selected_history = []
        used_tokens = 0
        
        for context, relevance in relevant_contexts:
            if context.summary:
                # 要約を使用
                summary_tokens = self.estimate_token_count(context.summary)
                if used_tokens + summary_tokens <= available_tokens:
                    selected_history.append({
                        "role": "system",
                        "content": f"[過去の会話要約] {context.summary}"
                    })
                    used_tokens += summary_tokens
            elif context.token_count <= available_tokens - used_tokens:
                # 全メッセージを追加
                for msg in context.messages[-5:]:  # 最新5メッセージまで
                    if used_tokens + self.estimate_token_count(msg.get('content', '')) <= available_tokens:
                        selected_history.append(msg)
                        used_tokens += self.estimate_token_count(msg.get('content', ''))
                    else:
                        break
            
            if used_tokens >= available_tokens * 0.8:  # 80%で停止
                break
        
        # コンテキスト要約
        context_summary = None
        if selected_history:
            context_summary = f"{len(selected_history)}件の関連する過去の会話を参考にしています。"
        
        return ContextWindow(
            system_prompt=system_prompt,
            relevant_history=selected_history,
            current_conversation=current_messages,
            total_tokens=system_tokens + used_tokens + current_tokens,
            context_summary=context_summary
        )
    
    def get_conversation_stats(self) -> Dict[str, Any]:
        """コンテキスト管理の統計情報"""
        total_conversations = len(self.contexts)
        total_tokens = sum(ctx.token_count for ctx in self.contexts.values())
        summarized_count = sum(1 for ctx in self.contexts.values() if ctx.summary)
        
        project_distribution = {}
        for ctx in self.contexts.values():
            proj = ctx.project_id or "global"
            project_distribution[proj] = project_distribution.get(proj, 0) + 1
        
        return {
            "total_conversations": total_conversations,
            "total_tokens": total_tokens,
            "summarized_conversations": summarized_count,
            "project_distribution": project_distribution,
            "average_tokens_per_conversation": total_tokens / total_conversations if total_conversations > 0 else 0
        }
    
    def cleanup_old_contexts(self, days_threshold: int = 30):
        """古いコンテキストをクリーンアップ"""
        cutoff_date = datetime.now() - timedelta(days=days_threshold)
        
        to_remove = []
        for conv_id, context in self.contexts.items():
            if context.last_updated:
                try:
                    last_time = datetime.fromisoformat(context.last_updated)
                    if last_time < cutoff_date:
                        to_remove.append(conv_id)
                except:
                    pass
        
        for conv_id in to_remove:
            del self.contexts[conv_id]
        
        logger.info(f"Cleaned up {len(to_remove)} old contexts")
        return len(to_remove)

def create_context_manager(api_key: str) -> AIContextManager:
    """AIContextManagerのファクトリ関数"""
    return AIContextManager(api_key)