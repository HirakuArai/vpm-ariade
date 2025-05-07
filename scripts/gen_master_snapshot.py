import os
import json
import hashlib
import yaml
import ast

REPO_ROOT = "."
OUTPUT_PATH = "output/master_snapshot.json"
DIR_WHITELIST = ["", "core/", "scripts/", "docs/"]  # これは data/dir_whitelist.json を読む形に変更可


def md5_of_file(path):
    hash_md5 = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def extract_ast_info(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            src = f.read()
        tree = ast.parse(src)
        functions = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                name = node.name
                args = ast.unparse(node.args) if hasattr(ast, "unparse") else "(…)"
                decorators = [d.id for d in node.decorator_list if isinstance(d, ast.Name)]
                functions.append({
                    "name": name,
                    "signature": f"def {name}{args}",
                    "capability": next((d for d in decorators if d.startswith("kai_")), None),
                    "loc": len(src.splitlines())
                })
        return {"functions": functions}
    except Exception as e:
        return {"error": str(e)}


def extract_frontmatter(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        if not lines or not lines[0].strip() == "---":
            return None
        end = next(i for i, line in enumerate(lines[1:], start=1) if line.strip() == "---")
        yaml_block = "".join(lines[1:end])
        return yaml.safe_load(yaml_block)
    except Exception as e:
        return {"error": str(e)}


def is_in_whitelist(path):
    return any(path.startswith(os.path.join(REPO_ROOT, d)) for d in DIR_WHITELIST)


def gen_master_snapshot():
    snapshot = []
    for root, _, files in os.walk(REPO_ROOT):
        for fname in files:
            full_path = os.path.join(root, fname)
            rel_path = os.path.relpath(full_path, REPO_ROOT)
            if not is_in_whitelist(full_path):
                continue
            if ".git" in rel_path or ".venv" in rel_path:
                continue

            record = {
                "path": rel_path,
                "md5": md5_of_file(full_path),
                "size": os.path.getsize(full_path),
                "mtime": os.path.getmtime(full_path)
            }

            if fname.endswith(".py"):
                record["ast"] = extract_ast_info(full_path)
            elif fname.endswith(".md") or fname.endswith(".json"):
                fm = extract_frontmatter(full_path)
                if fm:
                    record["frontmatter"] = fm

            snapshot.append(record)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2, ensure_ascii=False)
    print(f"✅ master_snapshot.json generated: {OUTPUT_PATH} ({len(snapshot)} files)")


if __name__ == "__main__":
    gen_master_snapshot()
