from core.markdown_utils import extract_code_from_markdown
from core.code_rewriter import replace_function_in_source
from core.git_ops import try_git_commit

def apply_gpt_patch(markdown_text: str, fn_name: str, source_path: str = "app.py", auto_commit: bool = True) -> bool:
    """
    GPTが返したMarkdown形式の修正提案（markdown_text）からコードブロックを抽出し、
    指定された関数(fn_name)に上書きする。成功時に Git commit も実行。
    """
    code = extract_code_from_markdown(markdown_text)
    if not code:
        print("❌ コードブロックが抽出できませんでした。")
        return False

    success = replace_function_in_source(source_path, fn_name, code)
    if success and auto_commit:
        try_git_commit(source_path)
    return success
