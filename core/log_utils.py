# core/log_utils.py

import os
from datetime import datetime, timedelta

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CONV_DIR = os.path.join(BASE_DIR, "conversations")

def get_yesterday_log_filename() -> str:
    yesterday = datetime.now() - timedelta(days=1)
    yday_str = yesterday.strftime("%Y%m%d")
    os.makedirs(CONV_DIR, exist_ok=True)
    return os.path.join(CONV_DIR, f"conversation_{yday_str}.md")

def load_yesterdays_log_as_messages() -> list:
    log_file = get_yesterday_log_filename()
    messages = []
    current_role = None
    content_buffer = []

    if not os.path.exists(log_file) or os.path.getsize(log_file) == 0:
        return []

    with open(log_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    for line in lines:
        line = line.rstrip("\n")
        if line.startswith("## "):
            if current_role and content_buffer:
                role_for_chat = "user" if current_role in ["USER", "KAI"] else "assistant"
                messages.append({"role": role_for_chat, "content": "\n".join(content_buffer)})
            content_buffer = []
            idx1, idx2 = line.find("["), line.find("]")
            if idx1 != -1 and idx2 != -1:
                role = line[idx1+1:idx2].replace("ROLE: ", "")
                current_role = role
        else:
            content_buffer.append(line)

    if current_role and content_buffer:
        role_for_chat = "user" if current_role in ["USER", "KAI"] else "assistant"
        messages.append({"role": role_for_chat, "content": "\n".join(content_buffer)})

    return messages

def messages_to_text(messages: list) -> str:
    return "\n".join(f"[{msg['role'].upper()}] {msg['content']}" for msg in messages)
