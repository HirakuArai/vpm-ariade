import json, hashlib, argparse, pathlib, sys, time   # ← time を追加
ROOT = pathlib.Path(__file__).resolve().parent.parent
DSL_PATH   = ROOT / "dsl" / "integrated_dsl.jsonl"
SCHEMA_PATH = ROOT / "schemas" / "dsl_v0.1.json"
IDEMP_FILE  = ROOT / ".dsl" / "applied_keys.json"    # ← 追加

# ────────────────────────────────
def load_dsl(path=DSL_PATH):
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines()]

def idempotency_key(rec):
    return hashlib.sha256((rec["resource"] + rec["id"]).encode()).hexdigest()

# ─── Idempotency 用ヘルパ ───────
def load_applied_keys():
    if IDEMP_FILE.exists():
        return json.load(open(IDEMP_FILE, encoding="utf-8"))
    return {}

def save_applied_keys(keys: dict):
    IDEMP_FILE.parent.mkdir(exist_ok=True)
    json.dump(keys, open(IDEMP_FILE, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
# ────────────────────────────────

def validate_dsl(dsl):
    import jsonschema
    schema = json.load(open(SCHEMA_PATH))
    for rec in dsl:
        jsonschema.validate(rec, schema)

def plan(new_dsl):
    cur = {r["resource"]: r for r in load_dsl()}
    diff = []
    for rec in new_dsl:
        if rec != cur.get(rec["resource"]):
            diff.append(rec["resource"])
    return diff

def apply(new_dsl):
    """PUT 全量＋Idempotency‐Key 検査付き"""
    validate_dsl(new_dsl)
    applied = load_applied_keys()

    new_cnt, skip_cnt = 0, 0
    for rec in new_dsl:
        k = idempotency_key(rec)
        if k in applied:
            skip_cnt += 1
            continue
        new_cnt += 1
        applied[k] = int(time.time())

    # ❶ DSL ファイルを全量置換
    DSL_PATH.parent.mkdir(exist_ok=True)
    DSL_PATH.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in new_dsl))

    # ❷ 適用キーを保存
    save_applied_keys(applied)

    return f"Applied {new_cnt} new / {skip_cnt} skipped"

# ─── CLI エントリ ───────────────
if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", help="file to plan")
    ap.add_argument("--apply", help="file to apply")
    args = ap.parse_args()

    if args.plan:
        new = [json.loads(l) for l in open(args.plan, encoding="utf-8")]
        print(plan(new))
    elif args.apply:
        new = [json.loads(l) for l in open(args.apply, encoding="utf-8")]
        print(apply(new))
    else:
        print("Use --plan or --apply")
