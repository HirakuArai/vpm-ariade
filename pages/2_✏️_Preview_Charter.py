"""
✏️ Preview Charter - Editable charter review with data_editor
"""

import streamlit as st

# Set page config first, before any other Streamlit commands
st.set_page_config(
    page_title="Kai VPM v2 - Preview Charter",
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
st.title("✏️ Charter Preview & Edit")
st.markdown("Review and edit your project charter before analysis")

# Check prerequisites
charter_file = st.session_state.get("selected_charter_file")

if not charter_file:
    st.info("👈 Please create a charter first in the '📝 New Project' page")
    st.stop()

charter_path = Path(charter_file)

# Show charter file info
st.info(f"📄 **Charter File:** {charter_path.name}")

if not charter_path.exists():
    st.error(f"❌ Charter file not found: {charter_file}")
    st.stop()

# Load charter data
charter_data = load_charter_data(charter_file)
if not charter_data:
    st.error("❌ Failed to load charter data")
    st.stop()

# Display overview
display_charter_overview(charter_data)

# Show editable sections
st.markdown("---")
st.header("✏️ Edit Charter Details")

# Create tabs for different sections
tab1, tab2, tab3, tab4 = st.tabs(["📝 Basic Info", "🎯 Goals & Scope", "👥 Stakeholders", "📅 Timeline & Risks"])

with tab1:
    st.subheader("📝 Basic Information")
    
    # Project name
    edited_name = st.text_input(
        "Project Name *",
        value=charter_data.get("name", ""),
        help="Enter a clear, descriptive project name"
    )
    
    # Purpose
    edited_purpose = st.text_area(
        "Purpose & Background *",
        value=charter_data.get("purpose", ""),
        height=100,
        help="Explain why this project is needed and the background context"
    )
    
    # Budget and deadline
    constraints = charter_data.get("constraints", {})
    
    col1, col2 = st.columns(2)
    with col1:
        edited_budget = st.text_input(
            "Budget",
            value=constraints.get("budget", ""),
            help="Enter budget amount or 'n/a'"
        )
    
    with col2:
        deadline_value = constraints.get("deadline", "")
        edited_deadline = st.date_input(
            "Deadline",
            value=None,
            help="Select project deadline"
        )
        if edited_deadline:
            edited_deadline_str = edited_deadline.strftime('%Y-%m-%d')
        else:
            edited_deadline_str = deadline_value

with tab2:
    st.subheader("🎯 Goals & Scope")
    
    # Outcomes
    st.write("**Project Outcomes:**")
    outcomes = charter_data.get("outcomes", [])
    outcomes_df = pd.DataFrame([{"Outcome": outcome} for outcome in outcomes])
    
    if outcomes_df.empty:
        outcomes_df = pd.DataFrame([{"Outcome": ""}])
    
    edited_outcomes_df = st.data_editor(
        outcomes_df,
        num_rows="dynamic",
        use_container_width=True,
        key="outcomes_editor"
    )
    
    # Scope
    scope = charter_data.get("scope", {})
    
    # Scope In
    st.write("**Scope - What's Included:**")
    scope_in = scope.get("in", [])
    scope_in_df = pd.DataFrame([{"Included": item} for item in scope_in])
    
    if scope_in_df.empty:
        scope_in_df = pd.DataFrame([{"Included": ""}])
    
    edited_scope_in_df = st.data_editor(
        scope_in_df,
        num_rows="dynamic",
        use_container_width=True,
        key="scope_in_editor"
    )
    
    # Scope Out
    st.write("**Scope - What's Excluded:**")
    scope_out = scope.get("out", [])
    scope_out_df = pd.DataFrame([{"Excluded": item} for item in scope_out])
    
    if scope_out_df.empty:
        scope_out_df = pd.DataFrame([{"Excluded": ""}])
    
    edited_scope_out_df = st.data_editor(
        scope_out_df,
        num_rows="dynamic",
        use_container_width=True,
        key="scope_out_editor"
    )
    
    # Success Metrics
    st.write("**Success Metrics:**")
    success_metrics = charter_data.get("success_metrics", [])
    metrics_df = pd.DataFrame([{"Metric": metric} for metric in success_metrics])
    
    if metrics_df.empty:
        metrics_df = pd.DataFrame([{"Metric": ""}])
    
    edited_metrics_df = st.data_editor(
        metrics_df,
        num_rows="dynamic",
        use_container_width=True,
        key="metrics_editor"
    )

with tab3:
    st.subheader("👥 Stakeholders")
    
    stakeholders = charter_data.get("stakeholders", [])
    
    # Convert to DataFrame format
    stakeholders_data = []
    for stakeholder in stakeholders:
        if isinstance(stakeholder, dict):
            stakeholders_data.append({
                "Name": stakeholder.get("name", ""),
                "Role": stakeholder.get("role", "")
            })
        else:
            stakeholders_data.append({
                "Name": str(stakeholder),
                "Role": ""
            })
    
    if not stakeholders_data:
        stakeholders_data = [{"Name": "", "Role": ""}]
    
    stakeholders_df = pd.DataFrame(stakeholders_data)
    
    edited_stakeholders_df = st.data_editor(
        stakeholders_df,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "Name": st.column_config.TextColumn("Name", help="Stakeholder name"),
            "Role": st.column_config.TextColumn("Role", help="Their role in the project")
        },
        key="stakeholders_editor"
    )

with tab4:
    st.subheader("📅 Timeline & Risks")
    
    # Milestones
    st.write("**Project Milestones:**")
    milestones = charter_data.get("milestones", [])
    
    milestones_data = []
    for milestone in milestones:
        if isinstance(milestone, dict):
            milestones_data.append({
                "Date": milestone.get("date", ""),
                "Title": milestone.get("title", "")
            })
        else:
            milestones_data.append({
                "Date": "",
                "Title": str(milestone)
            })
    
    if not milestones_data:
        milestones_data = [{"Date": "", "Title": ""}]
    
    milestones_df = pd.DataFrame(milestones_data)
    
    edited_milestones_df = st.data_editor(
        milestones_df,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "Date": st.column_config.TextColumn("Date", help="Milestone date (YYYY-MM-DD)"),
            "Title": st.column_config.TextColumn("Title", help="Milestone description")
        },
        key="milestones_editor"
    )
    
    # Risks
    st.write("**Project Risks:**")
    risks = charter_data.get("risks", [])
    
    risks_data = []
    for risk in risks:
        if isinstance(risk, dict):
            risks_data.append({
                "Risk": risk.get("risk", ""),
                "Mitigation": risk.get("mitigation", "")
            })
        else:
            risks_data.append({
                "Risk": str(risk),
                "Mitigation": ""
            })
    
    if not risks_data:
        risks_data = [{"Risk": "", "Mitigation": ""}]
    
    risks_df = pd.DataFrame(risks_data)
    
    edited_risks_df = st.data_editor(
        risks_df,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "Risk": st.column_config.TextColumn("Risk", help="Potential risk description"),
            "Mitigation": st.column_config.TextColumn("Mitigation", help="How to mitigate this risk")
        },
        key="risks_editor"
    )

# Save button
st.markdown("---")
col1, col2, col3 = st.columns([1, 1, 1])

with col1:
    if st.button("💾 Save Changes", type="primary", use_container_width=True):
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
        outcomes_list = [row["Outcome"] for row in edited_outcomes_df.to_dict("records") if row["Outcome"].strip()]
        if outcomes_list:
            merged_data["outcomes"] = outcomes_list
        
        # Add scope
        scope_in_list = [row["Included"] for row in edited_scope_in_df.to_dict("records") if row["Included"].strip()]
        scope_out_list = [row["Excluded"] for row in edited_scope_out_df.to_dict("records") if row["Excluded"].strip()]
        if scope_in_list or scope_out_list:
            merged_data["scope"] = {}
            if scope_in_list:
                merged_data["scope"]["in"] = scope_in_list
            if scope_out_list:
                merged_data["scope"]["out"] = scope_out_list
        
        # Add success metrics
        metrics_list = [row["Metric"] for row in edited_metrics_df.to_dict("records") if row["Metric"].strip()]
        if metrics_list:
            merged_data["success_metrics"] = metrics_list
        
        # Add stakeholders
        stakeholders_list = []
        for row in edited_stakeholders_df.to_dict("records"):
            if row["Name"].strip():
                stakeholders_list.append({
                    "name": row["Name"].strip(),
                    "role": row["Role"].strip() or "未定義"
                })
        if stakeholders_list:
            merged_data["stakeholders"] = stakeholders_list
        
        # Add milestones
        milestones_list = []
        for row in edited_milestones_df.to_dict("records"):
            if row["Title"].strip():
                milestones_list.append({
                    "date": row["Date"] or "未定",
                    "title": row["Title"].strip()
                })
        if milestones_list:
            merged_data["milestones"] = milestones_list
        
        # Add risks
        risks_list = []
        for row in edited_risks_df.to_dict("records"):
            if row["Risk"].strip():
                risks_list.append({
                    "risk": row["Risk"].strip(),
                    "mitigation": row["Mitigation"].strip() or "対策要検討"
                })
        if risks_list:
            merged_data["risks"] = risks_list
        
        # Save to file
        try:
            if save_charter_data(charter_file, merged_data):
                st.success("✅ Charter updated successfully!")
                st.session_state.charter_reviewed = True
                
                # Show what was saved
                with st.expander("📝 Saved Changes", expanded=False):
                    st.json(merged_data)
            else:
                st.error("❌ Failed to save charter changes")
        except Exception as e:
            st.error(f"❌ Error saving charter: {str(e)}")

with col2:
    if st.button("🔄 Reset to Original", use_container_width=True):
        st.rerun()

with col3:
    if st.button("📊 Proceed to Analysis", use_container_width=True):
        st.session_state.charter_reviewed = True
        st.info("Navigate to 🧠 Analysis and WBS to continue")