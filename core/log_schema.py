"""
Log Schema for Kai VPM LLM Call Logging

This module defines the data models and utilities for logging LLM API calls
across the Kai VPM system.
"""

from enum import Enum
from typing import Optional, Dict, Any, Union
from datetime import datetime, timezone
from pydantic import BaseModel, Field
import json
from pathlib import Path


class RequestKind(str, Enum):
    """Types of LLM requests in the system"""
    SPEC_SCAN = "spec_scan"
    TICKET_GEN = "ticket_gen"
    REVIEW_GEN = "review_gen"
    UI_CHAT = "ui_chat"
    PROJECT_DETAIL = "project_detail"  # AI-generated project summaries and descriptions
    INTENT_DETECT = "intent_detect"    # User intent detection
    CONVERSATION_ANALYSIS = "conversation_analysis"  # Conversation summary and analysis
    MEMORY_UPDATE = "memory_update"  # Memory update LLM calls (N+1 patch generation)
    UNKNOWN = "unknown"  # Fallback for unregistered kinds


class RequestContext(str, Enum):
    """Context/subkind for more granular request classification"""
    HOME_CHAT = "home_chat"        # Chat from home page (no project selected)
    PROJECT_CHAT = "project_chat"  # Chat from within a specific project
    GENERAL = "general"            # General context
    N_PLUS_1_PATCH = "n_plus_1_patch"  # Memory update N+1 patch generation

class LogEntry(BaseModel):
    """Schema for LLM call log entries"""
    ts: str = Field(..., description="ISO-8601 timestamp of the call")
    agent: str = Field(..., pattern="^(kai|claude)$", description="Calling agent")
    model: str = Field(..., description="Model used (e.g., gpt-4.1)")
    kind: RequestKind = Field(..., description="Type of request")
    subkind: Optional[RequestContext] = Field(None, description="Request context for granular analysis")
    task_id: str = Field(..., description="Internal UUID assigned by Kai")
    prompt_tokens: int = Field(..., ge=0, description="Number of tokens sent")
    completion_tokens: int = Field(..., ge=0, description="Number of tokens received")
    error: Optional[str] = Field(None, description="Error type if failed")
    request: Dict[str, Any] = Field(..., description="Full request including system/user/functions")
    response: Optional[Dict[str, Any]] = Field(None, description="Full response (null during request)")
    
    model_config = {
        "use_enum_values": True,
        "json_encoders": {
            datetime: lambda v: v.isoformat()
        }
    }


def log_to_jsonl(entry: LogEntry, filepath: Union[str, Path]) -> None:
    """
    Append a LogEntry to a JSONL file.
    
    Args:
        entry: LogEntry instance to append
        filepath: Path to the JSONL file
    """
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        with open(filepath, 'a+', encoding='utf-8') as f:
            # Write with AI Log Output Guidelines v1.0 compliance
            # - Use ensure_ascii=False for UTF-8 support
            # - Use separators for compact output
            # - Handle None/True/False -> null/true/false conversion automatically via Pydantic
            json_str = entry.model_dump_json(by_alias=True, exclude_none=False)
            f.write(json_str + '\n')
            f.flush()
            # ファイルサイズを確認してデバッグ情報を出力
            file_size = filepath.stat().st_size
            print(f"✅ JSONLエントリを書き込みました: {filepath.name} (サイズ: {file_size:,} bytes)", flush=True)
    except Exception as e:
        print(f"❌ JSONLファイルへの書き込みエラー: {e}", flush=True)
        raise


def from_jsonl(filepath: Union[str, Path]) -> list[LogEntry]:
    """
    Read LogEntry objects from a JSONL file.
    
    Args:
        filepath: Path to the JSONL file
        
    Returns:
        List of LogEntry instances
    """
    filepath = Path(filepath)
    entries = []
    
    if not filepath.exists():
        return entries
    
    with open(filepath, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                entries.append(LogEntry(**data))
            except (json.JSONDecodeError, ValueError) as e:
                # Log parsing errors but continue processing
                print(f"Warning: Failed to parse line {line_num} in {filepath}: {e}")
                continue
    
    return entries


def get_log_filepath(timestamp: Optional[datetime] = None) -> Path:
    """
    Generate the log filepath for a given timestamp.
    
    Args:
        timestamp: Datetime to use for filename (defaults to now)
        
    Returns:
        Path object for the log file
    """
    if timestamp is None:
        timestamp = datetime.now(timezone.utc)
    
    filename = timestamp.strftime("%Y%m%d-%H%M%S.jsonl")
    return Path("logs/llm") / filename