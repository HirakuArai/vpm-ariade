# -*- coding: utf-8 -*-
"""
AI Quality Manager - AI品質管理とエラーハンドリングシステム
AI応答の品質監視、エラー検出、自動回復機能
"""

import json
import logging
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import time
import hashlib

try:
    import openai
except ImportError:
    openai = None

logger = logging.getLogger(__name__)

class ResponseQuality(Enum):
    """応答品質レベル"""
    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    POOR = "poor"
    ERROR = "error"

class ErrorType(Enum):
    """エラータイプ"""
    API_ERROR = "api_error"
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"
    INVALID_RESPONSE = "invalid_response"
    CONTEXT_TOO_LONG = "context_too_long"
    NETWORK_ERROR = "network_error"

@dataclass
class AIResponse:
    """AI応答データクラス"""
    request_id: str
    prompt: str
    response: str
    model: str
    timestamp: datetime
    response_time: float
    token_count: int
    quality_score: Optional[float] = None
    quality_level: Optional[ResponseQuality] = None
    error_type: Optional[ErrorType] = None
    error_message: Optional[str] = None
    retry_count: int = 0

@dataclass
class QualityMetrics:
    """品質メトリクス"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    average_response_time: float = 0.0
    average_quality_score: float = 0.0
    error_rate: float = 0.0
    last_24h_requests: int = 0

class AIQualityManager:
    """AI品質管理システム"""
    
    def __init__(self, openai_api_key: str):
        """
        Initialize AI Quality Manager
        
        Args:
            openai_api_key: OpenAI API key
        """
        self.api_key = openai_api_key
        self.responses: Dict[str, AIResponse] = {}
        self.metrics = QualityMetrics()
        
        # 設定
        self.max_retries = 3
        self.retry_delays = [1, 2, 4]  # 指数バックオフ
        self.timeout_seconds = 30
        self.quality_threshold = 0.7
        
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
    
    def generate_request_id(self, prompt: str) -> str:
        """リクエストIDを生成"""
        timestamp = str(time.time())
        content = f"{prompt[:100]}_{timestamp}"
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    def make_request_with_quality_check(self, 
                                      messages: List[Dict[str, str]], 
                                      model: str = "gpt-4.1",
                                      temperature: float = 0.7,
                                      max_tokens: int = 128000) -> AIResponse:
        """
        品質チェック付きAIリクエスト実行
        
        Args:
            messages: 会話メッセージ
            model: 使用モデル
            temperature: 温度パラメータ
            max_tokens: 最大トークン数
            
        Returns:
            AIResponse: 応答結果
        """
        if not self.available:
            return self._create_error_response("", "", "AI機能が利用できません", ErrorType.API_ERROR)
        
        prompt = json.dumps(messages, ensure_ascii=False)
        request_id = self.generate_request_id(prompt)
        start_time = time.time()
        
        # リトライロジック
        for attempt in range(self.max_retries + 1):
            try:
                # リクエスト実行（ログ記録ラッパー使用）
                from core.v2.openai_config import create_chat_completion
                response = create_chat_completion(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=self.timeout_seconds
                )
                
                response_time = time.time() - start_time
                response_text = response.choices[0].message.content.strip()
                token_count = response.usage.total_tokens if hasattr(response, 'usage') else 0
                
                # 応答オブジェクト作成
                ai_response = AIResponse(
                    request_id=request_id,
                    prompt=prompt,
                    response=response_text,
                    model=model,
                    timestamp=datetime.now(),
                    response_time=response_time,
                    token_count=token_count,
                    retry_count=attempt
                )
                
                # 品質評価
                self._evaluate_response_quality(ai_response)
                
                # 成功時の処理
                self.responses[request_id] = ai_response
                self._update_metrics(success=True, response_time=response_time)
                
                logger.info(f"Successful AI request {request_id} in {response_time:.2f}s")
                return ai_response
                
            except openai.RateLimitError as e:
                error_type = ErrorType.RATE_LIMIT
                error_msg = "レート制限に達しました"
                logger.warning(f"Rate limit exceeded on attempt {attempt + 1}: {e}")
                
            except openai.APITimeoutError as e:
                error_type = ErrorType.TIMEOUT
                error_msg = "リクエストがタイムアウトしました"
                logger.warning(f"Timeout on attempt {attempt + 1}: {e}")
                
            except openai.APIConnectionError as e:
                error_type = ErrorType.NETWORK_ERROR
                error_msg = "ネットワークエラーが発生しました"
                logger.warning(f"Network error on attempt {attempt + 1}: {e}")
                
            except Exception as e:
                error_type = ErrorType.API_ERROR
                error_msg = f"API エラー: {str(e)}"
                logger.error(f"Unexpected error on attempt {attempt + 1}: {e}")
            
            # リトライ待機
            if attempt < self.max_retries:
                delay = self.retry_delays[min(attempt, len(self.retry_delays) - 1)]
                logger.info(f"Retrying in {delay} seconds...")
                time.sleep(delay)
        
        # 最終的に失敗
        response_time = time.time() - start_time
        self._update_metrics(success=False, response_time=response_time)
        
        error_response = self._create_error_response(request_id, prompt, error_msg, error_type)
        error_response.retry_count = self.max_retries
        
        self.responses[request_id] = error_response
        return error_response
    
    def _create_error_response(self, request_id: str, prompt: str, 
                             error_message: str, error_type: ErrorType) -> AIResponse:
        """エラー応答を作成"""
        return AIResponse(
            request_id=request_id or "error",
            prompt=prompt,
            response="",
            model="none",
            timestamp=datetime.now(),
            response_time=0.0,
            token_count=0,
            quality_level=ResponseQuality.ERROR,
            error_type=error_type,
            error_message=error_message
        )
    
    def _evaluate_response_quality(self, response: AIResponse) -> None:
        """応答品質を評価"""
        score = 1.0
        
        # 応答時間による評価
        if response.response_time > 10:
            score -= 0.2
        elif response.response_time > 5:
            score -= 0.1
        
        # 応答長による評価
        if len(response.response) < 10:
            score -= 0.3
        elif len(response.response) > 2000:
            score -= 0.1
        
        # リトライ回数による評価
        score -= response.retry_count * 0.1
        
        # JSON形式の応答検証（該当する場合）
        if self._appears_to_be_json_response(response.response):
            if not self._is_valid_json(response.response):
                score -= 0.4
        
        # スコアを0-1に正規化
        response.quality_score = max(0.0, min(1.0, score))
        
        # 品質レベル決定
        if response.quality_score >= 0.9:
            response.quality_level = ResponseQuality.EXCELLENT
        elif response.quality_score >= 0.8:
            response.quality_level = ResponseQuality.GOOD
        elif response.quality_score >= 0.6:
            response.quality_level = ResponseQuality.ACCEPTABLE
        else:
            response.quality_level = ResponseQuality.POOR
    
    def _appears_to_be_json_response(self, response: str) -> bool:
        """JSON応答かどうかを判定"""
        stripped = response.strip()
        return stripped.startswith('{') and stripped.endswith('}')
    
    def _is_valid_json(self, response: str) -> bool:
        """有効なJSONかどうかを確認"""
        try:
            json.loads(response)
            return True
        except json.JSONDecodeError:
            return False
    
    def _update_metrics(self, success: bool, response_time: float) -> None:
        """メトリクスを更新"""
        self.metrics.total_requests += 1
        
        if success:
            self.metrics.successful_requests += 1
        else:
            self.metrics.failed_requests += 1
        
        # 平均応答時間更新
        if self.metrics.total_requests == 1:
            self.metrics.average_response_time = response_time
        else:
            self.metrics.average_response_time = (
                (self.metrics.average_response_time * (self.metrics.total_requests - 1) + response_time) 
                / self.metrics.total_requests
            )
        
        # エラー率計算
        self.metrics.error_rate = self.metrics.failed_requests / self.metrics.total_requests
        
        # 24時間以内のリクエスト数更新
        cutoff_time = datetime.now() - timedelta(hours=24)
        recent_responses = [r for r in self.responses.values() if r.timestamp > cutoff_time]
        self.metrics.last_24h_requests = len(recent_responses)
        
        # 平均品質スコア更新
        quality_scores = [r.quality_score for r in recent_responses if r.quality_score is not None]
        if quality_scores:
            self.metrics.average_quality_score = sum(quality_scores) / len(quality_scores)
    
    def get_quality_report(self) -> Dict[str, Any]:
        """品質レポートを取得"""
        recent_responses = [
            r for r in self.responses.values() 
            if r.timestamp > datetime.now() - timedelta(hours=24)
        ]
        
        # エラー分析
        error_counts = {}
        for response in recent_responses:
            if response.error_type:
                error_type = response.error_type.value
                error_counts[error_type] = error_counts.get(error_type, 0) + 1
        
        # 品質分布
        quality_distribution = {}
        for response in recent_responses:
            if response.quality_level:
                level = response.quality_level.value
                quality_distribution[level] = quality_distribution.get(level, 0) + 1
        
        return {
            "metrics": asdict(self.metrics),
            "recent_errors": error_counts,
            "quality_distribution": quality_distribution,
            "total_stored_responses": len(self.responses),
            "report_generated_at": datetime.now().isoformat()
        }
    
    def get_recommendations(self) -> List[str]:
        """改善推奨事項を取得"""
        recommendations = []
        
        if self.metrics.error_rate > 0.1:
            recommendations.append("🔴 エラー率が高いです。ネットワーク接続を確認してください。")
        
        if self.metrics.average_response_time > 8:
            recommendations.append("🟡 応答時間が長くなっています。プロンプトの簡略化を検討してください。")
        
        if self.metrics.average_quality_score < 0.7:
            recommendations.append("🟡 応答品質が低下しています。プロンプトの改善が必要です。")
        
        if self.metrics.last_24h_requests > 1000:
            recommendations.append("⚠️ API使用量が多くなっています。コスト管理にご注意ください。")
        
        if not recommendations:
            recommendations.append("✅ システムは正常に動作しています。")
        
        return recommendations
    
    def cleanup_old_responses(self, days_threshold: int = 7):
        """古い応答データをクリーンアップ"""
        cutoff_date = datetime.now() - timedelta(days=days_threshold)
        
        to_remove = [
            req_id for req_id, response in self.responses.items()
            if response.timestamp < cutoff_date
        ]
        
        for req_id in to_remove:
            del self.responses[req_id]
        
        logger.info(f"Cleaned up {len(to_remove)} old responses")
        return len(to_remove)

def create_quality_manager(api_key: str) -> AIQualityManager:
    """AIQualityManagerのファクトリ関数"""
    return AIQualityManager(api_key)