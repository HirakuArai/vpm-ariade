import openai
import os
from dotenv import load_dotenv
load_dotenv()


openai.api_key = os.getenv("OPENAI_API_KEY")  # .env に保存されていること前提

SYSTEM_PROMPT = """あなたはPython開発に精通したアシスタントです。
以下の機能IDが示す Kai に必要な機能について、日本語でその役割・目的を説明し、
Kai の core/ ディレクトリに追加すべき関数スケルトンを出力してください。

制約:
- docstring を詳細に記述すること
- 関数名は機能IDに準拠
- 実装は未完成で構いません。`pass` でOKです。
"""

def request_capability_skeleton(capability_id):
    user_prompt = f"必要な機能ID: {capability_id}"
    print(f"🧠 GPTへ問い合わせ中: {capability_id}")

    client = openai.OpenAI()

    response = client.chat.completions.create(
        model="gpt-4-1106-preview",  # または "gpt-4.1"（動作すればOK）
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.3
    )

    reply = response.choices[0].message.content.strip()
    print("\n📄 提案されたスケルトン:\n")
    print(reply)

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("❗ 実行方法: python scripts/gpt_generate_capability.py <機能ID>")
        exit(1)

    capability_id = sys.argv[1]
    request_capability_skeleton(capability_id)
