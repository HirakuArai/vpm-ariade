#!/usr/bin/env python3
"""
auto_review_low_confidence.py – integrated_dsl.jsonl の low-confidence 行を自動確定

実行:
  python scripts/auto_review_low_confidence.py --mode heuristic
  python scripts/auto_review_low_confidence.py --mode gpt
"""
import re, json, argparse, pathlib, hashlib, os, sys
from core import dsl_engine

DSL_PATH = dsl_engine.DSL_PATH
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

def infer_purpose_heuristic(rec_id: str) -> str:
    """関数 ID / ファイル名からざっくり推測"""
    id_low = rec_id.lower()
    if any(k in id_low for k in ["load", "read"]):
        return "データ読込"
    if any(k in id_low for k in ["save", "write", "append"]):
        return "データ保存"
    if "log" in id_low:
        return "ログ操作"
    if "git" in id_low:
        return "Git 操作"
    if "task" in id_low:
        return "タスク管理"
    if "capab" in id_low:
        return "Kai の能力関連"
    if "update" in id_low or "patch" in id_low:
        return "更新処理"
    return "目的不明"

def infer_purpose_gpt(code_snippet: str, default: str) -> str:
    """GPT-4o で 1 行 JSON を生成 {purpose:"...",confidence:0-1}"""
    import openai, textwrap
    openai.api_key = OPENAI_KEY
    prompt = textwrap.dedent(f"""
    あなたはソフトウェアアーキテクトです。
    次の Python コード片が何を目的とした関数か一言で要約し、日本語で返してください。
    返答は 30 文字以内で。
    ---
    {code_snippet[:1200]}
    ---
    """)
    try:
        rsp = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role":"user","content":prompt}],
            temperature=0.2, max_tokens=60)
        return rsp.choices[0].message.content.strip()
    except Exception as e:
        print("⚠️ GPT 失敗:", e, file=sys.stderr)
        return default

def main(mode: str):
    dsl = dsl_engine.load_dsl()
    updated = 0
    for rec in dsl:
        if rec.get("confidence", 1.0) >= 0.6:
            continue
        rid = rec["id"]
        default_purp = infer_purpose_heuristic(rid)
        if mode == "gpt" and OPENAI_KEY:
            code = rec.get("code", "")
            purpose = infer_purpose_gpt(code or rid, default_purp)
        else:
            purpose = default_purp
        rec["inferred_purpose"] = purpose
        rec["confidence"] = 0.9
        rec["decision_id"] = f"auto-{mode}-{hashlib.sha1(rid.encode()).hexdigest()[:8]}"
        updated += 1
    dsl_engine.apply(dsl)
    print(f"✅ auto-review 完了: {updated} 行を確定しました。")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["heuristic", "gpt"], default="heuristic")
    args = ap.parse_args()
    main(args.mode)
