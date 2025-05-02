# core/manage_tasks.py

from core.capabilities_registry import kai_capability  # まだならファイル先頭でimport

@kai_capability(
    id="create_task",
    name="タスク作成",
    description="Kaiは「タスク作成」の機能を持っています。これはタイトル、詳細、期限、優先度といった情報を基に新しいタスクを作成して管理することができます。",
    requires_confirm=False,
    enabled=True
)
def create_task(title, description, due_date, priority):
    """
    新しいタスクを作成し、保存する。
    ...
    """
    pass

@kai_capability(
    id="update_task",
    name="タスク更新機能",
    description="Kaiは指定されたIDを持つタスクの各フィールド（タイトル、説明、期日、優先度）を更新する能力を持っています。これにより、タスクの詳細な情報変更が可能になります。",
    requires_confirm=False,
    enabled=True
)
def update_task(task_id, title=None, description=None, due_date=None, priority=None):
    """
    既存のタスクを更新する。
    ...
    """
    pass

@kai_capability(
    id="delete_task",
    name="タスク削除",
    description="この機能は、特定のタスクを削除する能力をKaiに提供します。指定されたIDを持つタスクをKaiのタスクリストから削除することができます。",
    requires_confirm=False,
    enabled=True
)
def delete_task(task_id):
    """
    指定されたIDのタスクを削除する。
    ...
    """
    pass

@kai_capability(
    id="list_tasks",
    name="タスク一覧表示機能",
    description="Kaiは、特定のフィルター条件や並び順に基づいて、タスクの一覧を表示する機能を持っています。これによりユーザーは必要なタスクを効率的に管理・把握することが可能です。",
    requires_confirm=False,
    enabled=True
)
def list_tasks(filter_by=None, order_by=None):
    """
    保存されているタスクのリストを取得する。フィルターやソート順を指定できる。
    ...
    """
    pass
