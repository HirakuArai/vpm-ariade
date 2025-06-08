"""
scan_capabilities.py – Self‑Checker core module
================================================

* 静的解析 (pycg) でリポジトリ全体のコールグラフを生成
* Streamlit / Click / GitHub Actions などの **エントリポイント** を抽出
* coverage.json で実行時ヒットを補完
* kai_capabilities.json と突合し、関数ごとに status ラベルを決定
    - enabled        : UI/CLI/GHA 経由で到達、かつ capabilities に enabled:true で登録
    - unreachable   : capabilities に登録されているがエントリポイントから到達不可
    - unused        : 実装はあるが capabilities 未登録 (潜在能力)
    - needs_review : 静的には unreachable だが runtime でヒット（曖昧 / 要確認）

出力: gap_report.json
```
{
  "functions": {
    "package.module.func": {
       "status": "enabled",
       "reasons": ["reachable_from:UI app.py:button"]
    },
    ...
  }
}
```

CLI:
    $ python core/self_checker/scan_capabilities.py --root . --coverage coverage.json --out gap_report.json
"""

from __future__ import annotations

import argparse
import ast
import json
import logging
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Set

import networkx as nx

# ------------------------------------------------------------
# 🔧 設定
# ------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]  # /core/self_checker/ → repo root
CAP_FILE = PROJECT_ROOT / "docs" / "kai_capabilities.json"
DEFAULT_CALLGRAPH = PROJECT_ROOT / "tmp_callgraph.json"

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ------------------------------------------------------------
# 1. コールグラフ生成 & 読み込み
# ------------------------------------------------------------

def run_pycg(source_paths: List[Path], output_path: Path = DEFAULT_CALLGRAPH) -> Path:
    """pycg を実行して callgraph JSON を生成。既にある場合はスキップ。"""
    if output_path.exists():
        logger.info("callgraph.json already exists – skip pycg run")
        return output_path

    cmd = [
        sys.executable, "-m", "pycg",
        "-o", str(output_path),
        "--fast",
        *[str(p) for p in source_paths],
    ]
    logger.info("Running pycg …")
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        logger.error(res.stderr)
        sys.exit(1)
    logger.info("pycg finished: %s", output_path)
    return output_path

def load_callgraph(callgraph_path: Path) -> nx.DiGraph:
    with open(callgraph_path, encoding="utf-8") as f:
        data = json.load(f)

    g = nx.DiGraph()
    for edge in data["edges"]:
        caller = edge["caller"]
        callee = edge["callee"]
        g.add_edge(caller, callee)
    return g

# ------------------------------------------------------------
# 2. エントリポイント検出
# ------------------------------------------------------------

STREAMLIT_CALLS = {"button", "form_submit_button", "text_input", "file_uploader"}
CLICK_DECORATOR = "click.command"


def find_streamlit_entrypoints(app_py: Path) -> Set[str]:
    """app.py を AST 解析し、st.button などから呼ばれる関数名を取得"""
    entrypoints: Set[str] = set()
    try:
        tree = ast.parse(app_py.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning("AST parse failed for %s: %s", app_py, e)
        return entrypoints

    class _Visitor(ast.NodeVisitor):
        def visit_Call(self, node: ast.Call):
            # st.button("…")
            if isinstance(node.func, ast.Attribute) and node.func.attr in STREAMLIT_CALLS:
                # 親が If → body[0] = Expr(Call(func)) のパターンを期待
                parent_if = getattr(node, "parent", None)
                if isinstance(parent_if, ast.If) and parent_if.body:
                    first = parent_if.body[0]
                    if isinstance(first, ast.Expr) and isinstance(first.value, ast.Call):
                        if isinstance(first.value.func, ast.Name):
                            entrypoints.add(first.value.func.id)
            self.generic_visit(node)

    # annotate parent links
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            child.parent = parent  # type: ignore[attr-defined]

    _Visitor().visit(tree)
    return entrypoints


def find_click_entrypoints(py_files: Iterable[Path]) -> Set[str]:
    """Click の @click.command デコレータが付与された関数を検出"""
    entry: Set[str] = set()
    for f in py_files:
        try:
            tree = ast.parse(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                for dec in node.decorator_list:
                    if isinstance(dec, ast.Attribute) and dec.attr == "command":
                        entry.add(node.name)
    return entry


def find_github_actions_entrypoints(workflow_dir: Path) -> Set[str]:
    """YAML 内の `run: python xxx.py` を抽出し、スクリプト名を関数シンボル風に返す"""
    entry: Set[str] = set()
    py_re = re.compile(r"python\s+([\w./]+\.py)")
    for yml in workflow_dir.glob("*.yml"):
        try:
            import yaml  # local import to avoid hard dep if unused

            data = yaml.safe_load(yml.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                continue
            for job in data.get("jobs", {}).values():
                for step in job.get("steps", []):
                    run_cmd = step.get("run", "")
                    m = py_re.search(run_cmd)
                    if m:
                        script_path = Path(m.group(1)).stem  # foo.py → foo
                        entry.add(script_path)
        except Exception:
            continue
    return entry

# ------------------------------------------------------------
# 3. coverage.json 取り込み
# ------------------------------------------------------------

def load_runtime_hits(path: Path) -> Set[str]:
    if not path.exists():
        return set()
    try:
        data = json.loads(path.read_text())
        hits = set()
        for file_stats in data.get("files", {}).values():
            for fn in file_stats.get("summary", {}).get("functions", []):
                hits.add(fn)
        return hits
    except Exception as e:
        logger.warning("Failed to read coverage.json: %s", e)
        return set()

# ------------------------------------------------------------
# 4. capabilities.json 読み込み
# ------------------------------------------------------------

def load_capability_ids() -> Set[str]:
    if not CAP_FILE.exists():
        return set()
    try:
        cap_data = json.loads(CAP_FILE.read_text(encoding="utf-8"))
        return {c["id"] for c in cap_data if c.get("enabled", True)}
    except Exception as e:
        logger.error("Failed to read kai_capabilities.json: %s", e)
        return set()

# ------------------------------------------------------------
# 5. ステータス判定
# ------------------------------------------------------------

def classify_status(
    fn: str,
    reachable: Set[str],
    enabled_ids: Set[str],
    runtime_hits: Set[str],
) -> str:
    if fn in enabled_ids:
        if fn in reachable or fn in runtime_hits:
            return "enabled"
        return "unreachable"
    else:
        if fn in reachable or fn in runtime_hits:
            return "unused"
        return "unused"  # 実装のみ (L1) – 今は unused と扱う

# ------------------------------------------------------------
# 6. メイン処理
# ------------------------------------------------------------

def main(root: Path, coverage_json: Path, out_path: Path):
    # 1) callgraph
    py_files = list(root.rglob("*.py"))
    callgraph_path = run_pycg(py_files, DEFAULT_CALLGRAPH)
    g = load_callgraph(callgraph_path)

    # 2) entrypoints
    entrypoints = set()
    entrypoints |= find_streamlit_entrypoints(root / "app.py")
    entrypoints |= find_click_entrypoints(py_files)
    entrypoints |= find_github_actions_entrypoints(root / ".github" / "workflows")

    # 3) reachable set
    reachable: Set[str] = set(entrypoints)
    for ep in entrypoints:
        if ep in g:
            reachable |= nx.descendants(g, ep)

    # 4) runtime hits
    runtime_hits = load_runtime_hits(coverage_json)

    # 5) enabled capability IDs
    enabled_ids = load_capability_ids()

    # 6) classify
    func_status: Dict[str, Dict] = {}
    all_funcs = set(g.nodes()) | runtime_hits
    for fn in all_funcs:
        status = classify_status(fn, reachable, enabled_ids, runtime_hits)
        reasons = []
        if fn in entrypoints:
            reasons.append("entrypoint")
        if fn in reachable:
            reasons.append("reachable")
        if fn in runtime_hits:
            reasons.append("runtime")
        if fn in enabled_ids:
            reasons.append("enabled_id")
        func_status[fn] = {"status": status, "reasons": reasons}

    out_path.write_text(json.dumps({"functions": func_status}, indent=2), encoding="utf-8")
    logger.info("gap_report written to %s (total %d functions)", out_path, len(func_status))

# ------------------------------------------------------------
# CLI
# ------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Self‑Checker – scan capabilities status")
    parser.add_argument("--root", type=Path, default=PROJECT_ROOT, help="project root (default: repo root)")
    parser.add_argument("--coverage", type=Path, default=Path("coverage.json"), help="coverage json path")
    parser.add_argument("--out", type=Path, default=Path("gap_report.json"), help="output json")
    args = parser.parse_args()

    main(args.root, args.coverage, args.out)
