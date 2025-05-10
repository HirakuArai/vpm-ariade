# test_insert_decorator.py (改修後)
from core.decorator_inserter import insert_kai_decorator

cap = {
    "name": "get_today_log_path",
    "filepath": "app.py"
}

result = insert_kai_decorator(cap, dry_run=False)
print("✅ 書き込み完了:", result)
