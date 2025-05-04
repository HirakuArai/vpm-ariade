# core/structure_scanner.py

import os
import json
from typing import List, Dict


def scan_project_structure(base_path: str = ".") -> Dict[str, List[str]]:
    """
    プロジェクトのディレクトリ構造と主要ファイル一覧を辞書形式で返す。
    """
    structure = {}
    for root, dirs, files in os.walk(base_path):
        if any(skip in root for skip in [".venv", "__pycache__", ".git"]):
            continue
        rel_root = os.path.relpath(root, base_path)
        if rel_root == ".":
            rel_root = ""
        structure[rel_root] = sorted(files)
    return structure


def get_structure_snapshot(save_path: str = "data/structure_snapshot.json") -> List[Dict[str, str]]:
    """
    プロジェクト構造を取得し、JSONに保存したうえで UI 用にリスト形式でも返す。

    Returns:
        [{"path": 相対パス}, ...]
    """
    structure = scan_project_structure()
    
    # 保存処理
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(structure, f, indent=2, ensure_ascii=False)

    # 表示用の整形
    flat_list = []
    for directory, files in structure.items():
        for f in files:
            path = os.path.join(directory, f) if directory else f
            flat_list.append({"path": path})
    return flat_list
