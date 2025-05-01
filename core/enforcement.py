import json
import os
from core.capabilities_registry import kai_capability

RULES_PATH = "data/kai_rules.json"

def load_rules():
    if not os.path.exists(RULES_PATH):
        raise FileNotFoundError(f"Rules file not found: {RULES_PATH}")
    with open(RULES_PATH, encoding="utf-8") as f:
        return json.load(f).get("rules", [])

@kai_capability(
    id="enforce_rules",
    name="Kaiのルール適用チェック",
    description="Kaiが操作中にベース人格OSやプロジェクトルールに違反していないかを検査します。",
    requires_confirm=False,
    enabled=True
)
def enforce_rules(action_context: dict) -> list:
    """
    与えられたコンテキストに対し、kai_rules.json に基づくルール違反を検出する。
    - action_context: {
        "action": "propose_doc_update",
        "doc_type": "ondemand",
        "approved": False,
        ...
      }

    Returns: 違反したルールの一覧（空リストなら問題なし）
    """
    rules = load_rules()
    violations = []

    for rule in rules:
        rid = rule.get("id")
        desc = rule.get("description", "")
        scope = rule.get("scope")

        # 例：特定ルールに対する簡易チェック（拡張可）
        if rid == "kai-on-demand-doc-block":
            if action_context.get("action") in ["propose_doc_update", "apply_update"] and \
               action_context.get("doc_type") == "ondemand":
                violations.append(rule)

        elif rid == "kai-update-propose-approval":
            if action_context.get("action") == "apply_update" and not action_context.get("approved", False):
                violations.append(rule)

        elif rid == "kai-single-doc-single-commit":
            if action_context.get("action") == "try_git_commit" and \
               action_context.get("modified_docs", 0) > 1:
                violations.append(rule)

        # TODO: 追加ルールチェック（将来）

    return violations
