import ast
import os
import json

TARGET_DIRS = ["./app.py", "./core"]
EXCLUDE_DIRS = {"venv", ".venv", ".git", ".streamlit", "__pycache__", "scripts", "tests"}
OUTPUT_PATH = "kai_capabilities_generated.json"
MAX_ENTRIES = 50

def extract_functions_from_ast(tree, file_path):
    capabilities = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            docstring = ast.get_docstring(node)
            capabilities.append({
                "file": file_path,
                "type": "function",
                "name": node.name,
                "args": [arg.arg for arg in node.args.args],
                "doc": docstring.split("\n")[0] if docstring else None
            })
        elif isinstance(node, ast.ClassDef):
            methods = []
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    docstring = ast.get_docstring(item)
                    methods.append({
                        "name": item.name,
                        "args": [arg.arg for arg in item.args.args if arg.arg != "self"],
                        "doc": docstring.split("\n")[0] if docstring else None
                    })
            capabilities.append({
                "file": file_path,
                "type": "class",
                "name": node.name,
                "methods": methods
            })
    return capabilities


def scan_python_files():
    all_capabilities = []
    for path in TARGET_DIRS:
        if path.endswith(".py"):
            paths_to_check = [path]
        else:
            paths_to_check = []
            for root, dirs, files in os.walk(path):
                dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
                for file in files:
                    if file.endswith(".py"):
                        paths_to_check.append(os.path.join(root, file))

        for file_path in paths_to_check:
            with open(file_path, "r", encoding="utf-8") as f:
                try:
                    tree = ast.parse(f.read())
                    capabilities = extract_functions_from_ast(tree, os.path.relpath(file_path))
                    all_capabilities.extend(capabilities)
                except Exception as e:
                    print(f"Error parsing {file_path}: {e}")

    return all_capabilities[:MAX_ENTRIES]


def main():
    capabilities = scan_python_files()
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(capabilities, f, indent=2, ensure_ascii=False)
    print(f"Capabilities extracted to {OUTPUT_PATH} (limited to {MAX_ENTRIES} entries)")


if __name__ == "__main__":
    main()
