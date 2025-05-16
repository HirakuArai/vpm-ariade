"""
Optimized Streamlit‑Kai entrypoint.
- Focuses on **minimal, deterministic** prompt generation.
- Always pulls the latest project rules / definition / architecture & DSL.
- Self‑check utilities live in `selfcheck.py` (not shown here).
"""
from __future__ import annotations

import json
from pathlib import Path
from textwrap import dedent

# ────────────────────────────────────────────────
# ✨ Utility helpers
# ────────────────────────────────────────────────

ROOT = Path(__file__).resolve().parent
DOCS = ROOT / "docs"
DSL  = ROOT / "dsl"


def read(path: str | Path) -> str:
    """Read UTF‑8 text file."""
    return Path(path).read_text(encoding="utf‑8")


def extract_section(md_path: Path, headings: list[str]) -> str:
    """Return Markdown for only the specified top‑level headings.

    ▸ `headings` is a list of H1/H2 text to keep.
    ▸ Stops at the next heading of the same level.
    """
    lines = read(md_path).splitlines()
    keep, buf = False, []
    for line in lines:
        if line.startswith("#"):
            title = line.lstrip("# ").strip()
            keep = title in headings
        if keep:
            buf.append(line)
    return "\n".join(buf)


# ────────────────────────────────────────────────
# 🔑  Prompt generator (single source of truth)
# ────────────────────────────────────────────────

def get_system_prompt() -> str:
    """Return the **minimal & complete** system prompt for Kai."""

    # 1) Core operating rules
    rules = read(DOCS / "base_os_rules.md")

    # 2) Project definition & architecture (key sections only)
    proj = extract_section(DOCS / "project_definition.md", ["目的", "ゴール", "Kai Support の役割"])
    arch = extract_section(DOCS / "architecture_overview.md", ["PoC構成", "運用フロー"])

    # 3) DSL – capabilities catalogue (name & description only)
    lines = []
    for raw in (DSL / "integrated_dsl.jsonl").read_text(encoding="utf‑8").splitlines():
        item = json.loads(raw)
        lines.append(f"- **{item['name']}**: {item['description']}")
    dsl_block = "\n".join(lines)

    # 4) Compose
    prompt = dedent(
        f"""\
        ## Base Rules
        {rules}

        ## Project Overview
        {proj}

        ## Architecture Snapshot
        {arch}

        ## Kai Capabilities (DSL – single source of truth)
        {dsl_block}
        """
    ).strip()

    return prompt


# ────────────────────────────────────────────────
# Example usage inside Streamlit Kai (pseudo‑code)
# ────────────────────────────────────────────────

if __name__ == "__main__":  # local test
    print(get_system_prompt()[:1000])  # preview first 1k chars
