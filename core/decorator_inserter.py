# core/decorator_inserter.py

"""
Kai用デコレータ挿入ユーティリティ
- 指定関数の定義行を検出し、その直前に @kai_capability(...) を挿入
- 元ファイルを破壊しないよう行単位で編集
"""

import ast
import pathlib
from typing import Dict


def insert_kai_decorator(cap: Dict, *, dry_run=False) -> bool | str:
    file_path = pathlib.Path(cap["filepath"])
    if not file_path.exists():
        raise FileNotFoundError(file_path)

    source_lines = file_path.read_text(encoding="utf-8").splitlines()
    tree = ast.parse("\n".join(source_lines))

    target = next(
        (n for n in ast.walk(tree)
         if isinstance(n, ast.FunctionDef) and n.name == cap["name"]),
        None
    )
    if not target:
        raise ValueError(f"関数 `{cap['name']}` が {file_path} に見つかりません")

    idx = target.lineno - 1

    # すでに直前に同じ装飾があるならスキップ
    if "@kai_capability" in source_lines[idx - 1]:
        return False

    # 補完内容（description省略可）
    decorator = f"@kai_capability(id=\\\"{cap['name']}\\\", name=\\\"{cap['name'].replace('_',' ').title()}\\\", description=\\\"Kaiが {cap['name']} に関する能力を提供します。\\\", requires_confirm=False)"

    source_lines.insert(idx, decorator)
    new_source = "\n".join(source_lines) + "\n"

    if dry_run:
        return new_source

    file_path.write_text(new_source, encoding="utf-8")
    return True
