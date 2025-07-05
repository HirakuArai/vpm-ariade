"""
Memory Layer Phase 2 Configuration
安全性を重視したフィーチャーフラグ設定
"""

import os
from typing import Dict, Any

# Memory Layer フィーチャーフラグ
MEMORY_LAYER_ENABLED = os.getenv("MEMORY_LAYER_ENABLED", "False") == "True"
MEMORY_READ_ENABLED = os.getenv("MEMORY_READ_ENABLED", "False") == "True"

# Memory Layer 設定
MEMORY_CONFIG: Dict[str, Any] = {
    # 基本設定
    "enabled": MEMORY_LAYER_ENABLED,
    "read_enabled": MEMORY_READ_ENABLED,
    
    # パス設定
    "memory_repo_path": "memory_repo",
    "current_memory_file": "current_memory.json",
    "events_dir": "events",
    "snapshots_dir": "snapshots",
    "schema_dir": "schema",
    
    # イベントログ設定
    "max_events_per_file": 1000,
    "auto_rotate_logs": True,
    "log_format": "jsonl",
    
    # スナップショット設定
    "nightly_snapshot_enabled": False,  # Phase 3で有効化
    "snapshot_retention_days": 30,
    
    # GitHub同期設定
    "auto_sync_enabled": False,  # 段階的に有効化
    "sync_interval_hours": 1,
    "batch_commit_enabled": True,
    
    # 安全設定
    "max_memory_size_mb": 10,
    "validate_schema": True,
    "backup_before_write": True,
}

def get_memory_config() -> Dict[str, Any]:
    """メモリレイヤー設定を取得"""
    return MEMORY_CONFIG.copy()

def is_memory_enabled() -> bool:
    """メモリレイヤーが有効かチェック"""
    return MEMORY_LAYER_ENABLED

def is_memory_read_enabled() -> bool:
    """メモリ読み取りが有効かチェック"""
    return MEMORY_READ_ENABLED

# デバッグ用設定確認
if __name__ == "__main__":
    print("Memory Layer Configuration:")
    print(f"  MEMORY_LAYER_ENABLED: {MEMORY_LAYER_ENABLED}")
    print(f"  MEMORY_READ_ENABLED: {MEMORY_READ_ENABLED}")
    print(f"  Config: {get_memory_config()}")