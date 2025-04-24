from dotenv import load_dotenv
load_dotenv()  # .env から OPENAI_API_KEY を読み込む

from core import log_utils, doc_update_engine

# 昨日の会話ログを読み込む
messages = log_utils.load_yesterdays_log_as_messages()
if not messages:
    print("❗昨日の会話ログが見つからないか、空です。")
else:
    conversation_text = log_utils.messages_to_text(messages)
    doc_name = "project_definition.md"

    # 提案→承認→反映まで一括実行
    doc_update_engine.update_doc_with_gpt(doc_name, conversation_text)
