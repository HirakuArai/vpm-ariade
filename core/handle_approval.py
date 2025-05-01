def handle_approval(requester, document, approval_status):
    """
    指定されたドキュメントの承認処理を行います。

    Args:
        requester (str): 承認を要求するユーザーの名前またはID。
        document (str): 承認または非承認するドキュメントの名前またはID。
        approval_status (bool): ドキュメントを承認する場合はTrue、非承認する場合はFalse。

    Returns:
        str: 承認処理の結果を説明するメッセージ。

    使い方の例:
        # ドキュメント "Doc123" をユーザー "User456" が承認する場合
        result_message = handle_approval("User456", "Doc123", True)
        print(result_message)  # 承認が完了した旨のメッセージを出力

        # ドキュメント "Doc789" をユーザー "User101" が非承認する場合
        result_message = handle_approval("User101", "Doc789", False)
        print(result_message)  # 非承認が完了した旨のメッセージを出力
    """
    pass  # 実装はここに記述