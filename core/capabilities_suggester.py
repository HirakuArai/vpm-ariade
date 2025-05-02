# core/capabilities_suggester.py

import json
from typing import Dict, List, Any

import openai
import os
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

def generate_suggestions(diff_result: Dict[str, List[Dict[str, Any]]]) -> str:
    """
    差分結果をもとに、日本語で修正提案文を生成する。

    Args:
        diff_result: capabilities_diff.compare_capabilities() の結果

    Returns:
        日本語の提案文（Markdown形式）
    """
    lines = ["# 🔧 Kai 自己更新提案", ""]

    missing = diff_result.get("missing_in_json", [])
    mismatched = diff_result.get("mismatched", [])

    if missing:
        lines.append("## 🟡 未登録の関数提案")
        for cap in missing:
            lines.append(f"- 関数 `{cap.get('id')}` を新規登録提案：")
            lines.append(f"  - 名前: {cap.get('name')}")
            lines.append(f"  - 説明: {cap.get('description')}")
            lines.append(f"  - requires_confirm: {cap.get('requires_confirm')}")
            lines.append(f"  - enabled: {cap.get('enabled')}")
            lines.append("")

    if mismatched:
        lines.append("## 🟠 属性不一致の関数修正提案")
        for mismatch in mismatched:
            lines.append(f"- 関数 `{mismatch['id']}` の属性修正提案：")
            for key, change in mismatch["differences"].items():
                lines.append(f"  - {key}: JSON = {change['json']} → AST = {change['ast']}")
            lines.append("")

    if not missing and not mismatched:
        lines.append("✅ 現在、自己能力に差分はありません。修正提案は不要です。")

    return "\n".join(lines)


def generate_updated_capabilities(ast_caps: List[Dict[str, Any]], json_caps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    AST結果と既存JSONを突き合わせて、仮の新しいcapabilitiesリストを生成する。

    Args:
        ast_caps: ASTから取得した@kai_capability関数群
        json_caps: 既存のkai_capabilities.json内容

    Returns:
        仮更新後のcapabilitiesリスト
    """
    json_index = {cap["id"]: cap for cap in json_caps if cap.get("id")}
    ast_index = {cap["id"]: cap for cap in ast_caps if cap.get("id")}

    # ASTに存在するものをベースにリストを再構築
    updated_caps = []

    for id_, ast_cap in ast_index.items():
        json_cap = json_index.get(id_)
        if not json_cap:
            # もともと存在しない → 新規追加
            updated_caps.append(ast_cap)
        else:
            # 存在している場合は、AST側（最新情報）を信頼して更新
            merged_cap = {
                "id": id_,
                "name": ast_cap.get("name", json_cap.get("name")),
                "description": ast_cap.get("description", json_cap.get("description")),
                "requires_confirm": ast_cap.get("requires_confirm", json_cap.get("requires_confirm")),
                "enabled": ast_cap.get("enabled", json_cap.get("enabled"))
            }
            updated_caps.append(merged_cap)

    return updated_caps

def generate_needed_capabilities(role: str = "project_manager") -> Dict[str, Any]:
    """
    Kaiが担うロールに必要なcapability IDをGPTに判定させる。

    Args:
        role: Kaiの仮想ロール（例: "project_manager"）

    Returns:
        {"role": ..., "required_capabilities": [...]} という辞書
    """
    system_prompt = f"""
あなたはAIエージェントKaiの能力設計補助AIです。
以下のような仮想エージェントにとって、どのような機能（関数ID）を備えるべきかを判断し、
最も基本的かつ汎用的な能力IDリストをJSONで返してください。

- ロール名: {role}
- 目的: AIによるプロジェクト管理の補助
- 出力形式:
{{"role": "{role}", "required_capabilities": ["能力ID1", "能力ID2", ...]}}
    """

    response = openai.ChatCompletion.create(
        model="gpt-4.1",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Kaiの基本機能に必要なcapability IDを列挙してください。"}
        ],
        temperature=0.2
    )

    content = response.choices[0].message["content"]
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {"role": role, "required_capabilities": []}
