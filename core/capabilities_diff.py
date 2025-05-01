# core/capabilities_diff.py

import json
from typing import List, Dict, Any
from core.discover_capabilities import discover_capabilities

def load_ast_capabilities() -> List[Dict[str, Any]]:
    """
    AST解析により、@kai_capability付き関数を含む関数一覧を取得する。
    """
    return discover_capabilities(full_scan=True)

def load_json_capabilities(json_path: str = "data/kai_capabilities.json") -> List[Dict[str, Any]]:
    """
    kai_capabilities.jsonを読み込んで返す。
    """
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)

def compare_capabilities(ast_caps: List[Dict[str, Any]], json_caps: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    AST結果とJSON定義を比較し、差分（未登録・不一致）を返す。

    Returns:
        {
            "missing_in_json": [...],
            "mismatched": [...]
        }
    """
    json_index = {cap["id"]: cap for cap in json_caps if cap.get("id")}
    ast_index = {cap["id"]: cap for cap in ast_caps if cap.get("id")}

    missing = []
    mismatched = []

    for id_, ast_cap in ast_index.items():
        json_cap = json_index.get(id_)
        if not json_cap:
            missing.append(ast_cap)
        else:
            # 比較項目：name, description, requires_confirm, enabled
            diffs = {}
            for key in ["name", "description", "requires_confirm", "enabled"]:
                if ast_cap.get(key) != json_cap.get(key):
                    diffs[key] = {
                        "json": json_cap.get(key),
                        "ast": ast_cap.get(key)
                    }
            if diffs:
                mismatched.append({
                    "id": id_,
                    "differences": diffs
                })

    return {
        "missing_in_json": missing,
        "mismatched": mismatched
    }

def format_diff_for_output(diff_result: Dict[str, List[Dict[str, Any]]]) -> str:
    """
    差分結果をMarkdown形式で整形し、出力用にする。
    """
    lines = ["# 🔍 Kai 自己能力差分チェック結果", ""]

    if diff_result["missing_in_json"]:
        lines.append("## 🟡 capabilities.jsonに未登録の関数")
        for cap in diff_result["missing_in_json"]:
            lines.append(f"- `{cap.get('id')}`: {cap.get('name')}")
        lines.append("")

    if diff_result["mismatched"]:
        lines.append("## 🟠 属性不一致の関数")
        for mismatch in diff_result["mismatched"]:
            lines.append(f"### 🔧 `{mismatch['id']}`")
            for key, change in mismatch["differences"].items():
                lines.append(f"- `{key}`: JSON = {change['json']} → AST = {change['ast']}")
        lines.append("")

    if not lines[2:] and not lines[-1]:
        lines.append("✅ 差分はありません。すべて一致しています。")

    return "\n".join(lines)
