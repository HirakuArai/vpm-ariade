# core/structure_scanner.py

import os
import json
from typing import List, Dict


def scan_project_structure(base_path: str = ".") -> dict:
    """
    プロジェクトのディレクトリ構造と主要ファイル一覧を辞書形式で返す。
    """
    structure = {}

    for root, dirs, files in os.walk(base_path):
        # .venv や .git などは無視
        if any(skip in root for skip in [".venv", "__pycache__", ".git"]):
            continue

        rel_root = os.path.relpath(root, base_path)
        if rel_root == ".":
            rel_root = ""

        structure[rel_root] = sorted(files)

    return structure


def save_structure_snapshot(save_path="data/structure_snapshot.json"):
    """
    構造スナップショットをファイルに保存する。
    """
    structure = scan_project_structure()
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(structure, f, indent=2, ensure_ascii=False)


def get_structure_snapshot() -> List[Dict[str, str]]:
    """
    Streamlit UI で使用する用に、ファイル構造をリスト形式で返す。

    Returns:
        [{"path": 相対パス}, ...]
    """
    raw_structure = scan_project_structure()
    flat_list = []
    for directory, files in raw_structure.items():
        for f in files:
            path = os.path.join(directory, f) if directory else f
            flat_list.append({"path": path})
    return flat_list
