from datetime import datetime, timedelta
import os
import json
from core.capabilities_registry import kai_capability

LOG_DIR = "logs"

@kai_capability(
    id="get_yesterday_log_filename",
    name="昨日のログファイル取得",
    description="この機能はKaiが前日のログファイルの名前を取得する能力を実現します。主にデバッグやトラブルシューティングに役立つ情報を提供します。",
    requires_confirm=False,
    enabled=True
)
def get_yesterday_log_filename():
    yesterday = datetime.now() - timedelta(days=1)
    return yesterday.strftime("%Y-%m-%d") + ".log"

@kai_capability(
    id="load_yesterdays_log_as_messages",
    name="昨日のログをメッセージとして読み込む",
    description="この関数は昨日のログを取得し、メッセージとして形成して読み込む能力を提供します。これにより、Kaiは過去のデータを利用してより適応的な対話を行うことが可能となります。",
    requires_confirm=False,
    enabled=True
)
def load_yesterdays_log_as_messages():
    log_path = os.path.join(LOG_DIR, get_yesterday_log_filename())
    if not os.path.exists(log_path):
        return []

    with open(log_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    messages = []
    for line in lines:
        try:
            entry = json.loads(line)
            if "role" in entry and "content" in entry:
                messages.append(entry)
        except json.JSONDecodeError:
            continue
    return messages

@kai_capability(
    id="messages_to_text",
    name="メッセージのテキスト変換",
    description="Kaiは、この機能を用いて引数として渡されたメッセージをテキスト形式に変換します。具体的には、インプットとして受け取ったメッセージを適切な形式のテキストデータに編集・変換する機能を持っています。",
    requires_confirm=False,
    enabled=True
)
def messages_to_text(messages):
    text = ""
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content", "")
        text += f"{role.upper()}: {content}\n"
    return text.strip()
