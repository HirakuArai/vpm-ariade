# app.py
import streamlit as st
import openai
import os
from datetime import datetime
from dotenv import load_dotenv

# .envの読み込み
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# パス設定
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOCS_DIR = os.path.join(BASE_DIR, "docs")
CONV_DIR = os.path.join(BASE_DIR, "conversations")
os.makedirs(CONV_DIR, exist_ok=True)

# 今日のログファイルパス
def get_today_log_path():
    today = datetime.now().strftime("%Y%m%d")
    return os.path.join(CONV_DIR, f"conversation_{today}.md")

# ログに追記
def append_to_log(role: str, content: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(get_today_log_path(), "a", encoding="utf-8") as f:
        f.write(f"## {timestamp} [ROLE: {role}]\n{content.strip()}\n\n")

# ログをChat形式で読み込む
def load_conversation_messages():
    log_path = get_today_log_path()
    if not os.path.exists(log_path):
        return []

    messages = []
    current_role = None
    buffer = []

    with open(log_path, "r", encoding="utf-8") as f:
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

# systemプロンプト構築
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

# Streamlit UI
st.set_page_config(page_title="Kai - VPMアシスタント", page_icon="🧠")
st.title("🧵 Virtual Project Manager - Kai")
st.write("プロジェクトについて何でも聞いてください。")

user_input = st.text_input("💬 あなたの発言")

if user_input:
    # ログ読み込み & systemプロンプト付与
    messages = [{"role": "system", "content": get_system_prompt()}]
    messages.extend(load_conversation_messages())
    messages.append({"role": "user", "content": user_input})

    # OpenAI API呼び出し
    response = openai.ChatCompletion.create(
        model="gpt-4.1",
        messages=messages
    )
    reply = response.choices[0].message["content"]

    # 表示とログ保存
    st.markdown("#### ✨ Kaiの返答")
    st.markdown(reply)
    append_to_log("USER", user_input)
    append_to_log("KAI", reply)
