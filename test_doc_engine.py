from dotenv import load_dotenv
import openai
from core import log_utils, doc_update_engine

load_dotenv()  # .env から OPENAI_API_KEY 読み込み

messages = log_utils.load_yesterdays_log_as_messages()
if not messages:
    print("❗昨日の会話ログが見つからないか、空です。")
else:
    conversation_text = log_utils.messages_to_text(messages)
    doc_name = "project_definition.md"  # テスト対象
    result = doc_update_engine.propose_doc_update(doc_name, conversation_text, model="gpt-4.1")
    print("\n=== 提案された修正文 ===")
    print(result)
