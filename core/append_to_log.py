# core/append_to_log.py

from core.capabilities_registry import kai_capability  # ← もし未インポートなら追加

@kai_capability(
    id="append_to_log",
    name="ログ追加",
    description="この関数は、指定されたメッセージをログファイルに追加します。ログファイルのパスは引数で指定できます。",
    requires_confirm=False,
    enabled=True
)
def append_to_log(message, log_file_path="default.log"):
    """
    指定されたログファイルにメッセージを追加する関数。

    Args:
        message (str): ログファイルに追加するメッセージ。
        log_file_path (str): ログファイルのパス。デフォルトは 'default.log'。

    この関数は、指定されたログファイルが存在しない場合には新しく作成し、
    存在する場合にはファイルの末尾にメッセージを追記します。
    メッセージはタイムスタンプ付きで追加されるべきです。

    例外処理を行い、ファイルへの書き込みに失敗した場合には適切なエラーメッセージをログに残すか、
    呼び出し元に例外を伝播させることが望ましいです。
    """
    pass  # 実装は未完成で構いません。
