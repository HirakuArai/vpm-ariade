import os
import json

from core.capabilities_registry import kai_capability

@kai_capability(
    id="load_json",
    name="JSONファイルロード機能",
    description="Kaiが指定したパスにあるJSONファイルを読み込む能力を提供します。データセットや設定ファイルなどの読み込みに利用します。",
    requires_confirm=False,
    enabled=True
)
def load_json(path):
    """
    JSONファイルを読み込んで返す。ファイルが存在しない場合は空の dict または文字列を返す。
    """
    if not os.path.exists(path):
        return {} if path.endswith(".json") else ""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

@kai_capability(
    id="read_file",
    name="ファイル読み込み能力",
    description="この関数を使用することで、指定されたパスのファイルを読み込むことができます。ファイルアクセスを通じて、データ解析や情報取得等に用いることが可能となります。",
    requires_confirm=False,
    enabled=True
)
def read_file(path):
    """
    指定されたファイルを読み取り文字列として返す。存在しない場合は空文字列。
    """
    return open(path, encoding="utf-8").read() if os.path.exists(path) else ""

@kai_capability(
    id="write_file",
    name="ファイル書き込み",
    description="Kaiは、指定されたパスにファイルを生成し、その中に与えられたコンテンツを書き込むことができます。これにより、特定のデータをファイルとして保存する能力が実現されます。",
    requires_confirm=False,
    enabled=True
)
def write_file(path, content):
    """
    指定されたパスに文字列を保存する。
    """
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

@kai_capability(
    id="ensure_output_dir",
    name="出力ディレクトリの確認・作成",
    description="「ensure_output_dir」関数は、指定されたパスのディレクトリが存在するかを確認し、存在しない場合にはディレクトリを作成します。これにより、Kaiはファイルの出力や保存場所を管理するための能力を実現します。",
    requires_confirm=False,
    enabled=True
)
def ensure_output_dir(path="kai_generated"):
    """
    指定パスのディレクトリを作成（既に存在すれば何もしない）。
    """
    os.makedirs(path, exist_ok=True)

@kai_capability(
    id="safe_mkdir",
    name="ディレクトリ作成",
    description="エージェントKaiは、「safe_mkdir」関数を使って指定したパスに安全にディレクトリを作成します。既存のディレクトリが存在しない場合に限り、新しいディレクトリを作ります。",
    requires_confirm=False,
    enabled=True
)
def safe_mkdir(path):
    """
    指定されたディレクトリを作成（存在チェック付き）。
    """
    os.makedirs(path, exist_ok=True)
