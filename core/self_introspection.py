# core/self_introspection.py

"""Kai self‑introspection utilities.

This module compares AST‑extracted @kai_capability decorators with the
current JSON registry *and* the GPT‑generated needed_capabilities list.
It returns a dictionary with:

    diff_result      – detailed diff from compare_capabilities()
    missing_required – IDs required by GPT but not present in JSON
    violations       – rule‑enforcement results
"""

from __future__ import annotations

import pathlib
from typing import Dict, Any, List

from core.capabilities_diff import (
    load_ast_capabilities,
    compare_capabilities,
)
from core.enforcement import enforce_rules
from core.utils import load_json

# ---------------------------------------------------------------------------
# Helpers & constants
# ---------------------------------------------------------------------------

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent  # repo root
DATA_DIR = PROJECT_ROOT / "data"

JSON_CAPS_PATH = DATA_DIR / "kai_capabilities.json"
NEEDED_CAPS_PATH = DATA_DIR / "needed_capabilities_gpt.json"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_kai_self_check() -> Dict[str, Any]:
    """Run Kai self‑diagnostics and return a summary dict."""

    # 1) Load capabilities
    ast_caps: List[Dict[str, Any]] = load_ast_capabilities()
    json_caps: List[Dict[str, Any]] = load_json(JSON_CAPS_PATH)

    # 2) Compute diff between AST & JSON definitions – *use a copy* to avoid
    #    accidental mutation inside compare_capabilities().
    diff = compare_capabilities(ast_caps, list(json_caps))  # pass copy

    # 3) Identify *required* capabilities GPT says we need
    needed = load_json(NEEDED_CAPS_PATH)
    needed_ids = set(needed.get("required_capabilities", []))

    # 4) Collect IDs already registered in JSON (skip entries w/o id)
    registered_ids = {cap.get("id") for cap in json_caps if cap.get("id")}

    # 5) Calculate what is still missing
    missing_required = sorted(needed_ids - registered_ids)

    # 6) Run rule‑enforcement checks (dummy context for now)
    test_context = {
        "action": "propose_doc_update",
        "doc_type": "core",  # avoid false positive for on‑demand docs
        "approved": True,
        "modified_docs": 0,
    }
    violations = enforce_rules(test_context)

    return {
        "diff_result": diff,
        "missing_required": missing_required,
        "violations": violations,
    }
