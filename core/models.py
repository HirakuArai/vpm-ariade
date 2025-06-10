from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4

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

    def to_dict(self) -> dict:
        return {k: (v if v else DEFAULT_UNDEF) for k, v in self.__dict__.items()}