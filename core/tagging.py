import openai
import os
import json

from core.capabilities_registry import kai_capability

DOCS_DIR = "docs"  # app.pyでも同じなので合わせます

@kai_capability(
    id="generate_tags",
    name="ドキュメントタグ生成",
    description="ドキュメント内容を解析し、関連するキーワードタグを自動生成します。",
    requires_confirm=False
)

def generate_tags(text: str) -> list[str]:
    """テキスト内容に基づき、最大3個の日本語タグを返す"""
    system_prompt = "あなたはプロジェクト管理支援AIです。以下の内容を読んで、簡潔な日本語タグを最大3個生成してください。出力はリスト形式で。"

    try:
        response = openai.chat.completions.create(
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

def save_tags(doc_name: str, tags: list):
    """
    指定されたMarkdownファイルに対応する.tagsファイルを作成し、タグを保存する
    """
    if not tags:
        print("⚠️ タグが空のため保存しません。")
        return

    base_name = os.path.splitext(doc_name)[0]
    tags_path = os.path.join(DOCS_DIR, f"{base_name}.tags")

    try:
        with open(tags_path, "w", encoding="utf-8") as f:
            json.dump(tags, f, ensure_ascii=False, indent=2)
        print(f"✅ タグを保存しました: {tags_path}")
    except Exception as e:
        print(f"❌ タグ保存に失敗しました: {e}")
