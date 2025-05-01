import os
import json
from openai import OpenAI

# パス設定
PRIORITY_PATH = "docs/capability_priorities.json"
CORE_DIR = "core"
PATCH_DIR = "patches"

# APIクライアント
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# GPTプロンプト
SYSTEM_PROMPT = """
あなたはプロジェクトマネージャーAI Kaiの能力拡張を支援するAIエンジニアです。

以下の機能IDに対して、Kai が使用する Python 関数のスケルトンを日本語で作成してください。

要件:
- 関数名は機能IDに準拠
- docstring（説明コメント）はすべて日本語で記述してください
- 引数、戻り値、想定される使い方を明記してください
- 実装内容は未完成（pass のままで構いません）
- コードブロックのマーク（```python など）は不要です
"""

def extract_python_code_block(text):
    if "```python" in text:
        return text.split("```python")[1].split("```")[0].strip()
    return text.strip()

def load_priorities():
    with open(PRIORITY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def request_skeleton(cap_id):
    user_prompt = f"機能ID: {cap_id}\nこの機能の目的を踏まえ、Kaiが使用するPythonスケルトン関数を1つ作成してください。"
    response = client.chat.completions.create(
        model="gpt-4-1106-preview",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.3
    )
    return response.choices[0].message.content.strip()

def save_skeleton_file(cap_id, code_text):
    os.makedirs(CORE_DIR, exist_ok=True)
    file_path = os.path.join(CORE_DIR, f"{cap_id}.py")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(code_text)
    print(f"✅ スケルトンを保存しました: {file_path}")
    return file_path

def save_capability_patch(cap_id, reason):
    os.makedirs(PATCH_DIR, exist_ok=True)
    patch_path = os.path.join(PATCH_DIR, f"{cap_id}_capability.json")
    patch = {
        "id": cap_id,
        "name": cap_id.replace("_", " ").title(),
        "description": reason,
        "requires_confirm": True,
        "enabled": True
    }
    with open(patch_path, "w", encoding="utf-8") as f:
        json.dump(patch, f, indent=2, ensure_ascii=False)
    print(f"📦 capabilities登録用の提案も保存しました: {patch_path}")

def main():
    priorities = load_priorities()
    sorted_items = sorted(priorities.items(), key=lambda x: {"high": 0, "medium": 1, "low": 2}[x[1]["priority"]])

    if not sorted_items:
        print("📭 優先度付き能力がありません。")
        return

    cap_id, meta = sorted_items[0]
    print(f"🧠 GPTにスケルトン生成を依頼中: {cap_id}")
    raw_code = request_skeleton(cap_id)
    clean_code = extract_python_code_block(raw_code)

    print("\n📄 生成結果:\n")
    print(clean_code)

    save_skeleton_file(cap_id, clean_code)
    save_capability_patch(cap_id, meta["reason"])

if __name__ == "__main__":
    main()
