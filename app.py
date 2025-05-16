"""
Optimized Streamlit‑Kai entrypoint.
- Focuses on **minimal, deterministic** prompt generation.
- Always pulls the latest project rules / definition / architecture & DSL.
- Self‑check utilities live in `selfcheck.py` (not shown here).
"""
from __future__ import annotations

import json
import streamlit as st
from pathlib import Path
from textwrap import dedent

# ────────────────────────────────────────────────
# ✨ Utility helpers
# ────────────────────────────────────────────────

ROOT = Path(__file__).resolve().parent
DOCS = ROOT / "docs"
DSL  = ROOT / "dsl"


def read(path: str | Path) -> str:
    """Read UTF‑8 text file."""
    return Path(path).read_text(encoding="utf‑8")


def extract_section(md_path: Path, headings: list[str]) -> str:
    """Return Markdown for only the specified top‑level headings.

    ▸ `headings` is a list of H1/H2 text to keep.
    ▸ Stops at the next heading of the same level.
    """
    lines = read(md_path).splitlines()
    keep, buf = False, []
    for line in lines:
        if line.startswith("#"):
            title = line.lstrip("# ").strip()
            keep = title in headings
        if keep:
            buf.append(line)
    return "\n".join(buf)


# ────────────────────────────────────────────────
# 🔑  Prompt generator (single source of truth)
# ────────────────────────────────────────────────

def get_system_prompt() -> str:
    """Return the **minimal & complete** system prompt for Kai."""

    # 1) Core operating rules
    rules = read(DOCS / "base_os_rules.md")

    # 2) Project definition & architecture (key sections only)
    proj = extract_section(DOCS / "project_definition.md", ["目的", "ゴール", "Kai Support の役割"])
    arch = extract_section(DOCS / "architecture_overview.md", ["PoC構成", "運用フロー"])

    # 3) DSL – capabilities catalogue (name & description only)
    dsl_lines = []
    for raw in (DSL / "integrated_dsl.jsonl").read_text(encoding="utf-8").splitlines():
        try:
            item = json.loads(raw)
            name = item.get('name')
            desc = item.get('description')
            if not name or not desc:
                continue  # 必須項目欠落はスキップ
            dsl_lines.append(f"- **{name}**: {desc}")
        except Exception:
            continue  # パースできない行もスキップ
    dsl_block = "\n".join(dsl_lines)

    # 4) Compose
    prompt = dedent(
        f"""\
        ## Base Rules
        {rules}

        ## Project Overview
        {proj}

        ## Architecture Snapshot
        {arch}

        ## Kai Capabilities (DSL – single source of truth)
        {dsl_block}
        """
    ).strip()

    return prompt


# ────────────────────────────────────────────────
# Example usage inside Streamlit Kai (pseudo‑code)
# ────────────────────────────────────────────────

if __name__ == "__main__":  # local test
    print(get_system_prompt()[:1000])  # preview first 1k chars


# ページ設定
st.set_page_config(page_title="Kai Chat", page_icon="💬")
st.title("💬 Kai - GPTチャット")

# 入力履歴のセッション管理
if "history" not in st.session_state:
    st.session_state["history"] = []

# ユーザー入力
user_input = st.text_input("あなたの発言（送信でEnter）", "")

# システムプロンプト生成
system_prompt = get_system_prompt()

# 入力があれば送信
if user_input:
    import openai  # 必要なら先頭でimport
    # OpenAIキーをどこかでセットすること
    messages = [{"role": "system", "content": system_prompt}]
    for msg in st.session_state["history"]:
        messages.append(msg)
    messages.append({"role": "user", "content": user_input})
    # GPT-4.1呼び出し（必要に応じてAPIキーをセット）
    response = openai.chat.completions.create(
        model="gpt-4.1",
        messages=messages
    )
    reply = response.choices[0].message.content
    st.session_state["history"].append({"role": "user", "content": user_input})
    st.session_state["history"].append({"role": "assistant", "content": reply})
    st.experimental_rerun()  # ページを再描画

# 履歴表示
for msg in st.session_state["history"]:
    is_user = msg["role"] == "user"
    st.chat_message("user" if is_user else "assistant").markdown(msg["content"])
