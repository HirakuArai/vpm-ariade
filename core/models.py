# --- core/models.py ---
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4
from typing import List, Dict, Any
from enum import Enum

SCHEMA_VERSION = "1.0"
DEFAULT_UNDEF = "__UNDEFINED__"

class ProjectPhase(Enum):
    """プロジェクトフェーズの定義"""
    INCEPTION = "INCEPTION"           # 構想段階
    DEFINITION = "DEFINITION"         # 定義段階  
    PLANNING = "PLANNING"             # 計画段階
    EXECUTION = "EXECUTION"           # 実行段階
    MONITORING = "MONITORING"         # 監視・制御段階
    CLOSURE = "CLOSURE"               # 完了段階

class ProjectStatus(Enum):
    """プロジェクトステータスの定義"""
    DRAFT = "DRAFT"                   # 下書き
    ACTIVE = "ACTIVE"                 # アクティブ
    ON_HOLD = "ON_HOLD"              # 保留
    COMPLETED = "COMPLETED"           # 完了
    CANCELLED = "CANCELLED"           # キャンセル
    ARCHIVED = "ARCHIVED"             # アーカイブ済み

@dataclass
class Project:
    identifier: str
    overview: str
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    created_by: str = DEFAULT_UNDEF
    status: str = "DRAFT"
    schema_version: str = SCHEMA_VERSION
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    change_log: list = field(default_factory=list)
    uuid: str = field(default_factory=lambda: str(uuid4()))
    tasks: List[Dict[str, Any]] = field(default_factory=list)
    
    # ライフサイクル管理用フィールド
    phase: str = ProjectPhase.INCEPTION.value
    completion_percentage: float = 0.0
    next_actions: List[Dict[str, Any]] = field(default_factory=list)
    blocking_issues: List[Dict[str, Any]] = field(default_factory=list)
    phase_requirements: Dict[str, Any] = field(default_factory=dict)
    phase_history: List[Dict[str, Any]] = field(default_factory=list)
    change_log: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict:
        result = {}
        for k, v in self.__dict__.items():
            # Special handling for list fields - don't convert empty list to UNDEFINED
            if k in ["tasks", "change_log", "next_actions", "blocking_issues", "phase_history"]:
                result[k] = v if isinstance(v, list) else []
            elif v:
                result[k] = v
            else:
                result[k] = DEFAULT_UNDEF
        return result