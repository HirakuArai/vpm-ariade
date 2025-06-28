import os
import json
from datetime import datetime

# ───────────────────────────────────────
# file_catalog.py
# Kaiプロジェクトの全ファイル構造を走査し、
# 役割・種類・使用状況の初期判定を行うカタログを生成
# 出力: output/file_catalog.json
# ───────────────────────────────────────

ROOT_DIR = "./"  # vpm-ariade のルート想定
OUTPUT_PATH = "output/file_catalog.json"

SKIP_DIRS = {".git", "__pycache__", "venv", "archive", ".idea"}


# ファイルタイプの推定ルール
def infer_type(filepath):
    if filepath.endswith(".md"):
        return "doc"
    if filepath.endswith(".json"):
        return "data"
    if filepath.endswith(".py"):
        if "test" in filepath.lower():
            return "script_test"
        if "patch" in filepath.lower():
            return "script_patch"
        return "script"
    return "other"


# 役割の初期推定ルール
def infer_purpose(path):
    lowered = path.lower()
    if "capabilities" in lowered:
        return "Kai能力管理"
    if "task" in lowered:
        return "タスク管理"
    if "log" in lowered:
        return "ログ管理"
    if "doc_update" in lowered:
        return "ドキュメント更新"
    if "approval" in lowered:
        return "承認処理"
    if "extract" in lowered or "scan" in lowered:
        return "情報抽出・分析"
    if "tag" in lowered:
        return "タグ生成"
    return "不明"


# メイン処理

def build_catalog():
    catalog = []
    for root, dirs, files in os.walk(ROOT_DIR):
        # スキップ対象除外
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for file in files:
            rel_path = os.path.relpath(os.path.join(root, file), ROOT_DIR)
            entry = {
                "path": rel_path.replace("\\", "/"),
                "filename": file,
                "type": infer_type(file),
                "purpose": infer_purpose(rel_path),
                "last_modified": datetime.fromtimestamp(
                    os.path.getmtime(os.path.join(root, file))
                ).isoformat(),
                "size": os.path.getsize(os.path.join(root, file)),
                "is_active": True  # 初期値。後で self_state_builder が判定補正
            }
            catalog.append(entry)
    return catalog


def main():
    result = build_catalog()
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"✅ ファイルカタログを保存しました: {OUTPUT_PATH}（{len(result)}件）")


if __name__ == "__main__":
    main()
