import ast

def extract_functions(source_path: str) -> list[dict]:
    """Pythonファイルから関数定義を抽出する"""
    with open(source_path, "r", encoding="utf-8") as f:
        source = f.read()

    tree = ast.parse(source, filename=source_path)
    results = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            results.append({
                "name": node.name,
                "lineno": node.lineno,
                "end_lineno": getattr(node, "end_lineno", None),
                "args": [arg.arg for arg in node.args.args],
                "docstring": ast.get_docstring(node)
            })
    return results

def extract_classes(source_path: str) -> list[dict]:
    """クラスとそのメソッド一覧を抽出"""
    with open(source_path, "r", encoding="utf-8") as f:
        source = f.read()

    tree = ast.parse(source, filename=source_path)
    classes = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            methods = [
                func.name
                for func in node.body
                if isinstance(func, ast.FunctionDef)
            ]
            classes.append({
                "name": node.name,
                "lineno": node.lineno,
                "end_lineno": getattr(node, "end_lineno", None),
                "methods": methods,
                "docstring": ast.get_docstring(node)
            })
    return classes

def extract_variables(source_path: str) -> list[dict]:
    """トップレベルの定数や変数を抽出（文字列・数値・リストなど）"""
    import ast

    with open(source_path, "r", encoding="utf-8") as f:
        source = f.read()

    tree = ast.parse(source, filename=source_path)
    variables = []

    for node in tree.body:
        if isinstance(node, ast.Assign):
            # 複数代入にも対応: a = b = 1
            for target in node.targets:
                if isinstance(target, ast.Name):
                    # 値は単純なものだけ（文字列、数値、リストなど）
                    if isinstance(node.value, (ast.Str, ast.Constant, ast.Num, ast.List, ast.Tuple)):
                        val = ast.literal_eval(node.value)
                        variables.append({
                            "name": target.id,
                            "lineno": node.lineno,
                            "value": val,
                            "type": type(val).__name__
                        })
    return variables
