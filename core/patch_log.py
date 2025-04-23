# core/patch_log.py

import os
import json
from datetime import datetime

LOG_PATH = "patch_history.json"

def log_patch(fn_name: str, user_instruction: str, markdown_diff: str):
    record = {
        "timestamp": datetime.now().isoformat(),
        "function": fn_name,
        "instruction": user_instruction,
        "diff": markdown_diff
    }

    try:
        logs_dir = os.path.dirname(LOG_PATH)
        if logs_dir:
            os.makedirs(logs_dir, exist_ok=True)

        if not os.path.exists(LOG_PATH):
            with open(LOG_PATH, "w", encoding="utf-8") as f:
                json.dump([record], f, ensure_ascii=False, indent=2)
        else:
            with open(LOG_PATH, "r", encoding="utf-8") as f:
                try:
                    history = json.load(f)
                except json.JSONDecodeError:
                    history = []

            history.append(record)
            with open(LOG_PATH, "w", encoding="utf-8") as f:
                json.dump(history, f, ensure_ascii=False, indent=2)

        print(f"📝 パッチ履歴を {LOG_PATH} に保存しました。", flush=True)

    except Exception as e:
        print(f"❌ パッチ履歴の保存に失敗しました: {e}", flush=True)
