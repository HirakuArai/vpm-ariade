import json
import os
import subprocess

COMPLETE_PATH = "kai_capabilities_completion.json"
REGISTRY_PATH = "kai_capabilities.json"

def load_json(path):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(data, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def merge_capabilities(registered, new_caps):
    registered_ids = {cap["id"] for cap in registered}
    merged = registered[:]
    added = []
    for cap in new_caps:
        if cap["id"] not in registered_ids:
            cap.setdefault("enabled", True)
            cap.setdefault("requires_confirm", False)
            merged.append(cap)
            added.append(cap)
    return merged, added

def commit_changes(file_path, message):
    subprocess.run(["git", "add", file_path], check=True)
    subprocess.run(["git", "commit", "-m", message], check=True)
    print(f"Committed changes: {message}")

def main():
    new_caps = load_json(COMPLETE_PATH)
    registered = load_json(REGISTRY_PATH)
    merged, added = merge_capabilities(registered, new_caps)

    if not added:
        print("No new capabilities to register.")
        return

    save_json(merged, REGISTRY_PATH)
    print(f"Added {len(added)} new capabilities to {REGISTRY_PATH}")

    commit_changes(REGISTRY_PATH, "feat: register new Kai capabilities")

if __name__ == "__main__":
    main()
