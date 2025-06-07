"""
Page 2: Preview Charter - Editable charter review with data_editor
"""

import streamlit as st
import pandas as pd
from pathlib import Path

from libs.ui_layout import (
    setup_page_config, navigation_buttons, error_boundary,
    load_charter_data, save_charter_data, display_charter_overview,
    check_prerequisites
)


@error_boundary
def show_page():
    """Show the charter preview page"""
    setup_page_config("Preview Charter", "2️⃣")
    
    st.title("2️⃣ Charter Preview & Edit")
    st.markdown("Review and edit your project charter before analysis")
    
    # Check prerequisites
    if not check_prerequisites(["selected_charter_file"]):
        st.info("👈 Please create a charter first in the 'New Project' page")
        navigation_buttons("2_preview_charter") 
        return
    
    charter_file = st.session_state.selected_charter_file
    charter_path = Path(charter_file)
    
    # Show charter file info
    st.info(f"📄 **Charter File:** {charter_path.name}")
    
    if not charter_path.exists():
        st.error(f"❌ Charter file not found: {charter_file}")
        return
    
    # Load charter data
    charter_data = load_charter_data(charter_file)
    if not charter_data:
        st.error("❌ Failed to load charter data")
        return
    
    # Display overview
    display_charter_overview(charter_data)
    
    # Show editable sections
    st.markdown("---")
    st.header("✏️ Edit Charter Details")
    
    # Create tabs for different sections
    tab1, tab2, tab3, tab4 = st.tabs(["📝 Basic Info", "🎯 Goals & Scope", "👥 Stakeholders", "📅 Timeline & Risks"])
    
    with tab1:
        edited_basic = edit_basic_info(charter_data)
    
    with tab2:
        edited_goals = edit_goals_and_scope(charter_data)
    
    with tab3:
        edited_stakeholders = edit_stakeholders(charter_data)
    
    with tab4:
        edited_timeline = edit_timeline_and_risks(charter_data)
    
    # Save button
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        if st.button("💾 Save Changes", type="primary", use_container_width=True):
            save_edited_charter(charter_file, edited_basic, edited_goals, edited_stakeholders, edited_timeline)
    
    with col2:
        if st.button("🔄 Reset to Original", use_container_width=True):
            st.rerun()
    
    with col3:
        if st.button("📊 Proceed to Analysis", use_container_width=True):
            st.session_state.charter_reviewed = True
            st.session_state.current_page = "3_persona_and_wbs"
            st.rerun()
    
    # Navigation
    st.markdown("---")
    navigation_buttons("2_preview_charter")


def edit_basic_info(charter_data: dict) -> dict:
    """Edit basic charter information"""
    st.subheader("📝 Basic Information")
    
    edited_data = {}
    
    # Project name
    edited_data["name"] = st.text_input(
        "Project Name *",
        value=charter_data.get("name", ""),
        help="Enter a clear, descriptive project name"
    )
    
    # Purpose
    edited_data["purpose"] = st.text_area(
        "Purpose & Background *",
        value=charter_data.get("purpose", ""),
        height=100,
        help="Explain why this project is needed and the background context"
    )
    
    # Budget and deadline
    constraints = charter_data.get("constraints", {})
    
    col1, col2 = st.columns(2)
    with col1:
        budget = st.text_input(
            "Budget",
            value=constraints.get("budget", ""),
            help="Enter budget amount or 'n/a'"
        )
    
    with col2:
        deadline = st.date_input(
            "Deadline",
            value=None,
            help="Select project deadline"
        )
        deadline_str = deadline.strftime('%Y-%m-%d') if deadline else constraints.get("deadline", "")
    
    edited_data["constraints"] = {
        "budget": budget,
        "deadline": deadline_str,
        "tools": constraints.get("tools", [])
    }
    
    return edited_data


def edit_goals_and_scope(charter_data: dict) -> dict:
    """Edit goals and scope with data_editor"""
    st.subheader("🎯 Goals & Scope")
    
    edited_data = {}
    
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
    edited_data["outcomes"] = [row["Outcome"] for row in edited_outcomes_df.to_dict("records") if row["Outcome"].strip()]
    
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
    
    edited_data["scope"] = {
        "in": [row["Included"] for row in edited_scope_in_df.to_dict("records") if row["Included"].strip()],
        "out": [row["Excluded"] for row in edited_scope_out_df.to_dict("records") if row["Excluded"].strip()]
    }
    
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
    edited_data["success_metrics"] = [row["Metric"] for row in edited_metrics_df.to_dict("records") if row["Metric"].strip()]
    
    return edited_data


def edit_stakeholders(charter_data: dict) -> dict:
    """Edit stakeholders with data_editor"""
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
    
    # Convert back to expected format
    edited_stakeholders = []
    for row in edited_stakeholders_df.to_dict("records"):
        if row["Name"].strip():
            edited_stakeholders.append({
                "name": row["Name"].strip(),
                "role": row["Role"].strip() or "未定義"
            })
    
    return {"stakeholders": edited_stakeholders}


def edit_timeline_and_risks(charter_data: dict) -> dict:
    """Edit milestones and risks with data_editor"""
    st.subheader("📅 Timeline & Risks")
    
    edited_data = {}
    
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
            "Date": st.column_config.DateColumn("Date", help="Milestone date (YYYY-MM-DD)"),
            "Title": st.column_config.TextColumn("Title", help="Milestone description")
        },
        key="milestones_editor"
    )
    
    # Convert milestones back to expected format
    edited_milestones = []
    for row in edited_milestones_df.to_dict("records"):
        if row["Title"].strip():
            date_val = row["Date"]
            if hasattr(date_val, 'strftime'):
                date_str = date_val.strftime('%Y-%m-%d')
            else:
                date_str = str(date_val) if date_val else "未定"
            
            edited_milestones.append({
                "date": date_str,
                "title": row["Title"].strip()
            })
    
    edited_data["milestones"] = edited_milestones
    
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
    
    # Convert risks back to expected format
    edited_risks = []
    for row in edited_risks_df.to_dict("records"):
        if row["Risk"].strip():
            edited_risks.append({
                "risk": row["Risk"].strip(),
                "mitigation": row["Mitigation"].strip() or "対策要検討"
            })
    
    edited_data["risks"] = edited_risks
    
    return edited_data


def save_edited_charter(charter_file: str, basic_data: dict, goals_data: dict, stakeholders_data: dict, timeline_data: dict):
    """Save the edited charter data"""
    try:
        # Merge all edited data
        merged_data = {}
        merged_data.update(basic_data)
        merged_data.update(goals_data)
        merged_data.update(stakeholders_data)
        merged_data.update(timeline_data)
        
        # Save to file
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