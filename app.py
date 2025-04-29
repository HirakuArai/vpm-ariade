# app.py  –  Kai (Streamlit Cloud)

# ──────────────────────────────────────────
# 必要なライブラリ import（すべて先頭に集約）
# ──────────────────────────────────────────
import os
import json
import subprocess
from datetime import datetime
from zoneinfo import ZoneInfo
import pytz
import streamlit as st
import openai
from dotenv import load_dotenv

from core.capabilities_registry import kai_capability

# ──────────────────────────────────────────
# 開発モード設定
# ──────────────────────────────────────────
DEVELOPMENT_MODE = False  # 本番デプロイ時はFalseに変更

# ──────────────────────────────────────────
# 認証キー & パス
# ──────────────────────────────────────────
import os
from dotenv import load_dotenv
import streamlit as st

# 環境変数ロード
load_dotenv()

# 認証キー安全取得
openai_api_key = os.getenv("OPENAI_API_KEY")
github_token = os.getenv("GITHUB_TOKEN")

# secrets.tomlが存在すれば読む（ローカル環境対策）
try:
    if hasattr(st, "secrets") and st.secrets:
        openai_api_key = openai_api_key or st.secrets.get("OPENAI_API_KEY", None)
        github_token = github_token or st.secrets.get("GITHUB_TOKEN", None)
except Exception:
    pass

openai.api_key = openai_api_key

# パス類
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOCS_DIR = os.path.join(BASE_DIR, "docs")
CONV_DIR = os.path.join(BASE_DIR, "conversations")
FLAG_PATH = os.path.join(BASE_DIR, "check_flags", "processed_logs.json")

# 必須フォルダ作成
os.makedirs(CONV_DIR, exist_ok=True)
os.makedirs(os.path.dirname(FLAG_PATH), exist_ok=True)

# ──────────────────────────────────────────
# 会話ログ処理系 関数定義
# ──────────────────────────────────────────

def get_today_log_path() -> tuple:
    try:
        tokyo = pytz.timezone('Asia/Tokyo')
        today = datetime.now(tokyo)
        date_str = today.strftime('%Y-%m-%d')
        log_directory = "logs"
        os.makedirs(log_directory, exist_ok=True)
        log_path = f"{log_directory}/{date_str}.log"
        return date_str, log_path
    except Exception as e:
        print(f"❌ get_today_log_path() でエラー: {e}", flush=True)
        return "unknown", "logs/unknown.log"

@kai_capability(
    id="append_log",
    name="会話ログを保存",
    description="ユーザーとの会話内容をログファイルに記録します。",
    requires_confirm=False
)

def append_to_log(role: str, content: str) -> None:
    ts = datetime.now(ZoneInfo("Asia/Tokyo")).strftime("%Y-%m-%d %H:%M:%S")
    _, path = get_today_log_path()
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"## {ts} [ROLE: {role}]\n{content.strip()}\n\n")
    try_git_commit(path)

@kai_capability(
    id="load_log",
    name="会話ログを読み込む",
    description="保存された過去の会話ログを読み込みます。",
    requires_confirm=False
)

def load_conversation_messages():
    _, path = get_today_log_path()
    if not os.path.exists(path):
        return []
    msgs, cur_role, buf = [], None, []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if line.startswith("## "):
                if cur_role and buf:
                    msgs.append({
                        "role": "user" if cur_role == "USER" else "assistant",
                        "content": "\n".join(buf)
                    })
                buf = []
                if "[ROLE: " in line:
                    cur_role = line.split("[ROLE: ")[1].split("]")[0]
            else:
                buf.append(line)
    if cur_role and buf:
        msgs.append({
            "role": "user" if cur_role == "USER" else "assistant",
            "content": "\n".join(buf)
        })
    return msgs

def check_unprocessed_logs():
    """未処理の会話ログファイルをチェックしてGit管理する"""
    print("🧪 check_unprocessed_logs() 開始", flush=True)
    try:
        print("🔍 check_unprocessed_logs: start", flush=True)
        if os.path.exists(FLAG_PATH):
            with open(FLAG_PATH, "r", encoding="utf-8") as f:
                flags = json.load(f)
        else:
            flags = {}

        files = sorted(f for f in os.listdir(CONV_DIR)
                       if f.startswith("conversation_") and f.endswith(".md"))

        updated = False
        for file in files:
            if file not in flags:
                print(f"🟡 未処理ログ検出: {file}", flush=True)
                flags[file] = "checked"
                updated = True

        if updated:
            print("📂 フラグを保存します", flush=True)
            with open(FLAG_PATH, "w", encoding="utf-8") as f:
                json.dump(flags, f, ensure_ascii=False, indent=2)
            print("📁 保存内容:", flags, flush=True)
            try_git_commit(FLAG_PATH)
        else:
            print("✅ すべてのログが処理済みです", flush=True)

    except Exception as e:
        print(f"❌ check_unprocessed_logs エラー: {e}", flush=True)

# ──────────────────────────────────────────
# System プロンプト
# ──────────────────────────────────────────
def read_file(path: str) -> str:
    return open(path, encoding="utf-8").read() if os.path.exists(path) else ""


def get_system_prompt() -> str:
    overview   = read_file(os.path.join(DOCS_DIR, "architecture_overview.md"))
    base_rules = read_file(os.path.join(DOCS_DIR, "base_os_rules.md"))
    definition = read_file(os.path.join(DOCS_DIR, "project_definition.md"))
    status     = read_file(os.path.join(DOCS_DIR, "project_status.md"))

    # ── NEW: kai_capabilities.json ─────────────────
    caps_path = os.path.join(DOCS_DIR, "kai_capabilities.json")
    caps = []
    if os.path.exists(caps_path):
        import json
        with open(caps_path, "r", encoding="utf-8") as f:
            caps = json.load(f)

    caps_text = "\n".join(
        f"- **{c.get('name','')}**: {c.get('description','')}"
        + (" (要承認)" if c.get('requires_confirm') else "")
        for c in caps if c.get("enabled", True)
    ) or "（能力リストがまだ登録されていません）"
    # ──────────────────────────────────────────────

    return f"""{overview}

{base_rules}

【プロジェクト定義】
{definition}

【現在のステータス】
{status if status.strip() else "（現在のステータス情報はありません）"}

【Kai Capabilities】
{caps_text}
"""

# ──────────────────────────────────────────
# Git: 安全にpull → commit → push
# ──────────────────────────────────────────
def try_git_pull_safe():
    try:
        subprocess.run(["git", "stash", "--include-untracked"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        repo_url_with_token = f"https://{github_token}@github.com/HirakuArai/vpm-ariade.git"
        result = subprocess.run(
            ["git", "pull", "--rebase", repo_url_with_token],
            check=False,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            print(f"❌ Git pull失敗: {result.stderr.strip()}", flush=True)
        else:
            print("✅ 安全にGit pull完了", flush=True)
        subprocess.run(["git", "stash", "pop"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError as e:
        print(f"❌ Git pull時の例外: {e}", flush=True)

def try_git_commit(file_path: str) -> None:
    if not github_token:
        return
    try:
        print(f"📌 Gitコミット開始: {file_path}", flush=True)
        subprocess.run(["git", "config", "--global", "user.name", "Kai Bot"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["git", "config", "--global", "user.email", "kai@example.com"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["git", "add", file_path], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["git", "commit", "-m", f"Update log: {os.path.basename(file_path)}"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["git", "push", f"https://{github_token}@github.com/HirakuArai/vpm-ariade.git"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError as e:
        print(f"❌ Git push失敗: {e}", flush=True)

# ──────────────────────────────────────────
# Streamlit UI（Kai モード切り替え統合版）
# ──────────────────────────────────────────
st.set_page_config(page_title="Kai - VPMアシスタント", page_icon="🧠")
st.title("🧵 Virtual Project Manager - Kai")
st.caption("バージョン: 2025-04-25 Kai修正文提案機能をUI統合")
st.write("プロジェクトについて何でも聞いてください。")

from core.code_analysis import extract_functions
from core.patch_log import load_patch_history, show_patch_log
from core import log_utils, doc_update_engine
from core.tagging import generate_tags  # 🆕 追加

# モード切り替え
mode = st.sidebar.radio("📂 モード選択", ["チャット", "関数修正", "ドキュメント更新"])

if mode == "チャット":
    if not DEVELOPMENT_MODE:
        try_git_pull_safe()
    check_unprocessed_logs()
    history = load_conversation_messages()
    for m in history:
        with st.chat_message("user" if m["role"] == "user" else "assistant", avatar="👋" if m["role"] == "user" else "🧠"):
            st.markdown(m["content"])
    user_input = st.chat_input("あなたの発言")
    if user_input:
        with st.chat_message("user", avatar="👋"):
            st.markdown(user_input)
        append_to_log("USER", user_input)
        messages = [{"role": "system", "content": get_system_prompt()}] + history + [{"role": "user", "content": user_input}]
        response = openai.ChatCompletion.create(model="gpt-4.1", messages=messages)
        reply = response.choices[0].message.content
        with st.chat_message("assistant", avatar="🧠"):
            st.markdown(reply)
        append_to_log("KAI", reply)

elif mode == "関数修正":
    st.divider()
    st.subheader("🛠 Kai 自己改修：関数選択モード")
    function_list = extract_functions("app.py") + extract_functions("core/doc_update_engine.py")
    function_labels = [f"{f['name']} ({', '.join(f['args'])}) @ L{f['lineno']}" for f in function_list]
    selected_func_label = st.selectbox("🔧 修正したい関数を選んでください", function_labels)
    user_instruction = st.text_area("📝 修正したい内容を具体的に記入してください")
    if st.button("💡 GPTに修正案を生成させる"):
        selected = function_list[function_labels.index(selected_func_label)]
        with open("app.py", encoding="utf-8") as f:
            lines = f.readlines()
        fn_source = "".join(lines[selected["lineno"] - 1 : selected.get("end_lineno", selected["lineno"] + 5)])
        system_prompt = "あなたはプロジェクトKaiのコード修正補助AIです。以下の関数について、ユーザーの指示をもとに改良案を提案してください。"
        user_prompt = f"# 修正対象の関数\n```python\n{fn_source}\n```\n# ユーザーの指示\n{user_instruction}\n# 提案内容を Markdown形式で記述してください。"
        response = openai.ChatCompletion.create(
            model="gpt-4.1",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )
        proposal = response.choices[0].message["content"]
        st.session_state["fn_proposal"] = proposal
        st.session_state["fn_selected"] = selected["name"]
        st.session_state["fn_instruction"] = user_instruction
        st.markdown("### 💬 修正提案（Kaiから）")
        st.code(proposal, language="markdown")

    fn_selected = st.session_state.get("fn_selected")
    if st.session_state.get("fn_proposal") and fn_selected:
        st.subheader("🔧 GPTの提案を適用する")
        if st.button("💾 修正をapp.pyに反映＋Gitコミット"):
            from core.kai_patch_applier import apply_gpt_patch
            success = apply_gpt_patch(
                markdown_text=st.session_state["fn_proposal"],
                fn_name=fn_selected,
                source_path="app.py",
                auto_commit=True
            )
            if success:
                st.success(f"✅ 関数 `{fn_selected}` を更新しました！")
                st.toast("💾 修正内容が履歴に保存されました", icon="📜")
                st.balloons()
            else:
                st.error(f"❌ 関数 `{fn_selected}` の更新に失敗しました。")

    st.divider()
    st.subheader("📜 差分履歴ログ（自動保存）")
    history_data = load_patch_history()
    if not history_data:
        st.info("まだパッチ履歴がありません。")
    else:
        for entry in reversed(history_data):
            with st.expander(f"🕒 {entry['timestamp']} | 関数: {entry['function']}"):
                st.markdown(f"**指示内容**:\n```\n{entry['instruction']}\n```")
                st.markdown(f"**提案された修正**:\n```markdown\n{entry['diff']}\n```")

        st.divider()
        show_patch_log()

elif mode == "ドキュメント更新":
    st.header("🧠 ドキュメント更新提案（Kai）")
    md_files = [f for f in os.listdir(DOCS_DIR) if f.endswith(".md")]
    doc_name = st.selectbox("更新対象のドキュメントを選択", md_files)
    if st.button("🔍 GPTで修正提案を確認"):
        messages = log_utils.load_yesterdays_log_as_messages()
        if not messages:
            st.warning("昨日の会話ログが見つからない、または空です。")
        else:
            conv_text = log_utils.messages_to_text(messages)
            with st.spinner("GPTが修正文を生成中..."):
                proposal = doc_update_engine.propose_doc_update(doc_name, conv_text)
            st.subheader("💡 GPT修正提案")
            st.code(proposal, language="diff")
            if st.button("✅ この修正を反映してGitコミット"):
                doc_update_engine.apply_update(doc_name, proposal, auto_approve=True)
                st.success("✅ コミット完了！")
    
    st.divider()
    st.header("🏷 ドキュメント自動タグ付けツール（Kai）")

    if st.button("🏷 選択中のドキュメントにタグを生成する"):
        with st.spinner("タグを生成中..."):
            content = read_file(os.path.join(DOCS_DIR, doc_name))
            tags = generate_tags(content)
            if tags:
                st.success(f"✅ タグ生成完了: {', '.join(tags)}")
                st.session_state["generated_tags"] = tags  # セッションに一時保存
            else:
                st.warning("⚠ タグを生成できませんでした。")

    # 🔥 タグ保存ボタン（上でタグ生成された場合のみ）
    if "generated_tags" in st.session_state and st.session_state["generated_tags"]:
        if st.button("💾 生成したタグをファイルに保存する"):
            from core.tagging import save_tags  # ここでimport（またはファイル先頭にまとめる）
            save_tags(doc_name, st.session_state["generated_tags"])
            st.success("✅ タグファイルを保存しました！")
            # ⬇ Gitに自動コミット！
            try_git_commit(os.path.join(DOCS_DIR, doc_name.replace(".md", ".tags")))

# ──────────────────────────────────────────
# 仮設：テスト用ボタン（discover_capabilities）
# ──────────────────────────────────────────
from core.discover_capabilities import discover_capabilities  # インポートも必須（まだならファイル頭で！）

st.divider()
st.subheader("🔍 Kai自己能力解析（テスト用）")

if st.sidebar.button("🔍 Discover Kai Capabilities (テスト)"):
    st.subheader("Kaiが自己解析した能力一覧（生データ）")
    capabilities = discover_capabilities()
    st.json(capabilities)

# ──────────────────────────────────────────
# 仮設：全関数AST走査ボタン
# ──────────────────────────────────────────

if st.sidebar.button("📜 AST 走査で関数一覧を出力"):
    st.subheader("🔍 Kaiが検出した関数一覧（decorated=Trueがcapability）")
    capabilities_full = discover_capabilities(full_scan=True)
    st.json(capabilities_full)

# ──────────────────────────────────────────
# 仮設：自己能力差分チェック（capabilities_diff）
# ──────────────────────────────────────────
from core.capabilities_diff import (
    load_ast_capabilities,
    load_json_capabilities,
    compare_capabilities,
    format_diff_for_output
)

if st.sidebar.button("🧪 Kai能力差分チェック（AST vs JSON）"):
    st.subheader("🧠 Kai 自己能力 差分チェック結果")
    ast_caps = load_ast_capabilities()
    json_caps = load_json_capabilities()
    diff = compare_capabilities(ast_caps, json_caps)
    formatted = format_diff_for_output(diff)
    st.markdown(formatted)
