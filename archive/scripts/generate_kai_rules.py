import os
import json
import openai
from dotenv import load_dotenv

DOCS_DIR = "docs"
OUTPUT_PATH = "data/kai_rules.json"
MODEL = "gpt-4.1"

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")


def load_docs():
    contents = []
    for file in os.listdir(DOCS_DIR):
        if file.endswith(".md"):
            with open(os.path.join(DOCS_DIR, file), encoding="utf-8") as f:
                contents.append(f.read())
    return "\n\n".join(contents)


def call_gpt_for_rules(doc_text):
    prompt = f"""
以下は「プロジェクトKai」の定義・運用ルールに関するドキュメントです。
Kaiが「プロジェクトマネージャーAI」として活動する際に従うべき自己制御ルールを、次の形式のJSONで出力してください。

- Kaiが自分自身に対して適用すべき制約や判断基準
- 実行許可条件、禁止事項、承認要否などを含む
- `id`, `description`, `scope`, `severity`を含む構造

# ドキュメント内容:
{doc_text}

# 出力形式:
{{
  "version": "1.0",
  "rules": [
    {{
      "id": "rule_id",
      "description": "説明文",
      "scope": "対象領域（例：self_modification, document_update, git_ops など）",
      "severity": "low / medium / high"
    }},
    ...
  ]
}}
"""

    response = openai.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "あなたはプロジェクトマネジメントAI Kaiの監査ルールを定義する支援者です。"},
            {"role": "user", "content": prompt.strip()}
        ]
    )
    return response.choices[0].message.content


def parse_json_response(text):
    try:
        if text.startswith("```json"):
            text = text.strip().removeprefix("```json").removesuffix("```")
        import re
        text = re.sub(r"//.*", "", text)
        return json.loads(text)
    except Exception as e:
        print("❌ JSON parse error:", e)
        return {}


def main():
    doc_text = load_docs()
    gpt_output = call_gpt_for_rules(doc_text)
    print("\n===== GPT OUTPUT =====\n")
    print(gpt_output)
    print("\n=======================\n")
    parsed = parse_json_response(gpt_output)
    if parsed:
        os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
        with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(parsed, f, ensure_ascii=False, indent=2)
        print(f"✅ Generated: {OUTPUT_PATH} with {len(parsed['rules'])} rules.")
    else:
        print("⚠ 解析失敗。")


if __name__ == "__main__":
    main()
