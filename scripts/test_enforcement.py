import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.enforcement import enforce_rules

def test_on_demand_doc_block():
    context = {
        "action": "propose_doc_update",
        "doc_type": "ondemand"
    }
    violations = enforce_rules(context)
    assert any(r["id"] == "kai-on-demand-doc-block" for r in violations), "Expected violation not found"

def test_update_without_approval():
    context = {
        "action": "apply_update",
        "approved": False
    }
    violations = enforce_rules(context)
    assert any(r["id"] == "kai-update-propose-approval" for r in violations), "Expected violation not found"

def test_multi_doc_commit():
    context = {
        "action": "try_git_commit",
        "modified_docs": 2
    }
    violations = enforce_rules(context)
    assert any(r["id"] == "kai-single-doc-single-commit" for r in violations), "Expected violation not found"

def test_valid_action():
    context = {
        "action": "try_git_commit",
        "modified_docs": 1
    }
    violations = enforce_rules(context)
    assert len(violations) == 0, "Unexpected violations detected"

if __name__ == "__main__":
    test_on_demand_doc_block()
    test_update_without_approval()
    test_multi_doc_commit()
    test_valid_action()
    print("✅ All enforcement tests passed.")
