# core/self_introspection.py

"""Kai self‑introspection utilities.

* Compares AST‑extracted ``@kai_capability`` decorators with the current
  JSON registry (``kai_capabilities.json``).
* Compares that set with GPT‑generated ``needed_capabilities_gpt.json``.
* Returns a dictionary ``{diff_result, missing_required, violations}`` that
  the Streamlit UI renders.
* **Writes an INFO log line** that includes an 8‑char md5 hash + mtime of
  *this* source file, so developers can verify that the latest code actually
  ran **without touching the UI**.
"""

from __future__ import annotations

import copy
import datetime as dt
import hashlib
import logging
import pathlib
from typing import Any, Dict, List, Set

from core.capabilities_diff import compare_capabilities, load_ast_capabilities
from core.enforcement import enforce_rules
from core.utils import load_json

logger = logging.getLogger("kai.selfcheck")  # Streamlit prints INFO by default

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
JSON_CAPS_PATH = DATA_DIR / "kai_capabilities.json"
NEEDED_CAPS_PATH = DATA_DIR / "needed_capabilities_gpt.json"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _norm(raw: str | None) -> str | None:
    """Normalise a capability ID for case‑/whitespace‑insensitive compare."""
    return None if raw is None else raw.strip().lower()


def _ids(lst: List[Dict[str, Any]]) -> Set[str]:
    """Extract a set of normalised IDs from a list of capability dicts."""
    return {_norm(c.get("id")) for c in lst if _norm(c.get("id"))}


def _source_fingerprint() -> str:
    """Return short md5 + mtime so we know *which* file ran."""
    path = pathlib.Path(__file__)
    digest = hashlib.md5(path.read_bytes()).hexdigest()[:8]
    mtime = dt.datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
    return f"{digest}@{mtime}"

# ---------------------------------------------------------------------------
# Public
# ---------------------------------------------------------------------------

def run_kai_self_check() -> Dict[str, Any]:
    """Run self‑diagnostics and emit a concise log fingerprint."""

    ast_caps = load_ast_capabilities()
    json_caps = load_json(JSON_CAPS_PATH)

    # 1) IDs already registered (before any mutation)
    registered_ids = _ids(json_caps)

    # 2) Diff – pass a deep‑copy so original list isn’t mutated
    diff = compare_capabilities(ast_caps, copy.deepcopy(json_caps))

    # 3) GPT‑required IDs
    needed_data = load_json(NEEDED_CAPS_PATH)
    needed_ids = {_norm(x) for x in needed_data.get("required_capabilities", [])}

    # 4) Missing IDs
    missing_required = sorted(needed_ids - registered_ids)

    # 5) Rule enforcement (dummy context for now)
    violations = enforce_rules({"action": "noop", "doc_type": "core"})

    # 6) Emit a single log line so devs can confirm *which* self_introspection ran
    logger.info(
        "[self-check] src=%s  missing=%d  violations=%d",
        _source_fingerprint(),
        len(missing_required),
        len(violations),
    )

    return {
        "diff_result": diff,
        "missing_required": missing_required,
        "violations": violations,
    }
