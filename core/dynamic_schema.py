# --- core/dynamic_schema.py ---
"""
Dynamic Project Schema Management
動的プロジェクト情報スキーマの管理
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class FieldPriority(Enum):
    """フィールドの優先度"""
    REQUIRED = "required"
    RECOMMENDED = "recommended" 
    OPTIONAL = "optional"
    DISABLED = "disabled"

class FieldStatus(Enum):
    """フィールドの状態"""
    UNDEFINED = "undefined"
    PARTIAL = "partial"
    DEFINED = "defined"
    CONFIRMED = "confirmed"

@dataclass
class DynamicField:
    """動的情報フィールド"""
    name: str
    value: Any = None
    priority: FieldPriority = FieldPriority.RECOMMENDED
    status: FieldStatus = FieldStatus.UNDEFINED
    confidence: float = 0.0
    source: Optional[str] = None
    last_updated: Optional[str] = None
    questions: List[str] = None
    ask_after: Optional[str] = None
    
    def __post_init__(self):
        if self.questions is None:
            self.questions = []
    
    def to_dict(self) -> Dict:
        """辞書形式に変換"""
        return {
            "value": self.value,
            "priority": self.priority.value,
            "status": self.status.value,
            "confidence": self.confidence,
            "source": self.source,
            "last_updated": self.last_updated,
            "questions": self.questions,
            "ask_after": self.ask_after
        }
    
    @classmethod
    def from_dict(cls, name: str, data: Dict) -> 'DynamicField':
        """辞書から復元"""
        return cls(
            name=name,
            value=data.get("value"),
            priority=FieldPriority(data.get("priority", "recommended")),
            status=FieldStatus(data.get("status", "undefined")),
            confidence=data.get("confidence", 0.0),
            source=data.get("source"),
            last_updated=data.get("last_updated"),
            questions=data.get("questions", []),
            ask_after=data.get("ask_after")
        )

class DynamicProjectSchema:
    """動的プロジェクト情報スキーマ管理"""
    
    def __init__(self, project_id: str, projects_dir: Path = None):
        self.project_id = project_id
        self.projects_dir = projects_dir or Path("data/projects")
        self.fields: Dict[str, DynamicField] = {}
        self.schema_version = "1.0"
        self.last_analyzed = None
        self._load_from_project_file()
    
    def _get_project_file_path(self) -> Path:
        """プロジェクトファイルのパスを取得"""
        return self.projects_dir / f"{self.project_id}.json"
    
    def _load_from_project_file(self):
        """プロジェクトファイルから動的スキーマを読み込み"""
        project_file = self._get_project_file_path()
        
        if not project_file.exists():
            logger.warning(f"Project file not found: {project_file}")
            return
        
        try:
            with open(project_file, 'r', encoding='utf-8') as f:
                project_data = json.load(f)
            
            dynamic_info = project_data.get("dynamic_info", {})
            self.schema_version = dynamic_info.get("schema_version", "1.0")
            self.last_analyzed = dynamic_info.get("last_analyzed")
            
            # フィールドを復元
            fields_data = dynamic_info.get("fields", {})
            for field_name, field_data in fields_data.items():
                self.fields[field_name] = DynamicField.from_dict(field_name, field_data)
                
        except Exception as e:
            logger.error(f"Failed to load dynamic schema for {self.project_id}: {e}")
    
    def save_to_project_file(self):
        """プロジェクトファイルに動的スキーマを保存"""
        project_file = self._get_project_file_path()
        
        if not project_file.exists():
            logger.error(f"Project file not found: {project_file}")
            return False
        
        try:
            # 既存のプロジェクトデータを読み込み
            with open(project_file, 'r', encoding='utf-8') as f:
                project_data = json.load(f)
            
            # dynamic_infoを更新
            dynamic_info = {
                "schema_version": self.schema_version,
                "last_analyzed": datetime.now().isoformat(),
                "fields": {name: field.to_dict() for name, field in self.fields.items()}
            }
            
            project_data["dynamic_info"] = dynamic_info
            
            # ファイルに保存
            with open(project_file, 'w', encoding='utf-8') as f:
                json.dump(project_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Dynamic schema saved for project {self.project_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save dynamic schema for {self.project_id}: {e}")
            return False
    
    def add_field(self, name: str, priority: FieldPriority = FieldPriority.RECOMMENDED, 
                  questions: List[str] = None, ask_after: str = None) -> bool:
        """新しいフィールドを追加"""
        if name in self.fields:
            logger.warning(f"Field {name} already exists")
            return False
        
        self.fields[name] = DynamicField(
            name=name,
            priority=priority,
            questions=questions or [],
            ask_after=ask_after
        )
        
        logger.info(f"Added field {name} with priority {priority.value}")
        return True
    
    def update_field_value(self, name: str, value: Any, confidence: float = 1.0, 
                          source: str = "conversation") -> bool:
        """フィールド値を更新"""
        if name not in self.fields:
            logger.warning(f"Field {name} does not exist")
            return False
        
        field = self.fields[name]
        field.value = value
        field.confidence = confidence
        field.source = source
        field.last_updated = datetime.now().isoformat()
        
        # ステータスを更新
        if value is not None and confidence > 0.8:
            field.status = FieldStatus.DEFINED
        elif value is not None:
            field.status = FieldStatus.PARTIAL
        
        logger.info(f"Updated field {name} with value: {value}")
        return True
    
    def set_field_priority(self, name: str, priority: FieldPriority) -> bool:
        """フィールドの優先度を設定（人間による調整）"""
        if name not in self.fields:
            logger.warning(f"Field {name} does not exist")
            return False
        
        old_priority = self.fields[name].priority
        self.fields[name].priority = priority
        
        logger.info(f"Changed field {name} priority from {old_priority.value} to {priority.value}")
        return True
    
    def get_pending_questions(self, max_questions: int = 3) -> List[Tuple[str, List[str]]]:
        """質問すべきフィールドとその質問を取得"""
        pending = []
        
        # 優先度順でソート
        priority_order = {
            FieldPriority.REQUIRED: 0,
            FieldPriority.RECOMMENDED: 1, 
            FieldPriority.OPTIONAL: 2
        }
        
        sorted_fields = sorted(
            self.fields.items(),
            key=lambda x: (
                priority_order.get(x[1].priority, 3),
                x[1].status == FieldStatus.UNDEFINED
            )
        )
        
        for field_name, field in sorted_fields:
            if (field.priority != FieldPriority.DISABLED and 
                field.status == FieldStatus.UNDEFINED and 
                field.questions and
                self._should_ask_field(field_name)):
                
                pending.append((field_name, field.questions))
                
                if len(pending) >= max_questions:
                    break
        
        return pending
    
    def _should_ask_field(self, field_name: str) -> bool:
        """フィールドについて質問すべきかを判定"""
        field = self.fields[field_name]
        
        # ask_afterが設定されている場合、そのフィールドが定義されているかチェック
        if field.ask_after:
            prerequisite_field = self.fields.get(field.ask_after)
            if not prerequisite_field or prerequisite_field.status == FieldStatus.UNDEFINED:
                return False
        
        return True
    
    def get_field_summary(self) -> Dict[str, int]:
        """フィールドの状況サマリーを取得"""
        summary = {
            "total": len(self.fields),
            "required": 0,
            "recommended": 0,
            "optional": 0,
            "defined": 0,
            "undefined": 0
        }
        
        for field in self.fields.values():
            # 優先度別カウント
            if field.priority == FieldPriority.REQUIRED:
                summary["required"] += 1
            elif field.priority == FieldPriority.RECOMMENDED:
                summary["recommended"] += 1
            elif field.priority == FieldPriority.OPTIONAL:
                summary["optional"] += 1
            
            # 状態別カウント
            if field.status in [FieldStatus.DEFINED, FieldStatus.CONFIRMED]:
                summary["defined"] += 1
            else:
                summary["undefined"] += 1
        
        return summary
    
    def get_completion_percentage(self) -> float:
        """プロジェクト情報の完成度を計算"""
        if not self.fields:
            return 0.0
        
        total_weight = 0
        completed_weight = 0
        
        weight_map = {
            FieldPriority.REQUIRED: 3.0,
            FieldPriority.RECOMMENDED: 2.0,
            FieldPriority.OPTIONAL: 1.0,
            FieldPriority.DISABLED: 0.0
        }
        
        for field in self.fields.values():
            weight = weight_map.get(field.priority, 0.0)
            total_weight += weight
            
            if field.status in [FieldStatus.DEFINED, FieldStatus.CONFIRMED]:
                completed_weight += weight
            elif field.status == FieldStatus.PARTIAL:
                completed_weight += weight * 0.5
        
        return (completed_weight / total_weight * 100) if total_weight > 0 else 0.0


# ユーティリティ関数
def get_project_schema(project_id: str, projects_dir: Path = None) -> DynamicProjectSchema:
    """プロジェクトのスキーマを取得"""
    return DynamicProjectSchema(project_id, projects_dir)

def initialize_schema_for_project(project_id: str, project_description: str, 
                                projects_dir: Path = None) -> DynamicProjectSchema:
    """プロジェクトのスキーマを初期化（将来的にはAI分析による自動生成）"""
    schema = DynamicProjectSchema(project_id, projects_dir)
    
    # 現在は手動で基本フィールドを追加
    # 将来的にはproject_descriptionを分析して動的に生成
    basic_fields = [
        ("participants", FieldPriority.REQUIRED, ["参加者は何名ですか？"]),
        ("timeline", FieldPriority.REQUIRED, ["実施予定時期はいつ頃ですか？"]),
        ("budget", FieldPriority.RECOMMENDED, ["予算の目安はありますか？"])
    ]
    
    for name, priority, questions in basic_fields:
        schema.add_field(name, priority, questions)
    
    schema.save_to_project_file()
    return schema