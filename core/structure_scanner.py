# core/structure_scanner.py

import os
import json

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
    structure = scan_project_structure()
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(structure, f, indent=2, ensure_ascii=False)
