# core/doc_update_engine.py

import os
from openai import OpenAI
from core.log_utils import messages_to_text

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DOCS_DIR = os.path.join(BASE_DIR, "docs")

# OpenAIクライアント初期化（.envのOPENAI_API_KEYを自動使用）
client = OpenAI()

def safe_load_text(path: str) -> str:
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return ""

def propose_doc_update(doc_name: str, conversation_text: str, model="gpt-4.1") -> str:
    base_os = safe_load_text(os.path.join(DOCS_DIR, "base_os_rules_a.md"))
    proj_def = safe_load_text(os.path.join(DOCS_DIR, "project_definition_a.md"))
    proj_stat = safe_load_text(os.path.join(DOCS_DIR, "project_status.md"))

    doc_path = os.path.join(DOCS_DIR, doc_name)
    if not os.path.exists(doc_path):
        return f"※ 指定のドキュメントが見つかりません: {doc_name}"

    with open(doc_path, "r", encoding="utf-8") as f:
        current_doc = f.read()

    system_prompt = (
        base_os
        + "\n\n【プロジェクト定義】\n" + proj_def
        + "\n\n【現状】\n" + (proj_stat if proj_stat.strip() else "（情報なし）")
        + "\n\nあなたはプロジェクトドキュメント更新AI（Ariade A）です。"
          "以下の会話内容とドキュメントを比較し、必要な修正案をMarkdown形式で提案してください。"
    )

    user_prompt = f"""
[会話ログ]
{conversation_text}

[現在のドキュメント: {doc_name}]
{current_doc}
"""

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.0
    )
    return response.choices[0].message.content
