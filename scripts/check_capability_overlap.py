# scripts/check_capability_overlap.py

import os
import json
import ast
from pathlib import Path

JSON_CAPABILITIES_PATH = "data/kai_capabilities.json"
BASE_DIR = "."

UTILITY_IDS = {
    "load_json", "write_file", "read_file", "write_metadata_file", "save_tags", 
    "ensure_output_dir", "safe_mkdir", "safe_load_text"
}
DECORATOR_IDS = {
    "kai_capability", "decorator"
}
MANUAL_ONLY = {
    "append_log", "load_log", "safe_pull", "git_commit", "apply_patch", "doc_update_proposal"
}

def load_json_capabilities():
    with open(JSON_CAPABILITIES_PATH, encoding="utf-8") as f:
        return [cap["id"] for cap in json.load(f)]

def discover_functions_with_decorator():
    results = {}
    targets = [Path(BASE_DIR) / "app.py", *(Path(BASE_DIR) / "core").glob("*.py")]
    for file_path in targets:
        if not file_path.is_file():
            continue
        with open(file_path, encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=str(file_path))
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                name = node.name
                has_decorator = any(
                    isinstance(deco, ast.Call) and getattr(deco.func, "id", "") == "kai_capability"
                    for deco in node.decorator_list or []
                )
                results[name] = has_decorator
    return results

def main():
    json_ids = set(load_json_capabilities())
    decorator_map = discover_functions_with_decorator()
    code_ids = set(decorator_map.keys())

    only_in_json = json_ids - code_ids
    classification = {}

    for id_ in only_in_json:
        if id_ in DECORATOR_IDS:
            classification[id_] = "helper_decorator"
        elif id_ in UTILITY_IDS:
            classification[id_] = "utility_function"
        elif id_ in MANUAL_ONLY:
            classification[id_] = "likely_manual"
        else:
            classification[id_] = "not_in_code"

    for id_ in (json_ids & code_ids):
        if not decorator_map.get(id_, False):
            classification[id_] = "decorator_missing"

    print("\n✅ Capability IDの差分・分類一覧")
    print("──────────────")
    for k, v in sorted(classification.items()):
        print(f"- {k}: {v}")

if __name__ == "__main__":
    main()
