# app.py
import streamlit as st
import openai
import os
import subprocess
from datetime import datetime
from dotenv import load_dotenv

# --- 認証キーのロード（Cloud / ローカル両対応） ---
load_dotenv()
openai.api_key = (
    st.secrets.get("OPENAI_API_KEY")
    or os.getenv("OPENAI_API_KEY")
    or "your-local-api-key"
)
github_token = (
    st.secrets.get("GITHUB_TOKEN")
    or os.getenv("GITHUB_TOKEN")
)

# --- パス設定 ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOCS_DIR = os.path.join(BASE_DIR, "docs")
CONV_DIR = os.path.join(BASE_DIR, "conversations")
os.makedirs(CONV_DIR, exist_ok=True)

# --- 会話ログファイル名（今日） ---
def get_today_log_path():
    today = datetime.now().strftime("%Y%m%d")
    return os.path.join(CONV_DIR, f"conversation_{today}.md")

# --- ログ保存処理 ---
def append_to_log(role: str, content: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    path = get_today_log_path()
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"## {timestamp} [ROLE: {role}]\n{content.strip()}\n\n")
    try_git_commit(path)

# --- ログ読み込み（Chat表示形式） ---
def load_conversation_messages():
    path = get_today_log_path()
    if not os.path.exists(path):
        return []
    messages = []
    current_role = None
    buffer = []

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("## "):
                if current_role and buffer:
                    messages.append({
                        "role": "user" if current_role == "USER" else "assistant",
                        "content": "\n".join(buffer)
                    })
                buffer = []
                if "[ROLE: " in line:
                    current_role = line.split("[ROLE: ")[1].split("]")[0]
            else:
                buffer.append(line)
    if current_role and buffer:
        messages.append({
            "role": "user" if current_role == "USER" else "assistant",
            "content": "\n".join(buffer)
        })
    return messages

# --- システムプロンプト構築 ---
def get_system_prompt():
    def read_file(path):
        return open(path, "r", encoding="utf-8").read() if os.path.exists(path) else ""
    base = read_file(os.path.join(DOCS_DIR, "base_os_rules.md"))
    definition = read_file(os.path.join(DOCS_DIR, "project_definition.md"))
    status = read_file(os.path.join(DOCS_DIR, "project_status.md"))
    return f"""{base}

【プロジェクト定義】
{definition}

【プロジェクト現状】
{status if status.strip() else "（現在のステータス情報はありません）"}
"""

# --- Git操作：自動コミット＋push ---
def try_git_commit(file_path: str):
    if not github_token:
        print("※ GitHubトークン未設定。Git操作はスキップされました。")
        return
    try:
        subprocess.run(["git", "add", file_path], check=True)
        subprocess.run(["git", "commit", "-m", f"Update log: {os.path.basename(file_path)}"], check=True)
        subprocess.run(["git", "push", f"https://{github_token}@github.com/HirakuArai/vpm-ariade.git"], check=True)
        print("✅ Git push 成功")
    except subprocess.CalledProcessError as e:
        print("⚠️ Gitエラー:", e)

# --- Streamlit UI ---
st.set_page_config(page_title="Kai - VPMアシスタント", page_icon="🧠")
st.title("🧵 Virtual Project Manager - Kai")
st.write("プロジェクトについて何でも聞いてください。")

# 会話ログを上に表示
history = load_conversation_messages()
for msg in history:
    with st.chat_message("user" if msg["role"] == "user" else "assistant", avatar="🙋‍♂️" if msg["role"] == "user" else "🧠"):
        st.markdown(msg["content"])

# 入力欄は一番下
user_input = st.chat_input("あなたの発言")

if user_input:
    with st.chat_message("user", avatar="🙋‍♂️"):
        st.markdown(user_input)
    append_to_log("USER", user_input)

    # 会話送信
    messages = [{"role": "system", "content": get_system_prompt()}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_input})

    response = openai.ChatCompletion.create(
        model="gpt-4.0-turbo",  # 必要に応じて変更
        messages=messages
    )
    reply = response.choices[0].message["content"]

    with st.chat_message("assistant", avatar="🧠"):
        st.markdown(reply)
    append_to_log("KAI", reply)
