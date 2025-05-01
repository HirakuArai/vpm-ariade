import os
import json

# ───────────────────────────────────────
# self_state_builder.py
# Kaiの能力・ファイル・必要性を統合した「自己状態」JSONを生成
# 出力: output/kai_self_state.json
# ───────────────────────────────────────

CATALOG_PATH = "output/file_catalog.json"
CAP_PATH = "data/kai_capabilities.json"
NEEDED_PATH = "output/needed_capabilities_gpt.json"
OUTPUT_PATH = "output/kai_self_state.json"


def load_json(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def build_state():
    catalog = load_json(CATALOG_PATH)
    capabilities = load_json(CAP_PATH)
    needed = set(load_json(NEEDED_PATH).get("required_capabilities", []))

    # マッピング: capability_id → file metadata
    path_map = {os.path.splitext(os.path.basename(f["path"]))[0]: f for f in catalog}

    state = {}
    for cap in capabilities:
        cid = cap["id"]
        fname = os.path.splitext(os.path.basename(cap.get("source_file", "")))[0]
        meta = path_map.get(fname, {})
        state[cid] = {
            "id": cid,
            "name": cap.get("name"),
            "description": cap.get("description"),
            "enabled": cap.get("enabled", True),
            "registered": True,
            "needed": cid in needed,
            "in_code": bool(meta),
            "file_path": meta.get("path"),
            "last_modified": meta.get("last_modified"),
            "size": meta.get("size"),
            "purpose": meta.get("purpose")
        }

    # 未登録だが必要なものも追加（漏れ検出）
    for cid in needed:
        if cid not in state:
            state[cid] = {
                "id": cid,
                "name": "(未登録)",
                "description": "",
                "enabled": False,
                "registered": False,
                "needed": True,
                "in_code": False,
                "file_path": None,
                "last_modified": None,
                "size": None,
                "purpose": None
            }

    return list(state.values())


def main():
    result = build_state()
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"✅ Kai自己状態ファイルを出力しました: {OUTPUT_PATH} ({len(result)} entries)")


if __name__ == "__main__":
    main()
