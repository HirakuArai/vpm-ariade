import streamlit as st
import json
from pathlib import Path

# --- CONFIG --------------------------------------------------------------
DSL_PATH = Path("dsl/integrated_dsl.jsonl")

# --- UTILS --------------------------------------------------------------

def load_dsl():
    if DSL_PATH.exists():
        return DSL_PATH.read_text(encoding="utf-8")
    return ""

def save_dsl(text: str):
    DSL_PATH.parent.mkdir(exist_ok=True)
    DSL_PATH.write_text(text, encoding="utf-8")

# dummy wrappers – will be swapped with real dsl_engine calls
@st.cache_data(show_spinner=False)
def plan_diff(new_text: str):
    from core import dsl_engine
    try:
        new_dsl = [json.loads(line) for line in new_text.splitlines() if line.strip()]
        return dsl_engine.plan(new_dsl)
    except Exception as e:
        return {"error": str(e)}

def apply_dsl(new_text: str, decision_id: str):
    from core import dsl_engine
    new_dsl = [json.loads(line) for line in new_text.splitlines() if line.strip()]
    result = dsl_engine.apply(new_dsl)
    return f"{result}\n✅ decision_id: {decision_id}"

# --- UI -----------------------------------------------------------------

st.title("📝 DSL Editor – Plan / Apply")

# Editor
st.subheader("Edit JSONL")
editor = st.text_area("DSL", load_dsl(), height=300, key="dsl_editor")

col1, col2 = st.columns(2)
if col1.button("Plan diff"):
    with st.spinner("Computing diff …"):
        diff = plan_diff(editor)
    st.write("### Diff")
    st.json(diff)

# Apply with decision id
with st.expander("Apply changes", expanded=False):
    decision_id = st.text_input("decision_id (e.g. 20250514-init)")
    if st.button("Apply", key="apply_btn"):
        if not decision_id:
            st.error("decision_id is required")
        else:
            try:
                msg = apply_dsl(editor, decision_id)
                save_dsl(editor)
                st.success(msg)
            except Exception as e:
                st.error(f"Apply failed: {e}")
