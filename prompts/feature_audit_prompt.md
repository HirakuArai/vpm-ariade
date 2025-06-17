# Claude Code Prompt — UI‑Executable Feature Audit

## 🎯 Purpose

Analyse **`app.py`** and every file under **`pages/`** to extract *exactly* what a user can execute from the Streamlit UI (pages, buttons, inputs, outputs), plus any dead/temporary code.  The result will be used by Kai for gap analysis.

---

## 📝 Instructions to Claude Code

```
Please analyse all files in `app.py` and the `pages/` directory.

For **each page file**:
1. Give the page title (Streamlit page label / filename).
2. List **every UI element** (e.g. `st.button`, `st.text_input`, `st.form`, menu items) the user can interact with.
3. For each element, specify:
   - **Label** shown to the user.
   - **Triggered function(s)** or callback(s) with file & line reference.
   - **Inputs** (form fields, arguments) and **outputs** (session keys, files written, Git commits etc.).
4. Provide a **3‑5 line code snippet** for each element to anchor the analysis.
5. Mark elements commented as `TODO`, `TEMP`, `deprecated`, or never referenced at runtime as:
   - `★ unused` (never called)
   - `★ planned` (commented TODO/FIXME)
6. Summarise inter‑page dependencies (e.g. a task added on page X appears on page Y).

Output in **structured Markdown** with clear hierarchy:
```

### Expected Markdown Outline (Claude Code should follow)

```
# UI‑Executable Features Audit (YYYY‑MM‑DD)

## Home (app.py)
- 🧠 **Kai状態同期**  
  - Triggers: `run_kai_self_check()`  
  - Output: `kai_self_check_result` → Session, JSON file
- ✏️ **Project Definition Editor**  
  - Inputs: Name, Description  
  - Saves to: `project_definition.md`

## pages/2_Task_Manager.py
- ➕ **Add Task** …

## ★ Unused / Planned
- `dummy_func()` …
```

---

## 🚀 How to Run (CLI example)

```bash
claude-code analyze --prompt feature_audit_prompt.md app.py pages/
```

After Claude Code returns the Markdown audit, paste it back to Kai for gap analysis.
