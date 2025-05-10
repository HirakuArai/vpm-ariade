import tiktoken
from app import get_system_prompt

encoding = tiktoken.encoding_for_model("gpt-4")
prompt = get_system_prompt()
tokens = encoding.encode(prompt)

print(f"🔢 プロンプトのトークン数: {len(tokens)}")
