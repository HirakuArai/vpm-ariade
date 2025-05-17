"""app.py – Kai (Minimal GPT Chat with Robust Prompt)"""

# ── Imports & Setup ─────────────────────────────────────────────
from __future__ import annotations
import os, json, sys, traceback
from pathlib import Path
from textwrap import dedent
import streamlit as st
import openai

# Read .env if present (local dev)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# API‑KEY 設定（secrets.toml > env の順）
openai.api_key = os.getenv("OPENAI_API_KEY", st.secrets.get("OPENAI_API_KEY", ""))
if not openai.api_key:
    st.error("❌ OPENAI_API_KEY が設定されていません")

ROOT = Path(__file__).resolve().parent
DOCS = ROOT / "docs"
DSL  = ROOT / "dsl"

# ── Utilities ──────────────────────────────────────────────────

def read(path: Path | str) -> str:
    return Path(path).read_text(encoding="utf-8")

def extract_section(md_path: Path, headings: list[str]) -> str:
    """Markdownから指定見出しのブロックだけ抽出"""
    lines = read(md_path).splitlines()
    keep, buf = False, []
    for line in lines:
        if line.startswith("#"):
            title = line.lstrip("# ").strip()
            keep = title in headings
        if keep:
            buf.append(line)
    return "\n".join(buf)

# ── Prompt Generator ──────────────────────────────────────────

def get_system_prompt() -> str:
    """Kai が毎回使う System Prompt を生成"""
    # A) 最優先 OS ルール
    rules = read(DOCS / "base_os_rules.md")

    # B) DSL (README + name/description)
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

    # C) Project Definition (主要見出しのみ)
    proj = extract_section(DOCS / "project_definition.md", ["目的", "ゴール", "Kai Support の役割"])

    # D) Architecture Overview (主要見出しのみ)
    arch = extract_section(DOCS / "architecture_overview.md", ["PoC構成", "運用フロー"])

    return "\n\n".join([rules, dsl_block, proj, arch])

# ── Streamlit UI ──────────────────────────────────────────────
st.set_page_config(page_title="Kai Chat", page_icon="💬")
st.title("💬 Kai - GPTチャット")

if "history" not in st.session_state:
    st.session_state["history"] = []

# 履歴表示
for msg in st.session_state["history"]:
    st.chat_message("user" if msg["role"] == "user" else "assistant").markdown(msg["content"])

# 入力欄 (最下段に来る)
user_input = st.text_input("あなたの発言（送信でEnter）", "")

if user_input:
    try:
        system_prompt = get_system_prompt()
        messages = [{"role": "system", "content": system_prompt}] + st.session_state["history"] + [{"role": "user", "content": user_input}]

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  # 利用可能モデルに合わせて変更
            messages=messages,
        )
        reply = response.choices[0].message.content

        st.session_state["history"].append({"role": "user", "content": user_input})
        st.session_state["history"].append({"role": "assistant", "content": reply})
        # ページ再描画は不要（入力欄が下に残り続ける）
        st.rerun()
    except Exception as e:
        st.error(f"❌ OpenAI 呼び出し失敗: {e}")
        traceback.print_exc(file=sys.stdout)
