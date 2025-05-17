"""
Optimized Streamlit‑Kai entrypoint.
- Focuses on **minimal, deterministic** prompt generation.
- Always pulls the latest project rules / definition / architecture & DSL.
- Self‑check utilities live in `selfcheck.py` (not shown here).
"""
from pathlib import Path
import json
from textwrap import dedent

import streamlit as st

ROOT = Path(__file__).resolve().parent
DOCS = ROOT / "docs"
DSL  = ROOT / "dsl"

def read(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8")

def extract_section(md_path: Path, headings: list[str]) -> str:
    lines = read(md_path).splitlines()
    keep, buf = False, []
    for line in lines:
        if line.startswith("#"):
            title = line.lstrip("# ").strip()
            keep = title in headings
        if keep:
            buf.append(line)
    return "\n".join(buf)

def get_system_prompt() -> str:
    # (a) base_os_rules.md（YAML+役割宣言付き）
    rules = read(DOCS / "base_os_rules.md")

    # (b) integrated_dsl.jsonl（README+name/description一覧）
    dsl_readme = ""
    dsl_readme_path = DSL / "README.md"
    if dsl_readme_path.exists():
        dsl_readme = read(dsl_readme_path)
    dsl_lines = []
    for raw in (DSL / "integrated_dsl.jsonl").read_text(encoding="utf-8").splitlines():
        try:
            item = json.loads(raw)
            name = item.get('name')
            desc = item.get('description')
            if not name or not desc:
                continue
            dsl_lines.append(f"- **{name}**: {desc}")
        except Exception:
            continue
    dsl_block = "\n".join([dsl_readme.strip()] + dsl_lines if dsl_readme else dsl_lines)

    # (c) project_definition.md（役割宣言＋抜粋）
    proj = extract_section(DOCS / "project_definition.md", ["目的", "ゴール", "Kai Support の役割"])

    # (d) architecture_overview.md（役割宣言＋抜粋）
    arch = extract_section(DOCS / "architecture_overview.md", ["PoC構成", "運用フロー"])

    return "\n\n".join([rules, dsl_block, proj, arch])

# ────────────────────────────────────────────────
# Example usage inside Streamlit Kai (pseudo‑code)
# ────────────────────────────────────────────────

st.set_page_config(page_title="Kai Chat", page_icon="💬")
st.title("💬 Kai - GPTチャット")

if "history" not in st.session_state:
    st.session_state["history"] = []

# ① 履歴を上から順に表示
for msg in st.session_state["history"]:
    is_user = msg["role"] == "user"
    st.chat_message("user" if is_user else "assistant").markdown(msg["content"])

# ② 入力欄を一番下に
user_input = st.text_input("あなたの発言（送信でEnter）", "")

# 入力があれば送信
if user_input:
    import openai
    system_prompt = get_system_prompt()
    messages = [{"role": "system", "content": system_prompt}]
    for msg in st.session_state["history"]:
        messages.append(msg)
    messages.append({"role": "user", "content": user_input})
    response = openai.chat.completions.create(
        model="gpt-4.1",
        messages=messages
    )
    reply = response.choices[0].message.content
    st.session_state["history"].append({"role": "user", "content": user_input})
    st.session_state["history"].append({"role": "assistant", "content": reply})