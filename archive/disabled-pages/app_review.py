import streamlit as st
import json
import os
from pathlib import Path

st.set_page_config(layout="wide")

# ファイル読み込み
DSL_PATH = Path("draft_dsl_filtered_v2_inferred.jsonl")
REVIEWED_PATH = Path("reviewed_dsl.jsonl")

st.title("📝 DSL レビュー UI")

# DSL の読み込み
dsl_items = []
with DSL_PATH.open("r", encoding="utf-8") as f:
    for line in f:
        rec = json.loads(line)
        if rec.get("confidence", 0.0) < 0.6:
            dsl_items.append(rec)

if not dsl_items:
    st.success("🎉 低信頼のエントリはありません。すべて確定済みです。")
    st.stop()

# セッション状態を初期化
if "current_index" not in st.session_state:
    st.session_state.current_index = 0

index = st.session_state.current_index
item = dsl_items[index]

st.markdown(f"### {index+1} / {len(dsl_items)}")
st.code(item["resource"], language="text")

purpose = st.text_input("目的 (inferred_purpose)", item["inferred_purpose"])
confidence = st.slider("自信度", 0.0, 1.0, float(item["confidence"]), step=0.1)

col1, col2, col3 = st.columns(3)

if col1.button("✅ 承認して次へ"):
    item["inferred_purpose"] = purpose
    item["confidence"] = confidence
    item["decision_id"] = f"approved-{item['id']}"
    with REVIEWED_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(item, ensure_ascii=False) + "\n")
    st.session_state.current_index += 1
    st.rerun()

if col2.button("⏩ スキップ"):
    st.session_state.current_index += 1
    st.rerun()

if col3.button("🔁 最初に戻る"):
    st.session_state.current_index = 0
    st.rerun()
