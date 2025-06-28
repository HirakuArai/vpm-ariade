# core/snapshot_utils.py
# core/snapshot_utils.py – use current interpreter for snapshot generation
"""Utility: regenerate master_snapshot.json for Kai.
This patch replaces hard‑coded 'python' with sys.executable so that the
script runs inside the same virtual‑env (PyYAML import works).
"""
from __future__ import annotations

import os
import subprocess
import sys
import json

SNAPSHOT_PATH = "output/master_snapshot.json"

def regenerate_master_snapshot() -> None:
    """Generate master_snapshot.json using the active Python interpreter."""
    print("🛠 Generating master_snapshot.json ...", flush=True)

    # Use the exact interpreter running this process to guarantee the same venv
    script_path = "archive/scripts/gen_master_snapshot.py"
    if not os.path.exists(script_path):
        # Fallback for legacy path
        script_path = "scripts/gen_master_snapshot.py"
    
    if not os.path.exists(script_path):
        print(f"❌ Snapshot script not found at {script_path}")
        print("⚠️ Skipping snapshot generation due to archived scripts")
        return
    
    subprocess.run(
        [sys.executable, script_path],
        check=True,
    )


def load_master_snapshot():
    if not os.path.exists(SNAPSHOT_PATH):
        raise FileNotFoundError("master_snapshot.json が存在しません。")
    with open(SNAPSHOT_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def get_function_snapshot_min(snapshot):
    """各 .py ファイルに含まれる関数名だけを抽出（件数制限なし）"""
    return [
        {
            "path": item["path"],
            "functions": [f["name"] for f in item.get("ast", {}).get("functions", [])]
        }
        for item in snapshot
        if "ast" in item and item["ast"].get("functions")
    ]


def get_structure_snapshot_min(snapshot):
    return [
        {
            "path": item["path"],
            "md5": item["md5"],
            "size": item["size"]
        }
        for item in snapshot
    ]
