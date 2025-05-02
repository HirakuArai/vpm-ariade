import json, os, re, pathlib

CAP_PATH = "data/kai_capabilities.json"
CORE_PATTERN = re.compile(r"^(append_|propose_|handle_|create_|update_|delete_|list_|try_)")

def guess_type(cap):
    # すでに type があれば尊重
    if "type" in cap:
        return cap["type"]
    fn = cap["id"]
    if CORE_PATTERN.match(fn):
        return "core"
    if fn.startswith(("read_", "write_", "load_", "save_", "extract_", "ensure_","safe_")):
        return "utility"
    return "core"   # デフォルト

def main():
    with open(CAP_PATH, encoding="utf-8") as f:
        caps = json.load(f)

    updated = 0
    for cap in caps:
        new_type = guess_type(cap)
        if cap.get("type") != new_type:
            cap["type"] = new_type
            updated += 1

    with open(CAP_PATH, "w", encoding="utf-8") as f:
        json.dump(caps, f, indent=2, ensure_ascii=False)
    print(f"✅ type を更新 : {updated} 件")

if __name__ == "__main__":
    main()
