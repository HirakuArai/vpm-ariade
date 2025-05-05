# core/self_introspection.py

"""Kai self‑introspection utilities.

* 比較対象
  - AST から抽出した `@kai_capability` 関数
  - JSON レジストリ `kai_capabilities.json`
  - GPT が生成した `needed_capabilities_gpt.json`
* 戻り値
  ``{
      diff_result,          # AST vs JSON の詳細 diff
      missing_required,     # GPT が必要と判定したが JSON に無い ID
      violations,           # ルール違反リスト
      capabilities_json,    # JSON レジストリ全体
      capabilities_ast      # AST 抽出結果
  }``
* 実行時に **fingerprint 行** を `print(..., flush=True)` で標準出力へ出力し、
  Streamlit / Cloud のログから「どのソースが走ったか」を即確認できる。
"""

from __future__ import annotations

import copy
import datetime as dt
import hashlib
import pathlib
from typing import Any, Dict, List, Set

from core.capabilities_diff import compare_capabilities, load_ast_capabilities
from core.enforcement import enforce_rules
from core.utils import load_json

# ---------------------------------------------------------------------------
# パス
# ---------------------------------------------------------------------------
PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
JSON_CAPS_PATH = DATA_DIR / "kai_capabilities.json"
NEEDED_CAPS_PATH = DATA_DIR / "needed_capabilities_gpt.json"

# ---------------------------------------------------------------------------
# ヘルパ
# ---------------------------------------------------------------------------

def _norm(val: str | None) -> str | None:
    """大小文字・前後空白を無視した ID 正規化"""
    return None if val is None else val.strip().lower()


def _id_set(lst: List[Dict[str, Any]]) -> Set[str]:
    return {_norm(c.get("id")) for c in lst if _norm(c.get("id"))}


def _fingerprint() -> str:
    path = pathlib.Path(__file__)
    md5 = hashlib.md5(path.read_bytes()).hexdigest()[:8]
    mtime = dt.datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
    return f"{md5}@{mtime}"

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_kai_self_check() -> Dict[str, Any]:
    """Run diagnostics; return diff/missing/violations + full caps lists."""

    # 1. Load
    ast_caps:  List[Dict[str, Any]] = load_ast_capabilities()
    json_caps: List[Dict[str, Any]] = load_json(JSON_CAPS_PATH)

    # 2. 事前に登録 ID を取得（compare_capabilities が弄っても影響しない）
    registered_ids = _id_set(json_caps)

    # 3. Diff (deep‑copy を渡して安全化)
    diff = compare_capabilities(ast_caps, copy.deepcopy(json_caps))

    # 4. GPT 必要 ID
    needed_json = load_json(NEEDED_CAPS_PATH)
    needed_ids = {_norm(x) for x in needed_json.get("required_capabilities", [])}

    # 5. 未登録 ID
    missing_required = sorted(needed_ids - registered_ids)

    # 6. ルール違反（ダミー）
    violations = enforce_rules({"action": "noop", "doc_type": "core"})

    # 7. fingerprint ログ
    print(
        f"[self-check] src={_fingerprint()}  missing={len(missing_required)}  violations={len(violations)}",
        flush=True,
    )

    return {
        "diff_result": diff,
        "missing_required": missing_required,
        "violations": violations,
        "capabilities_json": json_caps,
        "capabilities_ast": ast_caps,
    }
