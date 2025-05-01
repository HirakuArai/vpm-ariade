import os
from core.utils import load_json  # ← 共通ユーティリティから読み込み

DOCS_DIR = "docs"
NEEDED_CAPS_PATH = os.path.join(DOCS_DIR, "needed_capabilities.json")
KAI_CAPS_PATH = os.path.join(DOCS_DIR, "kai_capabilities.json")

def extract_kai_capability_ids(kai_caps):
    return {cap["id"] for cap in kai_caps}

def extract_needed_capability_ids(needed_caps):
    return set(needed_caps.keys())

def find_missing_capabilities():
    needed = load_json(NEEDED_CAPS_PATH)
    kai = load_json(KAI_CAPS_PATH)

    needed_ids = extract_needed_capability_ids(needed)
    kai_ids = extract_kai_capability_ids(kai)

    missing = needed_ids - kai_ids

    return missing

def main():
    missing = find_missing_capabilities()
    if missing:
        print(f"❗ Missing capabilities ({len(missing)}):")
        for cap in sorted(missing):
            print(f" - {cap}")
    else:
        print("✅ Kai already has all required capabilities!")

if __name__ == "__main__":
    main()
