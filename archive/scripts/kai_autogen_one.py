import os
import sys
import json
from openai import OpenAI

# パス設定修正：scripts/配下をimportできるように
sys.path.append("scripts")
from next_task_selector import select_next_task

CORE_DIR = "core"
PATCH_DIR = "patches"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

SYSTEM_PROMPT = """
あなたはプロジェクトマネージャーAI Kai の機能拡張エンジニアです。

以下の機能IDに基づいて、Kai が使用する Python 関数のスケルトンを作成してください。

要件：
- docstring はすべて日本語で記述してください
- 引数・戻り値・使い方の例を含めて丁寧に記述
- 実装本体は `pass` のままで構いません
- 出力は Markdownコードブロック（```python）を含まない形で返してください
"""

def extract_python_code_block(text):
    if "```python" in text:
        return text.split("```python")[1].split("```")[0].strip()
    return text.strip()

def request_skeleton(cap_id):
    prompt = f"機能ID: {cap_id} に対応する Kai の関数スケルトンを作ってください。"
    response = client.chat.completions.create(
        model="gpt-4.1",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3
    )
    return response.choices[0].message.content.strip()

def write_stub_file(cap_id, code_text):
    os.makedirs(CORE_DIR, exist_ok=True)
    filepath = os.path.join(CORE_DIR, f"{cap_id}.py")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(code_text)
    print(f"✅ スケルトンを保存: {filepath}")
    return filepath

def write_patch_file(cap_id, priority, reason):
    os.makedirs(PATCH_DIR, exist_ok=True)
    patch_path = os.path.join(PATCH_DIR, f"{cap_id}_capability.json")
    patch = {
        "id": cap_id,
        "name": cap_id.replace("_", " ").title(),
        "description": reason,
        "priority": priority,
        "requires_confirm": True,
        "enabled": True
    }
    with open(patch_path, "w", encoding="utf-8") as f:
        json.dump(patch, f, indent=2, ensure_ascii=False)
    print(f"📦 パッチ案を保存: {patch_path}")
    return patch_path

def main():
    next_task = select_next_task()
    if not next_task:
        print("🎉 すべての必要能力が実装済みです！")
        return

    cap_id = next_task["id"]
    priority = next_task["priority"]
    reason = next_task["reason"]

    print(f"🧠 GPTに依頼中: {cap_id}（優先度: {priority}）")
    raw_code = request_skeleton(cap_id)
    clean_code = extract_python_code_block(raw_code)

    print("\n📄 生成スケルトン:\n")
    print(clean_code)

    write_stub_file(cap_id, clean_code)
    write_patch_file(cap_id, priority, reason)

if __name__ == "__main__":
    main()
