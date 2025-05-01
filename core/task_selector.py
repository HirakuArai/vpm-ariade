from core.utils import load_json

CAP_PRIORITY_PATH = "docs/capability_priorities.json"
KAI_CAPS_PATH = "docs/kai_capabilities.json"

def select_next_task():
    priorities = load_json(CAP_PRIORITY_PATH)
    kai_caps = load_json(KAI_CAPS_PATH)
    owned_ids = {cap["id"] for cap in kai_caps}

    order = {"high": 0, "medium": 1, "low": 2}
    sorted_items = sorted(
        priorities.items(),
        key=lambda x: order.get(x[1]["priority"], 99)
    )

    for cap_id, entry in sorted_items:
        if cap_id not in owned_ids:
            return {
                "id": cap_id,
                "priority": entry["priority"],
                "reason": entry["reason"]
            }

    return None  # All capabilities already held
