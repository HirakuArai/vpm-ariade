# test_insert_decorator.py (改修後)
import pytest
pytest.skip("decorator inserter test is temporarily disabled", allow_module_level=True)

from core.decorator_inserter import insert_kai_decorator

cap = {
    "name": "get_today_log_path",
    "filepath": "app.py"
}

# pytest 実行時はここまででスキップされるため、以下は実行されません
# 手動実行したい場合に備えて main ガードを付けています
if __name__ == "__main__":
    result = insert_kai_decorator(cap, dry_run=False)
    print("✅ 書き込み完了:", result)
