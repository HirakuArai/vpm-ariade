#!/usr/bin/env python3
"""
Walks core/**/*.py, docs/**/*.md, *.json (excluding .dslignore) and emits JSONLines:
{"uri": "...", "type": "...", "path": "...", "name": "..."}
"""
import ast, json, os, re, hashlib, pathlib
import pathspec  # pip install pathspec

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT  = ROOT / "inventory.jsonl"
IGNORE_FILE = ROOT / ".dslignore"

# ── .dslignore ロード（あれば）
ignore_spec = None
if IGNORE_FILE.exists():
    with open(IGNORE_FILE, "r", encoding="utf-8") as f:
        ignore_spec = pathspec.PathSpec.from_lines("gitwildmatch", f)

def should_ignore(path: pathlib.Path) -> bool:
    if ignore_spec is None:
        return False
    rel_path = str(path.relative_to(ROOT)).replace(os.sep, "/")
    return ignore_spec.match_file(rel_path)

def py_items(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            yield f"code://{path.relative_to(ROOT)}#{node.name}", "function", node.name
        elif isinstance(node, ast.ClassDef):
            yield f"code://{path.relative_to(ROOT)}#{node.name}", "class", node.name

def emit(uri, rtype, path, name):
    print(json.dumps({
        "uri": uri,
        "type": rtype,
        "path": str(path),
        "name": name,
        "sha256": hashlib.sha256(open(path, "rb").read()).hexdigest()[:8]
    }), file=OUT.open("a", encoding="utf-8"))

if OUT.exists():
    OUT.unlink()

for path in ROOT.rglob("*"):
    if path.is_dir() or should_ignore(path):
        continue
    if re.match(r".*\.py$", path.name):
        for uri, tp, nm in py_items(path):
            emit(uri, tp, path, nm)
    elif re.match(r".*\.md$", path.name):
        emit(f"doc://{path.relative_to(ROOT)}", "doc", path, path.name)
    elif re.match(r".*\.json$", path.name):
        emit(f"json://{path.relative_to(ROOT)}", "json", path, path.name)

print(f"📝 inventory written to {OUT}")
