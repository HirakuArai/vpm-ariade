"""app.py – Kai (Minimal GPT Chat with Robust Prompt, OpenAI v1.x)"""

# ── Imports & Setup ─────────────────────────────────────────────
from __future__ import annotations
import os, json, sys, traceback
from pathlib import Path
from textwrap import dedent
import streamlit as st
import openai  # openai-python >=1.1.0 に対応

# .env 読み込み（ローカル開発用）
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# API キー設定（secrets.toml > 環境変数）
openai.api_key = os.getenv("OPENAI_API_KEY", st.secrets.get("OPENAI_API_KEY", ""))
if not openai.api_key:
    st.error("❌ OPENAI_API_KEY が設定されていません")

ROOT = Path(__file__).resolve().parent
DOCS = ROOT / "docs"
DSL  = ROOT / "dsl"

# ── Utilities ───────────────────────────────────────────────────

def read(path: Path | str) -> str:
    return Path(path).read_text(encoding="utf-8")

def extract_section(md_path: Path, headings: list[str]) -> str:
    """Markdownから指定見出しのみ抽出"""
    lines = read(md_path).splitlines()
    keep, buf = False, []
    for line in lines:
        if line.startswith("#"):
            title = line.lstrip("# ").strip()
            keep = title in headings
        if keep:
            buf.append(line)
    return "\n".join(buf)

# ── Prompt Generator ───────────────────────────────────────────

def get_system_prompt() -> str:
    # A) OS ルール
    rules = read(DOCS / "base_os_rules.md")

    # B) DSL
    dsl_readme = (DSL / "README.md").read_text(encoding="utf-8") if (DSL / "README.md").exists() else ""
    dsl_lines: list[str] = []
    for raw in (DSL / "integrated_dsl.jsonl").read_text(encoding="utf-8").splitlines():
        try:
            item = json.loads(raw)
            name, desc = item.get("name"), item.get("description")
            if name and desc:
                dsl_lines.append(f"- **{name}**: {desc}")
        except Exception:
            continue
    dsl_block = "\n".join([dsl_readme.strip()] + dsl_lines if dsl_readme else dsl_lines)

    # C) Project Definition
    proj = extract_section(DOCS / "project_definition.md", ["目的", "ゴール", "Kai Support の役割"])

    # D) Architecture Overview
    arch = extract_section(DOCS / "architecture_overview.md", ["PoC構成", "運用フロー"])

    return "\n\n".join([rules, dsl_block, proj, arch])

# ── Streamlit UI ───────────────────────────────────────────────
st.set_page_config(page_title="Kai Chat", page_icon="💬")
st.title("💬 Kai - GPTチャット")

if "history" not in st.session_state:
    st.session_state["history"] = []

# 履歴表示
for msg in st.session_state["history"]:
    st.chat_message("user" if msg["role"] == "user" else "assistant").markdown(msg["content"])

# 入力欄（常に最下段）
user_input = st.chat_input("あなたの発言")  # ← ここだけ変更

if user_input:
    try:
        system_prompt = get_system_prompt()
        msgs = [{"role": "system", "content": system_prompt}] + \
               st.session_state["history"] + \
               [{"role": "user", "content": user_input}]
        reply = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=msgs
        ).choices[0].message.content

        st.session_state["history"].extend([
            {"role": "user", "content": user_input},
            {"role": "assistant", "content": reply},
        ])
        # rerun 不要。chat_input は送信後に自動クリアされる
    except Exception as e:
        st.error(f"❌ OpenAI 呼び出し失敗: {e}")
        traceback.print_exc()
