import openai

def generate_tags(text: str) -> list[str]:
    """テキスト内容に基づき、最大3個の日本語タグを返す"""
    system_prompt = "あなたはプロジェクト管理支援AIです。以下の内容を読んで、簡潔な日本語タグを最大3個生成してください。出力はリスト形式で。"

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4.1",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ]
        )
        tags_text = response.choices[0].message.content.strip()
        tags = [tag.strip("・- ") for tag in tags_text.splitlines() if tag.strip()]
        return tags[:3]
    except Exception as e:
        print(f"❌ タグ生成失敗: {e}", flush=True)
        return []
