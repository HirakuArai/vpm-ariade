import streamlit as st
import json
from core import dsl_engine
from pathlib import Path

st.set_page_config(layout="wide")
st.title("🧠 DSL Purpose Review (integrated_dsl.jsonl)")

"""🧠 DSL Purpose Review  –  confidence < 0.6 行を integrated_dsl.jsonl から直接レビュー

・integrated_dsl.jsonl = 唯一の真実
・confidence が低い行だけを順番に表示 → 編集 → confidence を上げて保存
"""

# ------------------------------------------------------------------
# データロード
# ------------------------------------------------------------------
@st.cache_data
def load_low_conf_entries():
    dsl = dsl_engine.load_dsl()
    return [rec for rec in dsl if rec.get("confidence", 1.0) < 0.6]

actions = {
    "save_and_next": "✅ 承認して次へ",
    "skip": "⏩ スキップ",
}

if "review_queue" not in st.session_state:
    st.session_state.review_queue = load_low_conf_entries()
    st.session_state.idx = 0

queue = st.session_state.review_queue
idx = st.session_state.idx

if not queue:
    st.success("レビューすべき項目はありません ✅")
    st.stop()

if idx >= len(queue):
    st.success("🎉 全てのレビューが完了しました！")
    st.stop()

current = queue[idx]

# ------------------------------------------------------------------
# UI
# ------------------------------------------------------------------
st.markdown(f"### {idx+1} / {len(queue)}  –  {current['resource']}")

if code := current.get("code"):
    st.code(code, language="python")

inferred = st.text_input("inferred_purpose", value=current.get("inferred_purpose", ""))
confidence = st.slider("confidence", 0.0, 1.0, float(current.get("confidence", 0.0)), 0.1)
decision_id = st.text_input("decision_id (例: 20250511-review)")

col1, col2 = st.columns(2)

if col1.button(actions["save_and_next"]):
    # 更新
    full_dsl = dsl_engine.load_dsl()
    for rec in full_dsl:
        if rec["id"] == current["id"]:
            rec["inferred_purpose"] = inferred
            rec["confidence"] = confidence
            if decision_id:
                rec["decision_id"] = decision_id
            break
    # 保存 (冪等適用)
    dsl_engine.apply(full_dsl)
    # 次へ
    st.session_state.idx += 1
    st.experimental_rerun()

if col2.button(actions["skip"]):
    st.session_state.idx += 1
    st.experimental_rerun()
