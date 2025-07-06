"""
LLM Call Logger for Memory Layer Phase 2
OpenAI API呼び出しログ機能
"""

import json
import time
import logging
import gzip
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, List
import functools

logger = logging.getLogger(__name__)

# ログディレクトリ（仕様書準拠）
LLM_LOGS_DIR = Path("logs/llm")
LLM_LOGS_DIR.mkdir(parents=True, exist_ok=True)

# ファイルサイズ制限（1MB）
MAX_FILE_SIZE = 1024 * 1024  # 1MB


def get_daily_log_file() -> Path:
    """今日のLLMログファイルパスを取得（仕様書準拠）"""
    today = datetime.now().strftime("%Y-%m-%d")
    return LLM_LOGS_DIR / f"{today}.jsonl"


def rotate_log_if_needed(log_file: Path) -> Path:
    """
    ログファイルが1MB超の場合、gzipローテーションを実行
    
    Args:
        log_file: 対象のログファイルパス
        
    Returns:
        Path: 使用すべきログファイルパス
    """
    try:
        if log_file.exists() and log_file.stat().st_size > MAX_FILE_SIZE:
            # ローテーション実行
            timestamp = datetime.now().strftime("%H%M%S")
            rotated_name = f"{log_file.stem}_{timestamp}.jsonl.gz"
            rotated_path = log_file.parent / rotated_name
            
            # gzip圧縮
            with open(log_file, 'rb') as f_in:
                with gzip.open(rotated_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            # 元ファイルを削除
            log_file.unlink()
            
            logger.info(f"Log file rotated: {log_file} -> {rotated_path}")
            
            # 新しいファイルを作成
            log_file.touch()
            
        return log_file
        
    except Exception as e:
        logger.error(f"Log rotation failed: {e}")
        return log_file


def log_llm_call(
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    latency_ms: float,
    messages: Optional[List[Dict]] = None,
    response: Optional[str] = None,
    request_data: Optional[Dict] = None,
    response_data: Optional[Dict] = None,
    agent: str = "kai",
    kind: str = "ui_chat",
    subkind: Optional[str] = "general",
    task_id: Optional[str] = None
) -> None:
    """
    LLM呼び出しをログに記録（Streamlit Cloud対応強化版）
    
    Args:
        model: 使用したモデル名
        prompt_tokens: プロンプトトークン数
        completion_tokens: 生成トークン数  
        latency_ms: レスポンス時間（ミリ秒）
        messages: プロンプト全文（messagesパラメータ）
        response: 返答全文（response.choices[0].message.content）
        request_data: リクエストデータ（下位互換用）
        response_data: レスポンスデータ（下位互換用）
        agent: エージェント名（デフォルト: kai）
        kind: ログ種別（デフォルト: ui_chat）
        subkind: サブ種別（デフォルト: general）
        task_id: タスクID（オプション）
    """
    # Streamlit環境での詳細デバッグ
    try:
        import streamlit as st
        is_streamlit = True
    except:
        is_streamlit = False
    
    if is_streamlit:
        try:
            st.write(f"🔍 LLM Logger Debug: {kind} - {model}")
        except:
            pass
    
    try:
        # 既存ログ形式との互換性を保った構造
        log_entry = {
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
            "agent": agent,
            "model": model,
            "kind": kind,
            "subkind": subkind,
            "task_id": task_id or f"memory-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "error": None,
            "request": {
                **(request_data or {}),
                # 仕様書準拠: プロンプト全文をrequestに格納
                "messages": messages or [],
                "latency_ms": round(latency_ms, 2)
            },
            "response": {
                # 仕様書準拠: 返答全文をresponse辞書に格納（既存スキーマ準拠）
                "content": response or "",
                "choices": [{"message": {"content": response or ""}}] if response else []
            }
        }
        
        if is_streamlit:
            try:
                st.write(f"  - ログエントリ作成完了: {len(json.dumps(log_entry))} bytes")
            except:
                pass
        
        # ディレクトリ作成の確実な実行
        try:
            LLM_LOGS_DIR.mkdir(parents=True, exist_ok=True)
            if is_streamlit:
                try:
                    st.write(f"  - ディレクトリ確認: {LLM_LOGS_DIR} (存在: {LLM_LOGS_DIR.exists()})")
                except:
                    pass
        except Exception as dir_error:
            if is_streamlit:
                try:
                    st.error(f"❌ ディレクトリ作成失敗: {dir_error}")
                except:
                    pass
            logger.error(f"Failed to create log directory: {dir_error}")
            return
        
        # ファイル書き込み（ローテーション対応）
        log_file = get_daily_log_file()
        log_file = rotate_log_if_needed(log_file)
        
        if is_streamlit:
            try:
                st.write(f"  - ログファイル: {log_file}")
                st.write(f"  - ファイル存在: {log_file.exists()}")
            except:
                pass
        
        # ファイル書き込み試行
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
                f.flush()  # 強制フラッシュ
            
            # 書き込み確認
            if log_file.exists():
                file_size = log_file.stat().st_size
                if is_streamlit:
                    try:
                        st.write(f"  ✅ ログ書き込み成功: {file_size} bytes")
                    except:
                        pass
                logger.debug(f"LLM call logged: {model} ({prompt_tokens + completion_tokens} tokens, {latency_ms:.2f}ms)")
            else:
                if is_streamlit:
                    try:
                        st.error("❌ ファイル書き込み後にファイルが存在しない")
                    except:
                        pass
                logger.error("Log file does not exist after write")
                
        except Exception as write_error:
            if is_streamlit:
                try:
                    st.error(f"❌ ファイル書き込みエラー: {write_error}")
                except:
                    pass
            logger.error(f"Failed to write log file: {write_error}")
            raise
        
    except Exception as e:
        if is_streamlit:
            try:
                st.error(f"❌ LLMログ記録に失敗: {e}")
            except:
                pass
        logger.error(f"Failed to log LLM call: {e}")
        
        # 緊急フォールバック: st.session_stateに保存
        if is_streamlit:
            try:
                if 'llm_call_logs' not in st.session_state:
                    st.session_state['llm_call_logs'] = []
                st.session_state['llm_call_logs'].append({
                    'timestamp': datetime.now().isoformat(),
                    'model': model,
                    'kind': kind,
                    'tokens': f"{prompt_tokens}/{completion_tokens}",
                    'error': str(e)
                })
                st.warning(f"⚠️ ファイル保存失敗、セッション状態に保存: {len(st.session_state['llm_call_logs'])}件")
            except:
                pass  # フォールバック処理でもエラーの場合は無視


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
                        
                        # 新旧両形式から統計を計算
                        prompt_tokens = entry.get("prompt_tokens", 0)
                        completion_tokens = entry.get("completion_tokens", 0)
                        total_tokens += prompt_tokens + completion_tokens
                        
                        # コスト推定（モデル情報から）
                        model = entry.get("model", "gpt-4.1")
                        cost = estimate_cost(model, prompt_tokens, completion_tokens)
                        total_cost += cost
                        
                        # レスポンス時間（新形式ではrequest.latency_ms、旧形式では直接）
                        request_data = entry.get("request", {})
                        latency = request_data.get("latency_ms", entry.get("latency_ms", 0.0))
                        total_latency += latency
                        
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


def get_recent_llm_calls(limit: int = 10) -> List[Dict[str, Any]]:
    """
    最新のLLM呼び出しログを取得（仕様書準拠）
    
    Args:
        limit: 取得する件数（デフォルト: 10）
        
    Returns:
        List[Dict]: 最新のLLM呼び出しログリスト
    """
    try:
        log_file = get_daily_log_file()
        if not log_file.exists():
            return []
        
        recent_calls = []
        
        with open(log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        # 最新のN件を取得（逆順で読み込み）
        for line in reversed(lines[-limit:]):
            if line.strip():
                try:
                    entry = json.loads(line.strip())
                    # UIで表示するために整形（新旧両形式対応）
                    request_data = entry.get("request", {})
                    response_data = entry.get("response", {})
                    
                    # 新形式ではrequest.messagesとresponse.contentを使用
                    # 旧形式では直接フィールドから取得（下位互換性）
                    formatted_entry = {
                        "timestamp": entry.get("ts", ""),
                        "model": entry.get("model", ""),
                        "prompt_tokens": entry.get("prompt_tokens", 0),
                        "completion_tokens": entry.get("completion_tokens", 0),
                        "latency_ms": request_data.get("latency_ms", entry.get("latency_ms", 0)),
                        "messages": request_data.get("messages", entry.get("messages", [])),
                        "response": response_data.get("content", entry.get("response", "")),
                        "task_id": entry.get("task_id", "")
                    }
                    recent_calls.append(formatted_entry)
                except json.JSONDecodeError:
                    continue
        
        return recent_calls
        
    except Exception as e:
        logger.error(f"Failed to get recent LLM calls: {e}")
        return []


def format_messages_for_display(messages: List[Dict]) -> str:
    """
    メッセージリストを表示用に整形
    
    Args:
        messages: OpenAI API messagesパラメータ
        
    Returns:
        str: 表示用に整形されたメッセージ
    """
    try:
        if not messages:
            return "No messages"
        
        formatted = []
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            
            # 長すぎる場合は短縮
            if len(content) > 200:
                content = content[:200] + "..."
            
            formatted.append(f"**{role.title()}**: {content}")
        
        return "\n\n".join(formatted)
        
    except Exception as e:
        logger.error(f"Failed to format messages: {e}")
        return "Format error"


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