import os
import json
from core.utils import ensure_output_dir

OUTPUT_DIR = "kai_generated"

def write_stub_file(id: str, code: str):
    path = os.path.join(OUTPUT_DIR, f"{id}.py")
    with open(path, "w", encoding="utf-8") as f:
        f.write(code)

def write_metadata_file(id: str, name: str, description: str):
    meta = {
        "id": id,
        "name": name,
        "description": description,
        "requires_confirm": False,
        "enabled": True
    }
    path = os.path.join(OUTPUT_DIR, f"{id}_capability.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

def save_capability_stub(id, name, description, code):
    ensure_output_dir(OUTPUT_DIR)
    write_stub_file(id, code)
    write_metadata_file(id, name, description)
