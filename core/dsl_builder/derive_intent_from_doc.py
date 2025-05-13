import json, pathlib, re, hashlib, textwrap, os
from datetime import datetime

"""derive_intent_from_doc.py  –  M5.1 draft generator (OpenAI v1.x)

入力:
  • docs/project_definition.md
  • docs/base_os_rules.md
  • data/kai_capabilities.json（補助メタ）

出力:
  • draft_dsl/intent_dsl_draft_<timestamp>.jsonl

処理概要:
  1. Markdown を OpenAI GPT で解析し capability 行を抽出
  2. `- [id] purpose` 箇条書きを正規表現でフォールバック抽出
  3. 旧 JSON から enabled / requires_confirm を補完
  4. confidence=0.4, status フィールド付きで下書きを生成

依存:
  - openai>=1.10.0,<2.0.0  (requirements.txt に合わせる)
  - OPENAI_API_KEY 環境変数が必要
"""

from openai import OpenAI  # openai-python v1.x

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
DOCS = ROOT / "docs"
DRAFT_DIR = ROOT / "draft_dsl"
DRAFT_DIR.mkdir(exist_ok=True)

TARGET_FILES = {"project_definition.md", "base_os_rules.md"}
GPT_MODEL = os.getenv("GPT_MODEL", "gpt-4o-mini")

# --------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------

def sha2568(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:8]

REGEX_CAP = re.compile(r"^-\s*\[(?P<id>[^\]]+)\]\s+(?P<purpose>.+)$", re.MULTILINE)

def regex_extract(md_text: str):
    for m in REGEX_CAP.finditer(md_text):
        yield {
            "id": m.group("id"),
            "inferred_purpose": m.group("purpose"),
            "confidence": 0.4,
            "enabled": True,
            "requires_confirm": False,
            "status": "ok",
        }

def gpt_extract(md_text: str, client: OpenAI):
    prompt = textwrap.dedent(f"""
    あなたはソフトウェアPMです。次の Markdown 定義書から Kai/VPM が実装すべき capability 情報を JSON Lines で抽出してください。
    各行のフィールドは: id, inferred_purpose, enabled (bool), requires_confirm (bool), status(ok|missing|conflict)。
    欠落/矛盾があれば status を変更し、purpose に簡潔に要約を書いてください。
    JSONLines 以外の出力は禁止します。
    ---
    {md_text[:8000]}
    ---
    例: {{"id":"task_scheduler","inferred_purpose":"タスクをスケジュール実行","enabled":true,"requires_confirm":false,"status":"ok"}}
    """)
    try:
        rsp = client.chat.completions.create(
            model=GPT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        lines = rsp.choices[0].message.content.strip().splitlines()
        for l in lines:
            try:
                rec = json.loads(l)
                rec.setdefault("confidence", 0.4)
                yield rec
            except Exception:
                continue
    except Exception as e:
        print("⚠️ GPT 抽出失敗:", e)
        return []


def load_old_cap_json():
    for p in [ROOT / "data" / "kai_capabilities.json", DOCS / "kai_capabilities.json"]:
        if p.exists():
            return {c["id"]: c for c in json.load(open(p, encoding="utf-8"))}
    return {}

# --------------------------------------------------------------------
# Main pipeline
# --------------------------------------------------------------------

def main():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set")
    client = OpenAI(api_key=api_key)

    records: dict[str, dict] = {}

    for md_path in DOCS.glob("*.md"):
        if md_path.name not in TARGET_FILES:
            continue
        md_text = md_path.read_text(encoding="utf-8")
        # 1) GPT 抽出
        for rec in gpt_extract(md_text, client):
            rec.setdefault("observed_state", {})["sha256"] = sha2568(md_path)
            rec["resource"] = f"intent://{md_path.relative_to(ROOT)}#{rec['id']}"
            rec["dsl_version"] = "0.1"
            records[rec["id"]] = rec
        # 2) 正規表現フォールバック
        for rec in regex_extract(md_text):
            rec.setdefault("observed_state", {})["sha256"] = sha2568(md_path)
            rec["resource"] = f"intent://{md_path.relative_to(ROOT)}#{rec['id']}"
            rec["dsl_version"] = "0.1"
            records.setdefault(rec["id"], rec)  # GPT優先

    # 3) 補助メタのマージ
    old_caps = load_old_cap_json()
    for cid, meta in old_caps.items():
        rec = records.setdefault(
            cid,
            {
                "id": cid,
                "resource": f"intent://legacy/{cid}",
                "inferred_purpose": meta.get("purpose", "目的不明"),
                "confidence": 0.4,
                "dsl_version": "0.1",
                "status": "ok",
            },
        )
        rec["enabled"] = meta.get("enabled", True)
        rec["requires_confirm"] = meta.get("requires_confirm", False)

    # 4) Draft 書き出し
    ts = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    out_path = DRAFT_DIR / f"intent_dsl_draft_{ts}.jsonl"
    with open(out_path, "w", encoding="utf-8") as f:
        for r in records.values():
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"📝 Draft DSL written to {out_path}")

if __name__ == "__main__":
    main()
