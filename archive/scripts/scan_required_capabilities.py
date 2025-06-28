import os
import re
import json
from collections import defaultdict

# ---------------------------------------------
# scan_required_capabilities.py
# ---------------------------------------------
# docs/ 配下の Markdown を走査し、
# - 役割 (project_manager など) ごとに
# - 必要と推測される capability ID
# を抽出して JSON で出力するスクリプト。
# ---------------------------------------------

DOCS_DIR = "docs"
OUTPUT_PATH = "output/needed_capabilities_autogen.json"

# キーワード → capability ID 対応辞書
KEYWORD_MAPPING = {
    # タスク管理
    r"タスク(作成|追加)": "create_task",
    r"タスク(更新|編集)": "update_task",
    r"タスク(削除)": "delete_task",
    r"タスク一覧": "list_tasks",

    # 承認フロー / ドキュメント
    r"承認": "handle_approval",
    r"修正提案": "doc_update_proposal",
    r"GPT修正": "apply_patch",

    # Git 操作
    r"git (pull|最新化|取得)": "try_git_pull_safe",
    r"git (commit|コミット)": "try_git_commit",

    # ログ
    r"ログ(保存|追記)": "append_to_log",
    r"ログ(読み込み|参照)": "load_conversation_messages",
}

ROLE = "project_manager"  # 今は固定。将来拡張可。


def extract_required_capabilities():
    pattern_cache = {p: re.compile(p) for p in KEYWORD_MAPPING}
    required = defaultdict(set)

    for file in os.listdir(DOCS_DIR):
        if not file.endswith(".md"):
            continue
        with open(os.path.join(DOCS_DIR, file), encoding="utf-8") as f:
            text = f.read()
        for patt, cid in pattern_cache.items():
            if patt in text or pattern_cache[patt].search(text):
                required[ROLE].add(KEYWORD_MAPPING[patt])

    return {
        "role": ROLE,
        "required_capabilities": sorted(required[ROLE])
    }


def main():
    data = extract_required_capabilities()
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Generated {OUTPUT_PATH} with {len(data['required_capabilities'])} capability IDs.")


if __name__ == "__main__":
    main()
