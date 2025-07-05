"""
LLM Call Logger for Memory Layer Phase 2
OpenAI API呼び出しログ機能
"""

import json
import time
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional
import functools

logger = logging.getLogger(__name__)

# ログディレクトリ
LLM_LOGS_DIR = Path("logs/llm_calls")
LLM_LOGS_DIR.mkdir(parents=True, exist_ok=True)


def get_daily_log_file() -> Path:
    """今日のLLMログファイルパスを取得"""
    today = datetime.now().strftime("%Y-%m-%d")
    return LLM_LOGS_DIR / f"{today}.jsonl"


def log_llm_call(
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    latency_ms: float,
    request_data: Optional[Dict] = None,
    response_data: Optional[Dict] = None
) -> None:
    """
    LLM呼び出しをログに記録
    
    Args:
        model: 使用したモデル名
        prompt_tokens: プロンプトトークン数
        completion_tokens: 生成トークン数  
        latency_ms: レスポンス時間（ミリ秒）
        request_data: リクエストデータ（オプション）
        response_data: レスポンスデータ（オプション）
    """
    try:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "model": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "latency_ms": round(latency_ms, 2),
            "cost_estimate_usd": estimate_cost(model, prompt_tokens, completion_tokens)
        }
        
        # オプショナルデータを追加
        if request_data:
            log_entry["request"] = request_data
        if response_data:
            log_entry["response"] = response_data
        
        # ファイルに追記
        log_file = get_daily_log_file()
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
            
        logger.debug(f"LLM call logged: {model} ({log_entry['total_tokens']} tokens, {latency_ms:.2f}ms)")
        
    except Exception as e:
        logger.error(f"Failed to log LLM call: {e}")


def estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """
    API使用料金の概算計算
    
    Args:
        model: モデル名
        prompt_tokens: プロンプトトークン数
        completion_tokens: 生成トークン数
        
    Returns:
        float: 概算コスト（USD）
    """
    # 2025年7月時点の概算料金（実際の料金は変動する可能性があります）
    pricing = {
        "gpt-4": {"prompt": 0.03, "completion": 0.06},  # per 1K tokens
        "gpt-4-turbo": {"prompt": 0.01, "completion": 0.03},
        "gpt-4o": {"prompt": 0.005, "completion": 0.015},
        "gpt-3.5-turbo": {"prompt": 0.001, "completion": 0.002}
    }
    
    # モデル名の正規化
    model_key = model.lower()
    if "gpt-4o" in model_key:
        rates = pricing["gpt-4o"]
    elif "gpt-4-turbo" in model_key or "gpt-4.1" in model_key:
        rates = pricing["gpt-4-turbo"]
    elif "gpt-4" in model_key:
        rates = pricing["gpt-4"]
    elif "gpt-3.5" in model_key:
        rates = pricing["gpt-3.5-turbo"]
    else:
        # 不明なモデルはGPT-4として計算
        rates = pricing["gpt-4"]
    
    prompt_cost = (prompt_tokens / 1000) * rates["prompt"]
    completion_cost = (completion_tokens / 1000) * rates["completion"]
    
    return round(prompt_cost + completion_cost, 6)


def count_today_calls() -> int:
    """今日のLLM呼び出し回数をカウント"""
    try:
        log_file = get_daily_log_file()
        if not log_file.exists():
            return 0
        
        with open(log_file, "r", encoding="utf-8") as f:
            return sum(1 for line in f if line.strip())
            
    except Exception as e:
        logger.error(f"Failed to count LLM calls: {e}")
        return 0


def get_today_stats() -> Dict[str, Any]:
    """今日のLLM使用統計を取得"""
    try:
        log_file = get_daily_log_file()
        if not log_file.exists():
            return {"calls": 0, "total_tokens": 0, "total_cost": 0.0, "avg_latency": 0.0}
        
        calls = 0
        total_tokens = 0
        total_cost = 0.0
        total_latency = 0.0
        
        with open(log_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        entry = json.loads(line.strip())
                        calls += 1
                        total_tokens += entry.get("total_tokens", 0)
                        total_cost += entry.get("cost_estimate_usd", 0.0)
                        total_latency += entry.get("latency_ms", 0.0)
                    except json.JSONDecodeError:
                        continue
        
        return {
            "calls": calls,
            "total_tokens": total_tokens,
            "total_cost": round(total_cost, 4),
            "avg_latency": round(total_latency / calls if calls > 0 else 0.0, 2)
        }
        
    except Exception as e:
        logger.error(f"Failed to get LLM stats: {e}")
        return {"calls": 0, "total_tokens": 0, "total_cost": 0.0, "avg_latency": 0.0}


def create_chat_completion_wrapper(original_func):
    """
    OpenAI create_chat_completion関数をラップしてログ記録
    
    Args:
        original_func: 元のcreate_chat_completion関数
        
    Returns:
        ラップされた関数
    """
    @functools.wraps(original_func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        
        try:
            # API呼び出し実行
            response = original_func(*args, **kwargs)
            
            # レスポンス時間計算
            end_time = time.time()
            latency_ms = (end_time - start_time) * 1000
            
            # ログ記録
            if hasattr(response, 'usage') and hasattr(response, 'model'):
                usage = response.usage
                model = response.model
                
                log_llm_call(
                    model=model,
                    prompt_tokens=usage.prompt_tokens,
                    completion_tokens=usage.completion_tokens,
                    latency_ms=latency_ms,
                    request_data={
                        "model": kwargs.get("model", "unknown"),
                        "max_tokens": kwargs.get("max_tokens"),
                        "temperature": kwargs.get("temperature")
                    }
                )
            
            return response
            
        except Exception as e:
            # エラーもログに記録
            end_time = time.time()
            latency_ms = (end_time - start_time) * 1000
            
            logger.error(f"LLM call failed: {e}")
            
            # エラーログ
            error_entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "model": kwargs.get("model", "unknown"),
                "error": str(e),
                "latency_ms": round(latency_ms, 2)
            }
            
            log_file = get_daily_log_file()
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(error_entry, ensure_ascii=False) + "\n")
            
            # 元の例外を再発生
            raise
    
    return wrapper


# Memory Chat β用の統計表示関数
def render_llm_stats_for_memory_chat():
    """Memory Chat β用のLLM統計表示"""
    try:
        stats = get_today_stats()
        
        return {
            "calls_today": stats["calls"],
            "total_tokens": stats["total_tokens"],
            "estimated_cost": f"${stats['total_cost']:.4f}",
            "avg_latency": f"{stats['avg_latency']:.1f}ms"
        }
        
    except Exception as e:
        logger.error(f"Failed to render LLM stats: {e}")
        return {
            "calls_today": 0,
            "total_tokens": 0,
            "estimated_cost": "$0.0000",
            "avg_latency": "0.0ms"
        }


if __name__ == "__main__":
    # テスト実行
    print("Testing LLM logger functionality...")
    
    # テストログエントリ
    log_llm_call(
        model="gpt-4-turbo",
        prompt_tokens=100,
        completion_tokens=50,
        latency_ms=1500.5
    )
    
    # 統計確認
    stats = get_today_stats()
    print(f"Today's stats: {stats}")
    
    count = count_today_calls()
    print(f"Today's call count: {count}")