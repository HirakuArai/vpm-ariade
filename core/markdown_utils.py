import re

def extract_code_from_markdown(markdown_text: str, language: str = "python") -> str:
    """
    GPTから返されたMarkdown形式の提案から、指定言語のコードブロックを抽出する。
    - 通常は1つ目のpythonコードブロックを対象とする。
    """
    pattern = rf"```{language}\n(.*?)\n```"
    match = re.search(pattern, markdown_text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return ""
