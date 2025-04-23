import ast

def replace_function_in_source(source_path: str, fn_name: str, new_code: str) -> bool:
    try:
        with open(source_path, "r", encoding="utf-8") as f:
            source_lines = f.readlines()
            tree = ast.parse("".join(source_lines))

        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.name == fn_name:
                start = node.lineno - 1
                end = node.end_lineno if hasattr(node, "end_lineno") else node.lineno + 5
                break
        else:
            print(f"❌ 関数 '{fn_name}' が見つかりませんでした。")
            return False

        # new_code をインデント補正して挿入
        new_code_lines = [line + "\n" for line in new_code.strip().splitlines()]
        updated_lines = source_lines[:start] + new_code_lines + source_lines[end:]

        with open(source_path, "w", encoding="utf-8") as f:
            f.writelines(updated_lines)

        print(f"✅ 関数 '{fn_name}' を上書きしました。")
        return True

    except Exception as e:
        print(f"❌ 書き換えエラー: {e}")
        return False
