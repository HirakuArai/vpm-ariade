# core/self_introspection.py

from core.capabilities_diff import load_ast_capabilities, load_json_capabilities, compare_capabilities
from core.enforcement import enforce_rules
from core.utils import load_json

def run_kai_self_check():
    """
    Kaiの自己診断を実行：
    - capabilities.jsonとの整合性確認（差分チェック）
    - 必要能力（GPT or 自動）との差分チェック
    - ルール違反の検出（仮コンテキスト）
    """
    ast_caps = load_ast_capabilities()
    json_caps = load_json_capabilities()
    diff = compare_capabilities(ast_caps, json_caps)

    needed = load_json("data/needed_capabilities_gpt.json")
    needed_ids = set(needed.get("required_capabilities", []))
    registered_ids = set(cap["id"] for cap in json_caps)

    missing_required = sorted(needed_ids - registered_ids)

    # ルールチェック：仮のテスト文脈を使用
    test_context = {
        "action": "propose_doc_update",
        "doc_type": "ondemand",
        "approved": False,
        "modified_docs": 2
    }
    violations = enforce_rules(test_context)

    return {
        "diff_result": diff,
        "missing_required": missing_required,
        "violations": violations
    }
