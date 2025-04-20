# app.py  –  Kai (Streamlit Cloud)

import streamlit as st
import openai
import os
import subprocess
from datetime import datetime
from zoneinfo import ZoneInfo          # ← JST 時刻用
from dotenv import load_dotenv

# ────────────────────────────────
# 認証キー & トークン
# ────────────────────────────────
load_dotenv()                                          # .env があれば読む
openai.api_key = (
    st.secrets.get("OPENAI_API_KEY")                   # Cloud 優先
    or os.getenv("OPENAI_API_KEY")                     # ローカル用
)
github_token = (
    st.secrets.get("GITHUB_TOKEN")
    or os.getenv("GITHUB_TOKEN")
)

# ────────────────────────────────
# パス類
# ────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOCS_DIR = os.path.join(BASE_DIR, "docs")
CONV_DIR = os.path.join(BASE_DIR, "conversations")
os.makedirs(CONV_DIR, exist_ok=True)

# ────────────────────────────────
# 会話ログ（JSTで 1 日 1 ファイル）
# ────────────────────────────────
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

# ────────────────────────────────
# System プロンプト
# ────────────────────────────────
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

【プロジェクト現状】
{status if status.strip() else "（現在のステータス情報はありません）"}
"""

# ────────────────────────────────
# Git   pull --rebase → add → commit → push
# ────────────────────────────────
def try_git_commit(file_path: str) -> None:
    if not github_token:          # トークン無ければ何もしない
        return
    try:
        subprocess.run(
            ["git", "config", "--global", "user.name", "Kai Bot"],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        subprocess.run(
            ["git", "config", "--global", "user.email", "kai@example.com"],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        # ① 最新を取得（rebase）
        subprocess.run(
            ["git", "pull", "--rebase", "origin", "main"],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        # ② 追加 & コミット
        subprocess.run(["git", "add", file_path], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(
            ["git", "commit", "-m", f"Update log: {os.path.basename(file_path)}"],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        # ③ Push
        subprocess.run(
            ["git", "push",
             f"https://{github_token}@github.com/HirakuArai/vpm-ariade.git"],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
    except subprocess.CalledProcessError:
        pass   # 衝突時などは無視（Cloud ログには出ない）

# ────────────────────────────────
# Streamlit UI
# ────────────────────────────────
st.set_page_config(page_title="Kai - VPMアシスタント", page_icon="🧠")
st.title("🧵 Virtual Project Manager - Kai")
st.write("プロジェクトについて何でも聞いてください。")

history = load_conversation_messages()
for m in history:
    with st.chat_message("user" if m["role"] == "user" else "assistant",
                         avatar="🙋‍♂️" if m["role"] == "user" else "🧠"):
        st.markdown(m["content"])

user_input = st.chat_input("あなたの発言")

if user_input:
    # ユーザ発話
    with st.chat_message("user", avatar="🙋‍♂️"):
        st.markdown(user_input)
    append_to_log("USER", user_input)

    # OpenAI へ
    messages = [{"role": "system", "content": get_system_prompt()}] + \
               history + \
               [{"role": "user", "content": user_input}]

    response = openai.ChatCompletion.create(
        model="gpt-4.1",
        messages=messages
    )
    reply = response.choices[0].message.content

    # AI 返答
    with st.chat_message("assistant", avatar="🧠"):
        st.markdown(reply)
    append_to_log("KAI", reply)
