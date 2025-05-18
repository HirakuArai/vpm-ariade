"""app.py – Kai (Streamlit UI, JSON conversation logger)
-----------------------------------------------------------------------------
This version adds a persistent conversation‑logging feature:
    • 1‑day‑per‑file JSON log written to ./conversations/conversation_YYYYMMDD.json
    • every user/assistant exchange is appended immediately
The rest of the original Kai chat behaviour is preserved.
"""
from __future__ import annotations

import json
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path
from textwrap import dedent
from zoneinfo import ZoneInfo

import openai  # openai-python >= 1.1.0
import streamlit as st

# ────────────────────────────────────────────────────────────────────────────
# Paths & basic setup
# ────────────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent
DOCS = ROOT / "docs"
DSL_DIR = ROOT / "dsl"
CONV_DIR = ROOT / "conversations"
CONV_DIR.mkdir(parents=True, exist_ok=True)

# ────────────────────────────────────────────────────────────────────────────
# OpenAI API key (ENV > Streamlit secrets)
# ────────────────────────────────────────────────────────────────────────────
openai.api_key = os.getenv("OPENAI_API_KEY", st.secrets.get("OPENAI_API_KEY", ""))
if not openai.api_key:
    st.error("❌ OPENAI_API_KEY が設定されていません")

# ────────────────────────────────────────────────────────────────────────────
# Conversation‑log helpers (JSON, 1‑day‑per‑file)
# ────────────────────────────────────────────────────────────────────────────

_JST = ZoneInfo("Asia/Tokyo")


def _today_log_path() -> Path:
    """Return Path for today's conversation log."""
    today = datetime.now(_JST).strftime("%Y%m%d")
    return CONV_DIR / f"conversation_{today}.json"


def _append_log(role: str, content: str) -> None:
    """Append a single message to today's JSON log."""
    log_path = _today_log_path()
    now_iso = datetime.now(_JST).isoformat(timespec="seconds")

    if log_path.exists():
        with log_path.open(encoding="utf-8") as fp:
            data = json.load(fp)
    else:
        data = {"log_id": datetime.now(_JST).strftime("%Y%m%d"), "messages": []}

    data["messages"].append({"role": role, "content": content, "ts": now_iso})
    with log_path.open("w", encoding="utf-8") as fp:
        json.dump(data, fp, ensure_ascii=False, indent=2)


# ────────────────────────────────────────────────────────────────────────────
# Small utils
# ────────────────────────────────────────────────────────────────────────────

def _read(path: Path | str) -> str:
    return Path(path).read_text(encoding="utf-8")


def _extract_section(md_path: Path, headings: list[str]) -> str:
    """Extract only specified headings from markdown (unused but kept)."""
    lines = _read(md_path).splitlines()
    keep, buf = False, []
    for line in lines:
        if line.startswith("#"):
            title = line.lstrip("# ").strip()
            keep = title in headings
        if keep:
            buf.append(line)
    return "\n".join(buf)


# ────────────────────────────────────────────────────────────────────────────
# Prompt generator
# ────────────────────────────────────────────────────────────────────────────

def get_system_prompt() -> str:
    rules = _read(DOCS / "base_os_rules.md")

    dsl_readme = (DSL_DIR / "README.md").read_text(encoding="utf-8") if (DSL_DIR / "README.md").exists() else ""
    dsl_lines: list[str] = []
    try:
        for raw in (DSL_DIR / "integrated_dsl.jsonl").read_text(encoding="utf-8").splitlines():
            item = json.loads(raw)
            name, desc = item.get("name"), item.get("description")
            if name and desc:
                dsl_lines.append(f"- **{name}**: {desc}")
    except FileNotFoundError:
        pass
    dsl_block = "\n".join([dsl_readme.strip()] + dsl_lines if dsl_readme else dsl_lines)

    proj = _read(DOCS / "project_definition.md")
    arch = _read(DOCS / "architecture_overview.md")

    return "\n\n".join([rules, dsl_block, proj, arch])


# ────────────────────────────────────────────────────────────────────────────
# Streamlit UI
# ────────────────────────────────────────────────────────────────────────────

st.set_page_config(page_title="Kai Chat", page_icon="🤖", layout="centered")
st.title("Kai – Virtual Project Manager Chat")

if "history" not in st.session_state:
    st.session_state["history"] = []

# 履歴表示（セッション全件を常時下スクロール表示）
for msg in st.session_state["history"]:
    st.chat_message("user" if msg["role"] == "user" else "assistant").markdown(msg["content"])

# ユーザー入力
user_input = st.chat_input("あなたの発言を入力してください…")

if user_input:
    # 1) ログへ保存
    _append_log("user", user_input)

    # 2) GPT へ問い合わせ
    try:
        system_prompt = get_system_prompt()
        messages = [{"role": "system", "content": system_prompt}] + \
                   st.session_state["history"] + \
                   [{"role": "user", "content": user_input}]

        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",  # TODO: replace with "gpt-4.1" when available
            messages=messages,
        )
        assistant_reply = response.choices[0].message.content.strip()
    except Exception as e:
        st.error(f"❌ OpenAI 呼び出し失敗: {e}")
        traceback.print_exc()
        assistant_reply = "[ERROR]"  # fallback text

    # 3) UI 表示
    st.chat_message("user").markdown(user_input)
    st.chat_message("assistant").markdown(assistant_reply)

    # 4) 履歴保存 & ログへ保存
    st.session_state["history"].extend([
        {"role": "user", "content": user_input},
        {"role": "assistant", "content": assistant_reply},
    ])
    _append_log("assistant", assistant_reply)

# ────────────────────────────────────────────────────────────────────────────
# Footer / debug info (optional)
# ────────────────────────────────────────────────────────────────────────────

st.caption("version: 2025-05-19 JSON‑log enabled")
