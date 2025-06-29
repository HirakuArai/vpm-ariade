"""
Prompt Logger for Kai VPM

Context manager for logging LLM API calls with automatic capture of
request/response data and token counts.
"""

import uuid
import time
from contextlib import contextmanager
from datetime import datetime
from typing import Optional, Dict, Any, Callable, Generator
from pathlib import Path

from .log_schema import LogEntry, RequestKind, log_to_jsonl, get_log_filepath


class PromptLogger:
    """Manages logging of LLM API calls"""
    
    def __init__(self):
        """Initialize the prompt logger"""
        self._current_log_file: Optional[Path] = None
        self._ensure_log_directory()
    
    def _ensure_log_directory(self):
        """Ensure the log directory exists"""
        log_dir = Path("logs/llm_calls")
        log_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_current_log_file(self) -> Path:
        """Get the current log file path, creating new one each day"""
        now = datetime.now()
        current_date = now.strftime("%Y%m%d")
        
        # Check if we need a new log file (new day or first call)
        if self._current_log_file is None or current_date not in str(self._current_log_file):
            self._current_log_file = get_log_filepath(now)
        
        return self._current_log_file
    
    @contextmanager
    def log_call(
        self, 
        agent: str, 
        kind: RequestKind,
        model: str = "gpt-4.1",
        task_id: Optional[str] = None
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
        
        timestamp = datetime.now().isoformat()
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
            # Create and save log entry
            if context['request'] is not None:  # Only log if request was captured
                entry = LogEntry(
                    ts=timestamp,
                    agent=agent,
                    model=model,
                    kind=kind,
                    task_id=task_id,
                    prompt_tokens=context['prompt_tokens'],
                    completion_tokens=context['completion_tokens'],
                    error=context['error'],
                    request=context['request'],
                    response=context['response']
                )
                
                log_file = self._get_current_log_file()
                log_to_jsonl(entry, log_file)


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