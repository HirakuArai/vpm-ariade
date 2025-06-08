"""
✏️ Preview Charter - Editable charter review with data_editor
"""

import streamlit as st

# Set page config first, before any other Streamlit commands
st.set_page_config(
    page_title="Kai VPM v2 - チャーター確認",
    page_icon="✏️",
    layout="wide",
    initial_sidebar_state="expanded"
)

import pandas as pd
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from libs.ui_layout import (
    load_charter_data, save_charter_data, display_charter_overview
)

# Main page content
st.title("✏️ チャーター確認・編集")
st.markdown("分析前にプロジェクトチャーターの確認と編集を行います")

# Check prerequisites
charter_file = st.session_state.get("selected_charter_file")

if not charter_file:
    st.info("👈 まず '📝 新規プロジェクト' ページでチャーターを作成してください")
    st.stop()

charter_path = Path(charter_file)

# Show charter file info
st.info(f"📄 **チャーターファイル:** {charter_path.name}")

if not charter_path.exists():
    st.error(f"❌ チャーターファイルが見つかりません: {charter_file}")
    st.stop()

# Load charter data
charter_data = load_charter_data(charter_file)
if not charter_data:
    st.error("❌ チャーターデータの読み込みに失敗しました")
    st.stop()

# Display overview
display_charter_overview(charter_data)

# Show editable sections
st.markdown("---")
st.header("✏️ チャーター詳細編集")

# Create tabs for different sections
tab1, tab2, tab3, tab4 = st.tabs(["📝 基本情報", "🎯 目標・範囲", "👥 ステークホルダー", "📅 タイムライン・リスク"])

with tab1:
    st.subheader("📝 基本情報")
    
    # Project name
    edited_name = st.text_input(
        "プロジェクト名 *",
        value=charter_data.get("name", ""),
        help="明確で説明的なプロジェクト名を入力してください"
    )
    
    # Purpose
    edited_purpose = st.text_area(
        "目的・背景 *",
        value=charter_data.get("purpose", ""),
        height=100,
        help="このプロジェクトが必要な理由と背景を説明してください"
    )
    
    # Budget and deadline
    constraints = charter_data.get("constraints", {})
    
    col1, col2 = st.columns(2)
    with col1:
        edited_budget = st.text_input(
            "予算",
            value=constraints.get("budget", ""),
            help="予算額を入力するか、該当しない場合は 'なし' と入力"
        )
    
    with col2:
        deadline_value = constraints.get("deadline", "")
        edited_deadline = st.date_input(
            "期限",
            value=None,
            help="プロジェクトの期限を選択してください"
        )
        if edited_deadline:
            edited_deadline_str = edited_deadline.strftime('%Y-%m-%d')
        else:
            edited_deadline_str = deadline_value

with tab2:
    st.subheader("🎯 目標・範囲")
    
    # Outcomes
    st.write("**プロジェクト成果物:**")
    outcomes = charter_data.get("outcomes", [])
    outcomes_df = pd.DataFrame([{"成果物": outcome} for outcome in outcomes])
    
    if outcomes_df.empty:
        outcomes_df = pd.DataFrame([{"成果物": ""}])
    
    edited_outcomes_df = st.data_editor(
        outcomes_df,
        num_rows="dynamic",
        use_container_width=True,
        key="outcomes_editor"
    )
    
    # Scope
    scope = charter_data.get("scope", {})
    
    # Scope In
    st.write("**範囲 - 含まれるもの:**")
    scope_in = scope.get("in", [])
    scope_in_df = pd.DataFrame([{"含まれるもの": item} for item in scope_in])
    
    if scope_in_df.empty:
        scope_in_df = pd.DataFrame([{"含まれるもの": ""}])
    
    edited_scope_in_df = st.data_editor(
        scope_in_df,
        num_rows="dynamic",
        use_container_width=True,
        key="scope_in_editor"
    )
    
    # Scope Out
    st.write("**範囲 - 除外されるもの:**")
    scope_out = scope.get("out", [])
    scope_out_df = pd.DataFrame([{"除外されるもの": item} for item in scope_out])
    
    if scope_out_df.empty:
        scope_out_df = pd.DataFrame([{"除外されるもの": ""}])
    
    edited_scope_out_df = st.data_editor(
        scope_out_df,
        num_rows="dynamic",
        use_container_width=True,
        key="scope_out_editor"
    )
    
    # Success Metrics
    st.write("**成功指標:**")
    success_metrics = charter_data.get("success_metrics", [])
    metrics_df = pd.DataFrame([{"指標": metric} for metric in success_metrics])
    
    if metrics_df.empty:
        metrics_df = pd.DataFrame([{"指標": ""}])
    
    edited_metrics_df = st.data_editor(
        metrics_df,
        num_rows="dynamic",
        use_container_width=True,
        key="metrics_editor"
    )

with tab3:
    st.subheader("👥 ステークホルダー")
    
    stakeholders = charter_data.get("stakeholders", [])
    
    # Convert to DataFrame format
    stakeholders_data = []
    for stakeholder in stakeholders:
        if isinstance(stakeholder, dict):
            stakeholders_data.append({
                "名前": stakeholder.get("name", ""),
                "役割": stakeholder.get("role", "")
            })
        else:
            stakeholders_data.append({
                "名前": str(stakeholder),
                "役割": ""
            })
    
    if not stakeholders_data:
        stakeholders_data = [{"名前": "", "役割": ""}]
    
    stakeholders_df = pd.DataFrame(stakeholders_data)
    
    edited_stakeholders_df = st.data_editor(
        stakeholders_df,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "名前": st.column_config.TextColumn("名前", help="ステークホルダーの名前"),
            "役割": st.column_config.TextColumn("役割", help="プロジェクトでの役割")
        },
        key="stakeholders_editor"
    )

with tab4:
    st.subheader("📅 タイムライン・リスク")
    
    # Milestones
    st.write("**プロジェクトマイルストーン:**")
    milestones = charter_data.get("milestones", [])
    
    milestones_data = []
    for milestone in milestones:
        if isinstance(milestone, dict):
            milestones_data.append({
                "日付": milestone.get("date", ""),
                "タイトル": milestone.get("title", "")
            })
        else:
            milestones_data.append({
                "日付": "",
                "タイトル": str(milestone)
            })
    
    if not milestones_data:
        milestones_data = [{"日付": "", "タイトル": ""}]
    
    milestones_df = pd.DataFrame(milestones_data)
    
    edited_milestones_df = st.data_editor(
        milestones_df,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "日付": st.column_config.TextColumn("日付", help="マイルストーン日付 (YYYY-MM-DD)"),
            "タイトル": st.column_config.TextColumn("タイトル", help="マイルストーンの説明")
        },
        key="milestones_editor"
    )
    
    # Risks
    st.write("**プロジェクトリスク:**")
    risks = charter_data.get("risks", [])
    
    risks_data = []
    for risk in risks:
        if isinstance(risk, dict):
            risks_data.append({
                "リスク": risk.get("risk", ""),
                "対策": risk.get("mitigation", "")
            })
        else:
            risks_data.append({
                "リスク": str(risk),
                "対策": ""
            })
    
    if not risks_data:
        risks_data = [{"リスク": "", "対策": ""}]
    
    risks_df = pd.DataFrame(risks_data)
    
    edited_risks_df = st.data_editor(
        risks_df,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "リスク": st.column_config.TextColumn("リスク", help="潜在的なリスクの説明"),
            "対策": st.column_config.TextColumn("対策", help="このリスクを軽減する方法")
        },
        key="risks_editor"
    )

# Save button
st.markdown("---")
col1, col2, col3 = st.columns([1, 1, 1])

with col1:
    if st.button("💾 変更を保存", type="primary", use_container_width=True):
        # Merge all edited data
        merged_data = {
            "name": edited_name,
            "purpose": edited_purpose,
            "constraints": {
                "budget": edited_budget,
                "deadline": edited_deadline_str,
                "tools": constraints.get("tools", [])
            }
        }
        
        # Add outcomes
        outcomes_list = [row["成果物"] for row in edited_outcomes_df.to_dict("records") if row["成果物"].strip()]
        if outcomes_list:
            merged_data["outcomes"] = outcomes_list
        
        # Add scope
        scope_in_list = [row["含まれるもの"] for row in edited_scope_in_df.to_dict("records") if row["含まれるもの"].strip()]
        scope_out_list = [row["除外されるもの"] for row in edited_scope_out_df.to_dict("records") if row["除外されるもの"].strip()]
        if scope_in_list or scope_out_list:
            merged_data["scope"] = {}
            if scope_in_list:
                merged_data["scope"]["in"] = scope_in_list
            if scope_out_list:
                merged_data["scope"]["out"] = scope_out_list
        
        # Add success metrics
        metrics_list = [row["指標"] for row in edited_metrics_df.to_dict("records") if row["指標"].strip()]
        if metrics_list:
            merged_data["success_metrics"] = metrics_list
        
        # Add stakeholders
        stakeholders_list = []
        for row in edited_stakeholders_df.to_dict("records"):
            if row["名前"].strip():
                stakeholders_list.append({
                    "name": row["名前"].strip(),
                    "role": row["役割"].strip() or "未定義"
                })
        if stakeholders_list:
            merged_data["stakeholders"] = stakeholders_list
        
        # Add milestones
        milestones_list = []
        for row in edited_milestones_df.to_dict("records"):
            if row["タイトル"].strip():
                milestones_list.append({
                    "date": row["日付"] or "未定",
                    "title": row["タイトル"].strip()
                })
        if milestones_list:
            merged_data["milestones"] = milestones_list
        
        # Add risks
        risks_list = []
        for row in edited_risks_df.to_dict("records"):
            if row["リスク"].strip():
                risks_list.append({
                    "risk": row["リスク"].strip(),
                    "mitigation": row["対策"].strip() or "対策要検討"
                })
        if risks_list:
            merged_data["risks"] = risks_list
        
        # Save to file
        try:
            if save_charter_data(charter_file, merged_data):
                st.success("✅ チャーターが正常に更新されました！")
                st.session_state.charter_reviewed = True
                
                # Show what was saved
                with st.expander("📝 保存された変更", expanded=False):
                    st.json(merged_data)
            else:
                st.error("❌ チャーター変更の保存に失敗しました")
        except Exception as e:
            st.error(f"❌ チャーター保存エラー: {str(e)}")

with col2:
    if st.button("🔄 元に戻す", use_container_width=True):
        st.rerun()

with col3:
    if st.button("📊 分析に進む", use_container_width=True):
        st.session_state.charter_reviewed = True
        st.info("続けるには '🧠 分析とWBS' に移動してください")