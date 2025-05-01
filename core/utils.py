import os
import json

def load_json(path):
    """
    JSONファイルを読み込んで返す。ファイルが存在しない場合は空の dict または文字列を返す。
    """
    if not os.path.exists(path):
        return {} if path.endswith(".json") else ""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def read_file(path):
    """
    指定されたファイルを読み取り文字列として返す。存在しない場合は空文字列。
    """
    return open(path, encoding="utf-8").read() if os.path.exists(path) else ""

def write_file(path, content):
    """
    指定されたパスに文字列を保存する。
    """
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

def ensure_output_dir(path="kai_generated"):
    """
    指定パスのディレクトリを作成（既に存在すれば何もしない）。
    """
    os.makedirs(path, exist_ok=True)

def safe_mkdir(path):
    """
    指定されたディレクトリを作成（存在チェック付き）。
    """
    os.makedirs(path, exist_ok=True)
