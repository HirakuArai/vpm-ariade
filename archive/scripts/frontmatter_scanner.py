import os
import json
import yaml

DOCS_DIR = "docs"
OUTPUT_PATH = os.path.join(DOCS_DIR, "needed_capabilities.json")

def extract_frontmatter(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    if not lines or not lines[0].strip().startswith("---"):
        return {}

    yaml_lines = []
    for line in lines[1:]:
        if line.strip().startswith("---"):
            break
        yaml_lines.append(line)

    try:
        return yaml.safe_load("".join(yaml_lines)) or {}
    except yaml.YAMLError as e:
        print(f"⚠️ YAML parse error in {file_path}: {e}")
        return {}

def scan_all_markdown():
    result = {}
    for fname in os.listdir(DOCS_DIR):
        if not fname.endswith(".md"):
            continue
        path = os.path.join(DOCS_DIR, fname)
        meta = extract_frontmatter(path)
        caps = meta.get("required_capabilities", [])
        for cap in caps:
            if cap not in result:
                result[cap] = {"source_docs": []}
            result[cap]["source_docs"].append(fname)
    return result

def main():
    capabilities = scan_all_markdown()
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(capabilities, f, indent=2, ensure_ascii=False)
    print(f"✅ Extracted {len(capabilities)} capabilities → {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
