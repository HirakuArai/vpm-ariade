# core/patch_log.py

import os
import json
from datetime import datetime
import streamlit as st  # show_patch_log用に必要

LOG_PATH = "patch_history.json"

def log_patch(fn_name: str, user_instruction: str, markdown_diff: str):
    """関数修正履歴をpatch_history.jsonに保存する"""
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

def load_patch_history(log_path=LOG_PATH):
    """patch_history.jsonから履歴を読み込む"""
    if not os.path.exists(log_path):
        return []
    try:
        with open(log_path, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ 履歴読み込みに失敗しました: {e}", flush=True)
        return []

def show_patch_log():
    """patch_history.jsonから履歴をStreamlitで表示する"""
    st.subheader("📘 修正履歴ログ（ドキュメント）")
    patch_log_path = LOG_PATH

    if not os.path.exists(patch_log_path):
        st.info("修正履歴はまだありません。")
        return

    try:
        with open(patch_log_path, "r", encoding="utf-8") as f:
            patch_logs = json.load(f)
    except Exception as e:
        st.error(f"修正履歴の読み込み時にエラーが発生しました: {e}")
        return

    if not patch_logs:
        st.info("修正履歴はまだありません。")
        return

    # 新しい順に並べる
    patch_logs_sorted = sorted(
        patch_logs,
        key=lambda x: x.get("timestamp", ""),
        reverse=True
    )

    for log in patch_logs_sorted:
        dt = log.get("timestamp", "日時不明")
        fname = log.get("function", "関数名不明")
        diff = log.get("diff", "")
        instruction = log.get("instruction", "")

        with st.expander(f"{dt} — {fname}", expanded=False):
            st.write("**指示内容：**")
            st.code(instruction, language="markdown")
            st.write("**差分内容：**")
            st.code(diff, language="diff")
