# core/doc_update_engine.py

import os
import subprocess
from datetime import datetime

import openai

from dotenv import load_dotenv

from core.log_utils import messages_to_text
from core.capabilities_registry import kai_capability

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

@kai_capability(
    id="safe_load_text",
    name="テキストファイル安全読み込み",
    description="Kaiは、指定したパスにあるテキストファイルを安全に読み込むことができます。この機能は、ファイルが存在し読み込み可能な場合のみ実行され、エラーハンドリングも含まれています。",
    requires_confirm=False,
    enabled=True
)
def safe_load_text(path: str) -> str:
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return ""

@kai_capability(
    id="propose_doc_update",
    name="ドキュメント修正提案",
    description="ユーザーとの会話内容をもとにドキュメント修正案を生成します。指定されたドキュメントと会話ログに基づき、Kaiは修正文案をGPTに問い合わせて提案します。",
    requires_confirm=False,
    enabled=True
)
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

@kai_capability(
    id="update_doc_with_gpt",
    name="文書自動更新",
    description="Kaiが指定した文書名の文書を、会話テキストを用いて自動的に更新する能力を実現します。オプションの自動承認機能を用いて、更新内容の自動承認を行うことも可能です。",
    requires_confirm=False,
    enabled=True
)
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

import difflib
import json
from core.capabilities_registry import kai_capability  # 未追加ならファイル上部に追加

@kai_capability(
    id="apply_update",
    name="ドキュメント更新機能",
    description="この機能は指定されたドキュメント名（doc_name）の内容を新しい内容（new_content）で更新します。自動承認オプション（auto_approve）が設定されている場合、更新が即座に反映されます。",
    requires_confirm=False,
    enabled=True
)
def apply_update(doc_name: str, new_content: str, auto_approve=False):
    """
    GPTが生成したMarkdown内容をファイルに反映し、Gitコミット＋patch_log.jsonに差分履歴を記録する
    """
    target_path = os.path.join(DOCS_DIR, doc_name)
    if not os.path.exists(target_path):
        print(f"※ 指定のドキュメントが存在しません: {target_path}")
        return

    # 旧内容の読み込み
    with open(target_path, "r", encoding="utf-8") as f:
        old_content = f.read()

    if old_content == new_content:
        print("内容に変更がないため、更新は行われません。")
        return

    # 差分生成（unified形式）
    diff = list(difflib.unified_diff(
        old_content.splitlines(),
        new_content.splitlines(),
        fromfile=f'a/{doc_name}',
        tofile=f'b/{doc_name}',
        lineterm=''
    ))
    diff_text = "\n".join(diff)

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

    # patch_log.json に履歴を追記
    patch_log_path = os.path.join(DOCS_DIR, "patch_log.json")
    patch_entry = {
        "file": doc_name,
        "datetime": datetime.utcnow().isoformat() + "Z",
        "diff": diff_text
    }

    try:
        if os.path.exists(patch_log_path):
            with open(patch_log_path, "r", encoding="utf-8") as f:
                patch_log = json.load(f)
                if not isinstance(patch_log, list):
                    patch_log = []
        else:
            patch_log = []
    except Exception:
        patch_log = []

    patch_log.append(patch_entry)

    with open(patch_log_path, "w", encoding="utf-8") as f:
        json.dump(patch_log, f, ensure_ascii=False, indent=2)

    print(f"✅ {doc_name} を修正し、差分を patch_log.json に記録しました")

    # Gitコミット
    commit_msg = f"update: {doc_name} via GPT apply_update ({datetime.now().strftime('%Y-%m-%d')})"
    try:
        subprocess.run(["git", "-C", BASE_DIR, "add", target_path], check=True)
        subprocess.run(["git", "-C", BASE_DIR, "add", patch_log_path], check=True)  # patch_log もコミット対象に
        subprocess.run(["git", "-C", BASE_DIR, "commit", "-m", commit_msg], check=True)
        print(f"✅ Gitコミット完了: {commit_msg}")
    except subprocess.CalledProcessError as e:
        print("❗ Git操作中にエラーが発生しました:", e)