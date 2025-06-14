# --- core/models.py ---
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4
from typing import List, Dict, Any

SCHEMA_VERSION = "1.0"
DEFAULT_UNDEF = "__UNDEFINED__"

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

    def to_dict(self) -> dict:
        result = {}
        for k, v in self.__dict__.items():
            # Special handling for tasks - don't convert empty list to UNDEFINED
            if k == "tasks":
                result[k] = v if isinstance(v, list) else []
            elif v:
                result[k] = v
            else:
                result[k] = DEFAULT_UNDEF
        return result