import json
import os

GEN_PATH = "kai_capabilities_generated.json"
REG_PATH = "kai_capabilities.json"
PATCH_PATH = "kai_capabilities_patch.json"


def load_json(path):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def extract_registered_ids(registered):
    return {item["id"] for item in registered if "id" in item}


def generate_patch_entries(generated, registered_ids):
    patch = []
    for cap in generated:
        if cap["type"] != "function":
            continue
        fn_name = cap["name"]
        if fn_name in registered_ids:
            continue

        patch.append({
            "id": fn_name,
            "name": fn_name,
            "description": f"TODO: Kaiの能力 '{fn_name}' の説明を補完してください。",
            "source_file": cap["file"],
            "args": cap["args"]
        })
    return patch


def main():
    generated = load_json(GEN_PATH)
    registered = load_json(REG_PATH)
    registered_ids = extract_registered_ids(registered)
    
    patch = generate_patch_entries(generated, registered_ids)

    with open(PATCH_PATH, "w", encoding="utf-8") as f:
        json.dump(patch, f, indent=2, ensure_ascii=False)

    print(f"Generated patch file with {len(patch)} new capabilities → {PATCH_PATH}")


if __name__ == "__main__":
    main()
