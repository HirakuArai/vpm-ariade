# core/minutes_utils.py
from __future__ import annotations
from pathlib import Path
from datetime import date
import yaml, json, subprocess
from openai import OpenAI

PROMPT_TMPL = """You are Kai's Minutes Assistant.
Output valid YAML (schema v2). Summarise decisions only.

<conversation>
{log_text}
</conversation>
"""

def concat_daily_logs(day: date) -> str:
    day_dir = Path("conversations") / f"{day:%Y/%m/%d}"
    logs = []
    for f in sorted(day_dir.glob("conversation_*.json")):
        logs.extend(json.loads(f.read_text())["messages"])
    return json.dumps({"messages": logs}, ensure_ascii=False)

def generate_daily_minutes(day: date, force=True) -> Path:
    out = Path(f"docs/minutes/{day.year}/minutes_{day:%Y%m%d}.yaml")
    if out.exists() and not force:
        return out

    log_text = concat_daily_logs(day)
    client = OpenAI()
    resp = client.chat.completions.create(
        model="gpt-4.1",
        temperature=0,
        messages=[{"role": "system",
                   "content": PROMPT_TMPL.format(log_text=log_text)}]
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(resp.choices[0].message.content, encoding="utf-8")
    return out

def safe_push_minutes(msg: str):
    subprocess.run(["git", "add", "docs/minutes"], check=True)
    subprocess.run(["git", "commit", "-m", msg], check=True)
    subprocess.run(["git", "push", "origin", "feat/minutes-ui"], check=True)
