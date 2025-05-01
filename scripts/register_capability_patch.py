import os
import json
import sys
from core.utils import load_json  # ← 共通ユーティリティを使用

PATCH_DIR = "patches"
CAPABILITY_FILE = "docs/kai_capabilities.json"

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def register_capability(cap_id):
    patch_path = os.path.join(PATCH_DIR, f"{cap_id}_capability.json")
    if not os.path.exists(patch_path):
        print(f"❌ パッチファイルが存在しません: {patch_path}")
        return

    patch_data = load_json(patch_path)
    current_caps = load_json(CAPABILITY_FILE)

    existing_ids = {cap["id"] for cap in current_caps}
    if patch_data["id"] in existing_ids:
        print(f"⚠️ 既に登録済みの能力です: {patch_data['id']}")
        return

    current_caps.append(patch_data)
    save_json(CAPABILITY_FILE, current_caps)
    print(f"✅ {patch_data['id']} を kai_capabilities.json に登録しました。")

def main():
    if len(sys.argv) < 2:
        print("❗ 使用方法: python scripts/register_capability_patch.py <capability_id>")
        return

    cap_id = sys.argv[1]
    register_capability(cap_id)

if __name__ == "__main__":
    main()
