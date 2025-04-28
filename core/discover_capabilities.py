# core/discover_capabilities.py

import os
import ast
from pathlib import Path

def discover_capabilities(base_dir: str = ".", full_scan: bool = False) -> list:
    capabilities = []

    # 走査対象
    targets = [
        Path(base_dir) / "app.py",
        *(Path(base_dir) / "core").glob("*.py")
    ]

    for file_path in targets:
        if not file_path.is_file():
            continue

        with open(file_path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=str(file_path))

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                meta = {
                    "id": None,
                    "name": node.name,
                    "description": "",
                    "requires_confirm": False,
                    "enabled": True,
                    "decorated": False
                }
                # デコレータチェック
                for deco in node.decorator_list or []:
                    if isinstance(deco, ast.Call) and getattr(deco.func, "id", "") == "kai_capability":
                        for keyword in deco.keywords:
                            meta[keyword.arg] = ast.literal_eval(keyword.value)
                        meta["decorated"] = True
                if full_scan or meta["decorated"]:
                    capabilities.append(meta)

    return capabilities
