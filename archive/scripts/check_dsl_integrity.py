import sys, pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parent.parent))

import json
import hashlib
from core import dsl_engine

ROOT = pathlib.Path(__file__).resolve().parent.parent
DSL_PATH = ROOT / "dsl" / "integrated_dsl.jsonl"
SCHEMA_PATH = ROOT / "schemas" / "dsl_v0.1.json"

# --- 1. Schema validation ---
try:
    dsl = dsl_engine.load_dsl()
    dsl_engine.validate_dsl(dsl)
    print("✓ Schema validation: PASSED")
except Exception as e:
    print(f"❌ Schema validation FAILED: {e}")
    sys.exit(1)

# --- 2. Plan diff check (should be empty) ---
try:
    diff = dsl_engine.plan(dsl)
    if diff:
        print(f"❌ Plan diff check FAILED: {len(diff)} unmatched resource(s):")
        for r in diff:
            print(" -", r)
        sys.exit(1)
    print("✓ Plan diff check: PASSED")
except Exception as e:
    print(f"❌ Plan diff error: {e}")
    sys.exit(1)

# --- 3. Confidence level check ---
low_conf = [r for r in dsl if r.get("confidence", 1.0) < 0.6]
if low_conf:
    print(f"❌ Confidence check FAILED: {len(low_conf)} record(s) below threshold")
    for r in low_conf:
        print(" -", r["resource"])
    sys.exit(1)
print("✓ Confidence check: PASSED")
