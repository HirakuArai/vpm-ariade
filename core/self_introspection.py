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
from typing import Dict, Any, List, Set

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
# Utility
# ---------------------------------------------------------------------------

def _normalise_id(raw: str | None) -> str | None:
    """Strip whitespace/newlines and lower-case the ID for robust comparison."""
    if raw is None:
        return None
    return raw.strip().lower()


def _extract_ids(caps: List[Dict[str, Any]]) -> Set[str]:
    """Return a set of normalised capability IDs from a JSON list."""
    return {
        norm_id
        for cap in caps
        if (norm_id := _normalise_id(cap.get("id")))
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_kai_self_check() -> Dict[str, Any]:
    """Run Kai self‑diagnostics and return a summary dict."""

    # 1) Load capabilities
    ast_caps: List[Dict[str, Any]] = load_ast_capabilities()
    json_caps: List[Dict[str, Any]] = load_json(JSON_CAPS_PATH)

    # 2) Compute diff – pass a *copy* so compare_capabilities can't mutate
    diff = compare_capabilities(ast_caps, list(json_caps))

    # 3) IDs GPT says we need (normalised)
    needed_data = load_json(NEEDED_CAPS_PATH)
    needed_ids = {_normalise_id(x) for x in needed_data.get("required_capabilities", [])}

    # 4) IDs already registered in JSON (normalised + skip blanks)
    registered_ids = _extract_ids(json_caps)

    # 5) Calculate still‑missing IDs (case/whitespace agnostic)
    missing_required = sorted(needed_ids - registered_ids)

    # 6) Rule enforcement (dummy context)
    test_context = {
        "action": "propose_doc_update",
        "doc_type": "core",  # avoid on‑demand false positive
        "approved": True,
        "modified_docs": 0,
    }
    violations = enforce_rules(test_context)

    return {
        "diff_result": diff,
        "missing_required": missing_required,
        "violations": violations,
    }
