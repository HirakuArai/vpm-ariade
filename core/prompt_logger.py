"""
Prompt Logger for Kai VPM

Context manager for logging LLM API calls with automatic capture of
request/response data and token counts.
"""

import uuid
import time
import json
import hashlib
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Callable, Generator
from pathlib import Path

from .log_schema import LogEntry, RequestKind, log_to_jsonl, get_log_filepath


class PromptLogger:
    """Manages logging of LLM API calls with AI Log Output Guidelines v1.0 compliance"""
    
    # Constants for AI Log Output Guidelines v1.0
    MAX_FILE_SIZE_MB = 5
    MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
    
    def __init__(self):
        """Initialize the prompt logger"""
        self._current_log_file: Optional[Path] = None
        self._dedup_index_file: Optional[Path] = None
        self._ensure_log_directory()
    
    def _ensure_log_directory(self):
        """Ensure the log directory exists"""
        log_dir = Path("logs/llm_calls")
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize metadata directory and deduplication index file
        metadata_dir = log_dir / "metadata"
        metadata_dir.mkdir(parents=True, exist_ok=True)
        
        self._dedup_index_file = metadata_dir / "dedup_index.json"
        if not self._dedup_index_file.exists():
            self._dedup_index_file.write_text("{}")
    
    def _get_current_log_file(self) -> Path:
        """Get the current log file path with 5MB rotation support"""
        now = datetime.utcnow()  # Use UTC for consistency
        
        # Check if we need a new log file (new day, first call, or size limit exceeded)
        if self._current_log_file is None or self._should_rotate_log_file(now):
            self._current_log_file = self._generate_log_file_path(now)
        
        return self._current_log_file
    
    def _should_rotate_log_file(self, now: datetime) -> bool:
        """Check if log file should be rotated based on date or size"""
        if self._current_log_file is None:
            return True
        
        # Check if file is from different day
        current_date = now.strftime("%Y%m%d")
        if current_date not in str(self._current_log_file):
            return True
        
        # Check file size (5MB limit)
        if self._current_log_file.exists() and self._current_log_file.stat().st_size >= self.MAX_FILE_SIZE_BYTES:
            return True
        
        return False
    
    def _generate_log_file_path(self, now: datetime) -> Path:
        """Generate log file path with YYYYMMDD_HH rotation"""
        log_dir = Path("logs/llm_calls")
        
        # Format: YYYYMMDD_HH for hourly rotation when size limit is reached
        timestamp = now.strftime("%Y%m%d_%H")
        base_path = log_dir / f"{timestamp}.jsonl"
        
        # If file already exists and is near size limit, increment hour
        counter = 0
        while base_path.exists() and base_path.stat().st_size >= self.MAX_FILE_SIZE_BYTES:
            counter += 1
            hour = (now.hour + counter) % 24
            if hour < now.hour:  # wrapped to next day
                next_day = now + timedelta(days=1)
                timestamp = next_day.strftime(f"%Y%m%d_{hour:02d}")
            else:
                timestamp = now.strftime(f"%Y%m%d_{hour:02d}")
            base_path = log_dir / f"{timestamp}.jsonl"
        
        return base_path
    
    def _is_duplicate_log(self, task_id: str, response_content: str) -> bool:
        """Check if log entry is duplicate using hash-based deduplication"""
        if not response_content or not task_id:
            return False
        
        # Generate hash key as specified in directive
        hash_key = hashlib.sha256(f"{task_id}{response_content}".encode()).hexdigest()
        
        try:
            # Load deduplication index
            if not self._dedup_index_file.exists():
                return False
            
            with open(self._dedup_index_file, 'r', encoding='utf-8') as f:
                index = json.load(f)
            
            # Check if hash exists and is within 24h window
            if hash_key in index:
                entry_time = datetime.fromisoformat(index[hash_key].rstrip('Z'))
                time_diff = datetime.utcnow() - entry_time
                if time_diff.total_seconds() < 86400:  # 24 hours
                    # Log deduplication skip
                    self._log_dedup_skip(hash_key)
                    return True
            
            # Update index with current timestamp
            index[hash_key] = datetime.utcnow().isoformat(timespec="milliseconds") + "Z"
            
            # Clean old entries (older than 24h)
            cutoff_time = datetime.utcnow() - timedelta(hours=24)
            index = {
                k: v for k, v in index.items()
                if datetime.fromisoformat(v.rstrip('Z')) > cutoff_time
            }
            
            # Save updated index
            with open(self._dedup_index_file, 'w', encoding='utf-8') as f:
                json.dump(index, f, ensure_ascii=False, separators=(',', ':'))
            
            return False
            
        except Exception as e:
            print(f"⚠️ Deduplication check failed: {e}", flush=True)
            return False
    
    def _log_dedup_skip(self, hash_key: str):
        """Log deduplication skip to separate file"""
        try:
            # Store metadata in separate subdirectory
            metadata_dir = Path("logs/llm_calls/metadata")
            metadata_dir.mkdir(parents=True, exist_ok=True)
            dedup_log_file = metadata_dir / "dedup_skipped.jsonl"
            
            skip_entry = {
                "ts": datetime.utcnow().isoformat(timespec="milliseconds") + "Z",
                "dedup_skipped": True,
                "hash_key": hash_key
            }
            
            with open(dedup_log_file, 'a', encoding='utf-8') as f:
                json.dump(skip_entry, f, ensure_ascii=False, separators=(',', ':'))
                f.write('\n')
                
        except Exception as e:
            print(f"⚠️ Failed to log dedup skip: {e}", flush=True)
    
    def _validate_token_metrics(self, prompt_tokens: int, completion_tokens: int, task_id: str) -> bool:
        """Validate token metrics and detect anomalies"""
        anomaly_detected = False
        
        # Check for zero tokens
        if prompt_tokens == 0 or completion_tokens == 0:
            print(f"⚠️ Token metrics anomaly detected for task {task_id}: prompt_tokens={prompt_tokens}, completion_tokens={completion_tokens}", flush=True)
            anomaly_detected = True
        
        # TODO: Add check for identical tokens from previous calls
        # This would require storing recent token counts, but for now we focus on zero detection
        
        if anomaly_detected:
            self._log_metrics_anomaly(task_id, prompt_tokens, completion_tokens)
        
        return not anomaly_detected
    
    def _log_metrics_anomaly(self, task_id: str, prompt_tokens: int, completion_tokens: int):
        """Log token metrics anomaly"""
        try:
            # Store metadata in separate subdirectory  
            metadata_dir = Path("logs/llm_calls/metadata")
            metadata_dir.mkdir(parents=True, exist_ok=True)
            anomaly_log_file = metadata_dir / "metrics_anomalies.jsonl"
            
            anomaly_entry = {
                "ts": datetime.utcnow().isoformat(timespec="milliseconds") + "Z",
                "metrics_anomaly": True,
                "task_id": task_id,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens
            }
            
            with open(anomaly_log_file, 'a', encoding='utf-8') as f:
                json.dump(anomaly_entry, f, ensure_ascii=False, separators=(',', ':'))
                f.write('\n')
                
        except Exception as e:
            print(f"⚠️ Failed to log metrics anomaly: {e}", flush=True)
    
    def _validate_and_fallback_kind(self, kind: RequestKind) -> str:
        """Validate kind enum and fallback to 'unknown' if invalid"""
        try:
            # Check if kind is a valid RequestKind
            if isinstance(kind, RequestKind):
                return kind.value
            elif isinstance(kind, str) and kind in [k.value for k in RequestKind]:
                return kind
            else:
                print(f"⚠️ Unknown request kind: {kind}, falling back to 'unknown'", flush=True)
                return "unknown"
        except Exception as e:
            print(f"⚠️ Kind validation failed: {e}, falling back to 'unknown'", flush=True)
            return "unknown"
    
    @contextmanager
    def log_call(
        self, 
        agent: str, 
        kind: RequestKind,
        model: str = "gpt-4.1",
        task_id: Optional[str] = None,
        subkind: Optional['RequestContext'] = None
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Context manager for logging LLM calls.
        
        Args:
            agent: The calling agent ('kai' or 'claude')
            kind: Type of request (RequestKind enum)
            model: Model being used (default: gpt-4.1)
            task_id: Optional task ID (auto-generated if not provided)
            
        Yields:
            Dict containing 'log_request' and 'log_response' functions
            
        Example:
            with logger.log_call("kai", RequestKind.UI_CHAT) as log:
                log['log_request'](request_data)
                response = llm_client.complete(request_data)
                log['log_response'](response, prompt_tokens, completion_tokens)
                return response
        """
        if task_id is None:
            task_id = str(uuid.uuid4())
        
        # AI Log Output Guidelines v1.0 compliance: ISO-8601 with UTC timezone
        timestamp = datetime.utcnow().isoformat(timespec="milliseconds") + "Z"
        request_data = None
        response_data = None
        prompt_tokens = 0
        completion_tokens = 0
        error = None
        
        # Storage for captured data
        context = {
            'request': None,
            'response': None,
            'prompt_tokens': 0,
            'completion_tokens': 0,
            'error': None
        }
        
        def log_request(request: Dict[str, Any]):
            """Capture request data"""
            context['request'] = request
        
        def log_response(
            response: Optional[Dict[str, Any]], 
            prompt_tokens: int, 
            completion_tokens: int
        ):
            """Capture response data and token counts"""
            context['response'] = response
            context['prompt_tokens'] = prompt_tokens
            context['completion_tokens'] = completion_tokens
        
        def log_error(error_type: str):
            """Capture error information"""
            context['error'] = error_type
        
        # Provide logging functions to the caller
        log_context = {
            'log_request': log_request,
            'log_response': log_response,
            'log_error': log_error,
            'task_id': task_id
        }
        
        try:
            yield log_context
        except Exception as e:
            # Capture any unhandled exceptions as errors
            if context['error'] is None:
                context['error'] = f"unhandled_exception: {type(e).__name__}"
            raise
        finally:
            # Create and save log entry with AI Log Output Guidelines v1.0 compliance
            if context['request'] is not None:  # Only log if request was captured
                
                # Validate kind and fallback to 'unknown' if needed
                validated_kind = self._validate_and_fallback_kind(kind)
                
                # Validate token metrics
                self._validate_token_metrics(
                    context['prompt_tokens'], 
                    context['completion_tokens'], 
                    task_id
                )
                
                # Extract response content for deduplication check
                response_content = ""
                if context['response'] and 'choices' in context['response']:
                    try:
                        response_content = context['response']['choices'][0]['message']['content']
                    except (KeyError, IndexError):
                        response_content = json.dumps(context['response'], ensure_ascii=False)
                
                # Check for duplicates
                if self._is_duplicate_log(task_id, response_content):
                    print(f"⚠️ Duplicate log skipped for task {task_id}", flush=True)
                    return
                
                # Create entry with validated kind
                entry = LogEntry(
                    ts=timestamp,
                    agent=agent,
                    model=model,
                    kind=validated_kind,  # Use validated kind string
                    subkind=subkind,  # Add context classification
                    task_id=task_id,
                    prompt_tokens=context['prompt_tokens'],
                    completion_tokens=context['completion_tokens'],
                    error=context['error'],
                    request=context['request'],
                    response=context['response']
                )
                
                log_file = self._get_current_log_file()
                log_to_jsonl(entry, log_file)
                print(f"✅ LLMログを書き込みました: {log_file} (task_id: {task_id})", flush=True)
                
                # LLMログをGitに自動コミット（環境変数でDisable可能）
                import os
                if not os.environ.get("DISABLE_GIT_COMMITS"):
                    try:
                        from core.git_ops import commit_and_push_llm_logs
                        commit_and_push_llm_logs()
                        print(f"✅ LLMログをGitHubにプッシュしました", flush=True)
                    except Exception as e:
                        # ログの保存自体は成功しているので、Gitエラーは警告として処理
                        print(f"⚠️ LLMログのGitコミット失敗: {e}", flush=True)
                else:
                    print(f"ℹ️ DISABLE_GIT_COMMITS=1 のため、Gitコミットをスキップしました（ログは保存済み）", flush=True)


# Global logger instance
_prompt_logger = PromptLogger()


@contextmanager
def log_call(
    agent: str, 
    kind: RequestKind,
    model: str = "gpt-4.1",
    task_id: Optional[str] = None
) -> Generator[Dict[str, Any], None, None]:
    """
    Convenience function for logging LLM calls.
    
    This is a module-level wrapper around the PromptLogger.log_call method.
    
    Args:
        agent: The calling agent ('kai' or 'claude')
        kind: Type of request (RequestKind enum)
        model: Model being used (default: gpt-4.1)
        task_id: Optional task ID (auto-generated if not provided)
        
    Yields:
        Dict containing logging functions
        
    Example:
        from core.prompt_logger import log_call, RequestKind
        
        with log_call("kai", RequestKind.UI_CHAT) as log:
            request = {"messages": [...]}
            log['log_request'](request)
            
            # Make actual LLM call
            response = openai_client.chat.completions.create(**request)
            
            # Log response
            log['log_response'](
                response.model_dump(),
                response.usage.prompt_tokens,
                response.usage.completion_tokens
            )
    """
    with _prompt_logger.log_call(agent, kind, model, task_id) as log_context:
        yield log_context