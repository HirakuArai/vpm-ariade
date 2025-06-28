#!/usr/bin/env python3
"""
低 confidence エントリを対象に、関数コードを抽出して JSONL 出力するスクリプト。
入力: draft_dsl_filtered_v2_inferred.jsonl
出力: low_confidence_functions.jsonl
"""

import json, pathlib, ast
from typing import List, Dict

ROOT = pathlib.Path(__file__).resolve().parent.parent
INPUT = ROOT / "draft_dsl_filtered_v2_inferred.jsonl"
OUTPUT = ROOT / "low_confidence_functions.jsonl"

def extract_function_code(file_path: pathlib.Path, name: str) -> str:
    try:
        tree = ast.parse(file_path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
                return ast.get_source_segment(file_path.read_text(encoding="utf-8"), node)
    except Exception as e:
        return f"# コード抽出エラー: {e}"
    return "# 関数が見つかりません"

with INPUT.open("r", encoding="utf-8") as f, OUTPUT.open("w", encoding="utf-8") as out:
    for line in f:
        item = json.loads(line)
        if item.get("confidence", 1.0) >= 0.6:
            continue
        uri = item["resource"]
        if not uri.startswith("code://"):
            continue
        rel_path, symbol = uri.replace("code://", "").split("#", 1)
        file_path = ROOT / rel_path
        code = extract_function_code(file_path, symbol)
        out.write(json.dumps({
            "resource": uri,
            "code": code,
            "inferred_purpose": "__UNKNOWN__",
            "confidence": 0.0
        }, ensure_ascii=False) + "\n")

print(f"✅ 書き出し完了: {OUTPUT}")
