import json
import os
import openai
from dotenv import load_dotenv

PATCH_PATH = "kai_capabilities_patch.json"
OUTPUT_PATH = "kai_capabilities_completion.json"
MODEL = "gpt-4"

def load_json(path):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(data, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def call_gpt_capability_completion(item):
    prompt = f"""
以下はAIエージェントKaiに未登録の関数定義です。
関数ID: {item['id']}
ファイル: {item['source_file']}
引数: {', '.join(item['args']) if item['args'] else 'なし'}

この関数がKaiのどのような能力を実現するかを推測し、以下の形式で出力してください：
- name: Kaiの能力名（日本語）
- description: 具体的な機能説明（日本語、1文〜2文）
"""
    response = openai.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "あなたはKaiというAIエージェントの能力管理支援AIです。"},
            {"role": "user", "content": prompt.strip()}
        ]
    )
    content = response.choices[0].message.content
    return parse_completion_response(content, item)

def parse_completion_response(text, item):
    lines = text.strip().split("\n")
    name = ""
    description = ""
    for line in lines:
        if line.startswith("- name:"):
            name = line.replace("- name:", "").strip()
        elif line.startswith("- description:"):
            description = line.replace("- description:", "").strip()
    item["name"] = name or item["name"]
    item["description"] = description or item["description"]
    return item

def main():
    load_dotenv()
    patch = load_json(PATCH_PATH)
    results = []
    for item in patch:
        try:
            completed = call_gpt_capability_completion(item)
            results.append(completed)
        except Exception as e:
            print(f"Error: {e} on {item['id']}")
    save_json(results, OUTPUT_PATH)
    print(f"Saved completed capabilities to {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
