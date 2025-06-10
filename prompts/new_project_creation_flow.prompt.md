# New Project Creation Implementation Plan

## Purpose

Implement the agreed workflow so that a **new project** can be registered through a short conversation with Kai in the Streamlit UI, using only an `identifier` and an `overview`, automatically filling audit metadata, and landing the project in **DRAFT** status.
Once registered, the user can continue the conversation and Kai will be ready for the subsequent “update‑proposal → approval → apply” loop.

---

## Scope of this milestone

1. **Template layer** – introduce a minimal JSON schema with required/optional fields and default values.
2. **Core service layer** – add a `create_project()` helper that applies the template and writes a snapshot to disk / Git.
3. **Streamlit UI** – build a lightweight page that collects just *identifier* and *overview*, confirms creation, and shows the project card.
4. **Self‑Checker tweak** – ignore `__UNDEFINED__` values when computing diffs (info‑level only).

> **Out of scope** (next milestone): automatic diff proposals during ACTIVE phase, regular reports, etc.

---

## Directory / File map (proposed)

```
core/
  ├── models.py            # dataclasses & schema constants
  ├── project_service.py   # create_project(), load/save helpers
  └── self_checker.py      # diff logic (already exists, will patch)
streamlit/
  ├── pages/
  │     └── 01_create_project.py   # new UI entry point
  └── components/
        └── project_card.py        # reusable card component (optional)
```

---

## 1. Template layer

```python
# core/models.py
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4

SCHEMA_VERSION = "1.0"
DEFAULT_UNDEF = "__UNDEFINED__"

@dataclass
class Project:
    identifier: str
    overview: str
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    created_by: str = DEFAULT_UNDEF  # will be caller‑supplied
    status: str = "DRAFT"
    schema_version: str = SCHEMA_VERSION
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    change_log: list = field(default_factory=list)
    uuid: str = field(default_factory=lambda: str(uuid4()))

    # helper to serialise → dict (for JSON / DSL)
    def to_dict(self) -> dict:
        return {k: (v if v else DEFAULT_UNDEF) for k, v in self.__dict__.items()}
```

---

## 2. Core service layer

```python
# core/project_service.py
import json
from pathlib import Path
from .models import Project, DEFAULT_UNDEF

PROJECTS_DIR = Path("data/projects")
PROJECTS_DIR.mkdir(parents=True, exist_ok=True)


def create_project(identifier: str, overview: str, created_by: str) -> Project:
    """Create a new Project instance, save snapshot, and return it (idempotent)."""
    snapshot_path = PROJECTS_DIR / f"{identifier}.json"

    # Idempotency – if the file already exists, just load & return
    if snapshot_path.exists():
        with snapshot_path.open() as fp:
            data = json.load(fp)
        return Project(**data)

    project = Project(identifier=identifier, overview=overview, created_by=created_by)
    with snapshot_path.open("w") as fp:
        json.dump(project.to_dict(), fp, indent=2)
    return project
```

---

## 3. Streamlit UI (simplified example)

```python
# streamlit/pages/01_create_project.py
import streamlit as st
from core.project_service import create_project

st.header("🆕 Create New Project")

with st.form("new_project_form"):
    identifier = st.text_input("Identifier", help="Unique, e.g. project‑alpha")
    overview = st.text_input("Overview", help="One‑line summary")
    submitted = st.form_submit_button("Create")

if submitted and identifier and overview:
    proj = create_project(identifier, overview, created_by="human_user")
    st.success(f"Project '{proj.identifier}' created in DRAFT status.")
    st.json(proj.to_dict(), expanded=False)
```

> **Note:** Conversation integration: after creation, the page can automatically switch the Chat context to this project ID so that subsequent messages are tagged accordingly.

---

## 4. Self‑Checker diff tweak (pseudo‑diff)

```python
# core/self_checker.py (snippet)
if new_val == DEFAULT_UNDEF or old_val == DEFAULT_UNDEF:
    continue  # ignore undefined fields
```

---

## Testing checklist

* [ ] Unit test: create\_project twice with same identifier ⇒ single snapshot, unchanged.
* [ ] UI e2e: fill form ⇒ JSON card appears; reload browser ⇒ same data displayed.
* [ ] Self‑Checker: modify an undefined field ⇒ no ERROR.

---

## Next steps after this PR is merged

1. Wire the project ID into the **chat session state** so Kai recognises which project the conversation belongs to.
2. Implement a lightweight “update proposal” PoC for a single field (e.g., `due_date`).
3. Gradually expand diff detection & approval flow.

---

### Questions for the reviewer

1. Any additional audit fields to add right now?
2. Preference for storing snapshots as **JSON** or **YAML/DSL**?
3. OK to merge the UI into a single page for now, or split Wizard vs. Dashboard?

---

*Generated by Kai – 2025‑06‑11*

## Quick Instruction Set for **Claude code**

> Use the following checklist to implement the feature end‑to‑end.

1. **Create `core/models.py`**

   ```python
   from __future__ import annotations
   from dataclasses import dataclass, field
   from datetime import datetime
   from uuid import uuid4

   SCHEMA_VERSION = "1.0"
   DEFAULT_UNDEF = "__UNDEFINED__"

   @dataclass
   class Project:
       identifier: str
       overview: str
       created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
       created_by: str = DEFAULT_UNDEF
       status: str = "DRAFT"
       schema_version: str = SCHEMA_VERSION
       updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
       change_log: list = field(default_factory=list)
       uuid: str = field(default_factory=lambda: str(uuid4()))

       def to_dict(self) -> dict:
           return {k: (v if v else DEFAULT_UNDEF) for k, v in self.__dict__.items()}
   ```

2. **Create `core/project_service.py`**

   ```python
   import json
   from pathlib import Path
   from .models import Project

   PROJECTS_DIR = Path("data/projects")
   PROJECTS_DIR.mkdir(parents=True, exist_ok=True)

   def create_project(identifier: str, overview: str, created_by: str) -> Project:
       path = PROJECTS_DIR / f"{identifier}.json"
       if path.exists():
           return Project(**json.loads(path.read_text()))
       project = Project(identifier=identifier, overview=overview, created_by=created_by)
       path.write_text(json.dumps(project.to_dict(), indent=2))
       return project
   ```

3. **Patch `core/self_checker.py`** – ignore `__UNDEFINED__` values when comparing snapshots:

   ```python
   if old_val == DEFAULT_UNDEF or new_val == DEFAULT_UNDEF:
       continue  # skip undefined fields
   ```

4. **Add Streamlit page `streamlit/pages/01_create_project.py`**

   ```python
   import streamlit as st
   from core.project_service import create_project

   st.header("🆕 Create New Project")

   with st.form("new_project_form"):
       identifier = st.text_input("Identifier")
       overview = st.text_input("Overview")
       submitted = st.form_submit_button("Create")

   if submitted and identifier and overview:
       proj = create_project(identifier, overview, created_by="human_user")
       st.success(f"Project '{proj.identifier}' created (status=DRAFT)")
       st.json(proj.to_dict())
   ```

5. **Run unit tests**

   * Create project twice → same JSON (idempotent)
   * Self‑Checker reports no diff on undefined fields.

6. **Commit & push**

   ```bash
   git add core streamlit tests
   git commit -m "feat: minimal project creation flow via UI"
   git push origin main
   ```

*Updated by Kai – 2025‑06‑11*
