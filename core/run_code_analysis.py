import argparse
from core.code_analysis import (
    extract_functions,
    extract_classes,
    extract_variables,
)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True, help="解析対象のPythonファイル")
    parser.add_argument("--mode", choices=["functions", "classes", "variables", "all"], default="all")
    args = parser.parse_args()

    if args.mode in ("functions", "all"):
        print("=== Functions ===")
        for f in extract_functions(args.file):
            print(f"- {f['name']}({', '.join(f['args'])}) @ line {f['lineno']}")

    if args.mode in ("classes", "all"):
        print("\n=== Classes ===")
        for c in extract_classes(args.file):
            print(f"- class {c['name']} (methods: {', '.join(c['methods'])}) @ line {c['lineno']}")

    if args.mode in ("variables", "all"):
        print("\n=== Variables ===")
        for v in extract_variables(args.file):
            print(f"- {v['name']} = {v['value']} ({v['type']}) @ line {v['lineno']}")

if __name__ == "__main__":
    main()
