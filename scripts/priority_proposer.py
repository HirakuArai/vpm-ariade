import os
import json
import datetime
from openai import OpenAI
from capability_diff import find_missing_capabilities

# ✅ APIキー取得
openai_api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=openai_api_key)

# ✅ GPT用プロンプト（日本語・堅め）
SYSTEM_PROMPT = """
あなたはプロジェクトマネージャーAI Kaiです。
以下の機能ID一覧は、現在プロジェクトに不足している能力です。

プロジェクトの目的、構成、ルールを考慮し、それぞれの機能が
どの程度重要か（high / medium / low）を判断してください。

各能力について以下の形式でJSONで出力してください：

{
  "capability_id": {
    "priority": "high",
    "reason": "この機能が無いと進行に支障が出るため"
  },
  ...
}
"""

def propose_priorities(capability_ids):
    user_prompt = f"不足能力一覧: {capability_ids}"
    response = client.chat.completions.create(
        model="gpt-4-1106-preview",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.4
    )
    return response.choices[0].message.content.strip()

def save_outputs(json_obj):
    os.makedirs("docs", exist_ok=True)
    os.makedirs("logs", exist_ok=True)

    # 最新版保存
    with open("docs/capability_priorities.json", "w", encoding="utf-8") as f:
        json.dump(json_obj, f, indent=2, ensure_ascii=False)

    # 履歴ログ保存
    today = datetime.date.today().isoformat()
    log_path = f"logs/capability_priority_log_{today}.md"
    with open(log_path, "w", encoding="utf-8") as f:
        f.write(f"# 優先度判定ログ（{today}）\n\n")
        for cap_id, entry in json_obj.items():
            f.write(f"## {cap_id}\n")
            f.write(f"- 優先度: **{entry['priority']}**\n")
            f.write(f"- 理由: {entry['reason']}\n\n")

def main():
    missing = list(find_missing_capabilities())
    if not missing:
        print("✅ 不足している能力はありません。")
        return

    print(f"📋 不足能力 ({len(missing)}件): {missing}")
    print("🧠 GPT に優先度を問い合わせます...\n")

    raw_reply = propose_priorities(missing)

    try:
        parsed = json.loads(raw_reply)
        save_outputs(parsed)
        print("✅ 優先度リストを docs/capability_priorities.json に保存しました。")
    except json.JSONDecodeError:
        print("⚠️ GPTの応答をJSONとして解析できませんでした。内容を手動確認してください：\n")
        print(raw_reply)

if __name__ == "__main__":
    main()
