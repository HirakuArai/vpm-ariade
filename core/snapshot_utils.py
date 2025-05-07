# core/snapshot_utils.py

import os
import subprocess
import json

SNAPSHOT_PATH = "output/master_snapshot.json"

def regenerate_master_snapshot():
    print("🛠 Generating master_snapshot.json ...")
    subprocess.run(["python", "scripts/gen_master_snapshot.py"], check=True)


def load_master_snapshot():
    if not os.path.exists(SNAPSHOT_PATH):
        raise FileNotFoundError("master_snapshot.json が存在しません。")
    with open(SNAPSHOT_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def get_function_snapshot_min(snapshot):
    return [
        {
            "path": item["path"],
            "functions": item.get("ast", {}).get("functions", [])
        }
        for item in snapshot if "ast" in item
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
