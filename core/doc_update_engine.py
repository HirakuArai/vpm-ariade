# core/doc_update_engine.py

import os
import subprocess
from datetime import datetime

import openai

from dotenv import load_dotenv

from core.log_utils import messages_to_text

load_dotenv()  # ← ここで .env を読み込む

# ───────────────────────────────
# OpenAIクライアント初期化（より堅牢に）
# ───────────────────────────────
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise RuntimeError("❗ OPENAI_API_KEY is not set in the environment. Please check your .env file.")
# client = OpenAI(api_key=api_key)

# ───────────────────────────────
# パス設定
# ───────────────────────────────
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DOCS_DIR = os.path.join(BASE_DIR, "docs")

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

def update_doc_with_gpt(doc_name: str, conversation_text: str, auto_approve=False):
    """
    GPTによる修正文提案 → ユーザー承認 → ファイル更新 → Gitコミット
    """
    print(f"📄 対象ドキュメント: {doc_name}")
    print("🔄 GPTに修正文を問い合わせ中...")

    proposal = propose_doc_update(doc_name, conversation_text)

    print("=== GPTによる修正提案 ===")
    print(proposal)
    print("──────────────────────")

    if not auto_approve:
        choice = input("この修正を適用しますか？ (yes/no): ")
        if choice.strip().lower() not in ["yes", "y"]:
            print("🚫 更新をキャンセルしました。")
            return

    apply_update(doc_name, proposal, auto_approve=True)

def apply_update(doc_name: str, new_content: str, auto_approve=False):
    """
    GPTが生成したMarkdown内容をファイルに反映し、Gitコミットする
    """
    target_path = os.path.join(DOCS_DIR, doc_name)
    if not os.path.exists(target_path):
        print(f"※ 指定のドキュメントが存在しません: {target_path}")
        return

    print("=== 以下の内容でドキュメントを更新します ===")
    print(new_content)
    print("======================================")

    if not auto_approve:
        choice = input("この内容で更新してよろしいですか？(yes/no): ")
        if choice.strip().lower() not in ["yes", "y"]:
            print("キャンセルしました。ファイルは更新されません。")
            return

    # ファイル更新
    with open(target_path, "w", encoding="utf-8") as f:
        f.write(new_content)
    print(f"※ ファイルを更新しました: {target_path}")

    # Gitコミット
    commit_msg = f"update: {doc_name} via GPT apply_update ({datetime.now().strftime('%Y-%m-%d')})"
    try:
        subprocess.run(["git", "-C", BASE_DIR, "add", target_path], check=True)
        subprocess.run(["git", "-C", BASE_DIR, "commit", "-m", commit_msg], check=True)
        print(f"✅ Gitコミット完了: {commit_msg}")
    except subprocess.CalledProcessError as e:
        print("❗ Git操作中にエラーが発生しました:", e)