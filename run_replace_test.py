from core.code_rewriter import replace_function_in_source

target_file = "app.py"
target_function = "get_today_log_path"
replacement_code = """
def get_today_log_path() -> str:
    # 🔧 TEST改修済みバージョン
    from datetime import datetime
    return "dummy_path_from_test"
"""

replace_function_in_source(target_file, target_function, replacement_code)
