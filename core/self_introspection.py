# core/self_introspection.py

from core.capabilities_diff import load_ast_capabilities, load_json_capabilities, compare_capabilities
from core.enforcement import enforce_rules
from core.utils import load_json

def run_kai_self_check():
    ast_caps = load_ast_capabilities()
    json_caps = load_json("data/kai_capabilities.json")  # 正しいファイルを明示
    diff = compare_capabilities(ast_caps, json_caps)

    needed = load_json("data/needed_capabilities_gpt.json")
    needed_ids = set(needed.get("required_capabilities", []))

    # 安全に id を抽出（None や欠落を除外）
    registered_ids = set(cap.get("id") for cap in json_caps if cap.get("id"))

    missing_required = sorted(needed_ids - registered_ids)

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

