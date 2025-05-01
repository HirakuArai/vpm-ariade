# scripts/sync_kai_state.py

import os
import json
from datetime import datetime
import subprocess

from core.git_ops import try_git_pull_safe
from core.log_utils import (
    check_unprocessed_logs,
    messages_to_text,
    load_yesterdays_log_as_messages
)
from core.doc_update_engine import propose_doc_update, apply_update
from core.enforcement import enforce_rules
from core.capabilities_diff import (
    load_ast_capabilities,
    load_json_capabilities,
    compare_capabilities
)
from core.utils import write_file

STATE_PATH = "data/kai_state.json"

def sync_kai():
    # 1. 最新の状態にgit pull
    try_git_pull_safe()

    # 2. 未処理ログの確認とドキュメント更新提案（自動承認）
    unprocessed = check_unprocessed_logs()
    updates = []
    for fname in unprocessed:
        doc_name = "project_status.md"  # 将来的にマッピング可能に
        messages = load_yesterdays_log_as_messages(fname)
        conv_text = messages_to_text(messages)
        proposal = propose_doc_update(doc_name, conv_text)
        apply_update(doc_name, proposal, auto_approve=True)
        updates.append(doc_name)

    # 3. kai_rules.json 再生成
    subprocess.run(["python", "scripts/generate_kai_rules.py"])

    # 4. 必要な能力リストを再生成（GPT）
    subprocess.run(["python", "scripts/scan_required_capabilities_gpt.py"])

    # 5. ルール違反の検出（例: 自動更新の中での誤操作チェック）
    action_context = {"action": "sync", "approved": True}  # 必要に応じて拡張
    rule_violations = enforce_rules(action_context)

    # 6. ASTベースと登録済みcapabilitiesの差分を取得
    ast_caps = load_ast_capabilities()
    json_caps = load_json_capabilities()
    cap_diff = compare_capabilities(ast_caps, json_caps)

    # 7. 結果を1ファイルに統合保存
    state = {
        "timestamp": datetime.now().isoformat(),
        "doc_updates": updates,
        "rule_violations": rule_violations,
        "capability_diff": cap_diff
    }
    write_file(STATE_PATH, json.dumps(state, ensure_ascii=False, indent=2))
    print(f"✅ kai_state.json updated → {STATE_PATH}")

if __name__ == "__main__":
    sync_kai()
