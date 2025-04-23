# core/patch_log.py

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
        if not os.path.exists(LOG_PATH):
            with open(LOG_PATH, "w", encoding="utf-8") as f:
                json.dump([record], f, ensure_ascii=False, indent=2)
        else:
            with open(LOG_PATH, "r+", encoding="utf-8") as f:
                history = json.load(f)
                history.append(record)
                f.seek(0)
                json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"❌ パッチ履歴の保存に失敗しました: {e}")
