# app.py  –  Kai (Streamlit Cloud)

import streamlit as st
import openai
import os
import subprocess
import json
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

# ──────────────────────────────────────────
# 認証キー & トークン
# ──────────────────────────────────────────
load_dotenv()
openai.api_key = st.secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
github_token = st.secrets.get("GITHUB_TOKEN") or os.getenv("GITHUB_TOKEN")

# ──────────────────────────────────────────
# パス類
# ──────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOCS_DIR = os.path.join(BASE_DIR, "docs")
CONV_DIR = os.path.join(BASE_DIR, "conversations")
FLAG_PATH = os.path.join(BASE_DIR, "check_flags", "processed_logs.json")
os.makedirs(CONV_DIR, exist_ok=True)
os.makedirs(os.path.dirname(FLAG_PATH), exist_ok=True)

# ──────────────────────────────────────────
# 会話ログ
# ──────────────────────────────────────────
def get_today_log_path() -> str:
    today = datetime.now(ZoneInfo("Asia/Tokyo")).strftime("%Y%m%d")
    return os.path.join(CONV_DIR, f"conversation_{today}.md")

def append_to_log(role: str, content: str) -> None:
    ts = datetime.now(ZoneInfo("Asia/Tokyo")).strftime("%Y-%m-%d %H:%M:%S")
    path = get_today_log_path()
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"## {ts} [ROLE: {role}]\n{content.strip()}\n\n")
    try_git_commit(path)

def load_conversation_messages():
    path = get_today_log_path()
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
    return f"""{overview}

{base_rules}

【プロジェクト定義】
{definition}

【現在のステータス】
{status if status.strip() else "（現在のステータス情報はありません）"}
"""

# ──────────────────────────────────────────
# Git: 安全にpull → commit → push
# ──────────────────────────────────────────
def try_git_pull_safe():
    try:
        subprocess.run(["git", "stash", "--include-untracked"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        result = subprocess.run(
            ["git", "pull", "--rebase", "https://github.com/HirakuArai/vpm-ariade.git"],
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
# 会話ログの確認処理
# ──────────────────────────────────────────
def check_unprocessed_logs():
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
# Streamlit UI
# ──────────────────────────────────────────
st.set_page_config(page_title="Kai - VPMアシスタント", page_icon="🧠")
st.title("🧵 Virtual Project Manager - Kai")
st.caption("バージョン: 2025-04-20 JST対応 + gpt-4.1対応 + 安全Git pull実装_2")
st.write("プロジェクトについて何でも聞いてください。")

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
