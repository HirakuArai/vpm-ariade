import json, hashlib, argparse, pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parent.parent
DSL_PATH = ROOT / "dsl" / "integrated_dsl.jsonl"
SCHEMA_PATH = ROOT / "schemas" / "dsl_v0.1.json"

def load_dsl(path=DSL_PATH):
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines()]

def idempotency_key(rec):
    return hashlib.sha256((rec["resource"] + rec["id"]).encode()).hexdigest()

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
    validate_dsl(new_dsl)
    DSL_PATH.parent.mkdir(exist_ok=True)
    DSL_PATH.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in new_dsl))
    return f"Applied {len(new_dsl)} records"

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
