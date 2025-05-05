import os
import json
import openai
import re
from dotenv import load_dotenv

# ───────────────────────────────────────
# scan_required_capabilities_gpt.py
# GPTを使って、Kaiに必要な能力（capability）をdocs/から推定
# ───────────────────────────────────────

DOCS_DIR = "docs"
CAP_PATH = "data/kai_capabilities.json"
OUTPUT_PATH = "data/needed_capabilities_gpt.json"
MODEL = "gpt-4.1"

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")


def load_docs():
    texts = []
    for file in os.listdir(DOCS_DIR):
        if file.endswith(".md"):
            with open(os.path.join(DOCS_DIR, file), encoding="utf-8") as f:
                texts.append(f.read())
    return "\n\n".join(texts)


def load_capabilities():
    with open(CAP_PATH, encoding="utf-8") as f:
        all_caps = json.load(f)
    return [f"- {cap['id']}: {cap['name']}\n  {cap['description']}" for cap in all_caps]


def call_gpt_analysis(doc_text, capabilities_text):
    prompt = f"""
以下はプロジェクトKaiに関する定義やルール、進捗に関するドキュメントです。
Kaiがプロジェクトマネージャーとして機能するために必要な能力を、下記の能力リストから選んでください。

# 能力一覧（capability list）:
{capabilities_text}

# ドキュメント内容:
{doc_text}

# 出力形式:
JSON形式で以下のように出力してください：
{{
  "role": "project_manager",
  "required_capabilities": ["capability_id1", "capability_id2", ...]
}}
"""

    response = openai.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "あなたはプロジェクトマネージャー支援AIです。Kaiに必要な能力を提案してください。"},
            {"role": "user", "content": prompt.strip()}
        ]
    )
    result = response.choices[0].message.content
    print("\n===== GPT OUTPUT =====\n")
    print(result)
    print("\n=======================\n")
    return result


def parse_json_response(text):
    try:
        # コードブロックを除去（```json ... ```）
        if text.startswith("```json"):
            text = text.strip().removeprefix("```json").removesuffix("```")
        # 行末コメントを除去
        text = re.sub(r"//.*", "", text)
        return json.loads(text)
    except Exception as e:
        print("❌ JSON parse error:", e)
        return {}


def main():
    doc_text = load_docs()
    caps_text = "\n".join(load_capabilities())
    gpt_output = call_gpt_analysis(doc_text, caps_text)
    parsed = parse_json_response(gpt_output)

    if parsed:
        os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
        with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(parsed, f, ensure_ascii=False, indent=2)
        print(f"✅ Generated: {OUTPUT_PATH} with {len(parsed['required_capabilities'])} capabilities.")
    else:
        print("⚠ GPT出力の解析に失敗しました。")


if __name__ == "__main__":
    main()