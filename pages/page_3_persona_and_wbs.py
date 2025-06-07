"""
Page 3: Persona Analysis & WBS - Run analysis and display editable results
"""

import streamlit as st
import pandas as pd
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.v2.persona_core import analyze_charter
from core.v2.planning_core import generate_wbs

from libs.ui_layout import (
    setup_page_config, navigation_buttons, error_boundary,
    check_prerequisites, format_persona_results, format_wbs_for_editor,
    save_results_to_json
)


@error_boundary
def show_page():
    """Show the persona analysis and WBS page"""
    setup_page_config("Analysis & WBS", "3️⃣")
    
    st.title("3️⃣ Persona Analysis & Work Breakdown Structure")
    st.markdown("Analyze your charter and generate a detailed work breakdown structure")
    
    # Check prerequisites
    if not check_prerequisites(["selected_charter_file"]):
        st.info("👈 Please create and review a charter first")
        navigation_buttons("3_persona_and_wbs")
        return
    
    charter_file = st.session_state.selected_charter_file
    charter_path = Path(charter_file)
    
    # Show charter file info
    st.info(f"📄 **Analyzing Charter:** {charter_path.name}")
    
    if not charter_path.exists():
        st.error(f"❌ Charter file not found: {charter_file}")
        return
    
    # Analysis buttons
    col1, col2 = st.columns([1, 1])
    
    with col1:
        if st.button("🧠 Run Persona Analysis", type="primary", use_container_width=True):
            run_persona_analysis(charter_file)
    
    with col2:
        if (st.session_state.get("persona_result") and 
            st.button("📋 Generate WBS", use_container_width=True)):
            generate_wbs_analysis()
    
    # Display results
    if st.session_state.get("persona_result"):
        display_persona_analysis()
    
    if st.session_state.get("wbs_result"):
        display_wbs_analysis()
    
    # Save results section
    if st.session_state.get("persona_result") or st.session_state.get("wbs_result"):
        display_save_section(charter_file)
    
    # Navigation
    st.markdown("---")
    navigation_buttons("3_persona_and_wbs")


def run_persona_analysis(charter_file: str):
    """Execute persona analysis"""
    try:
        with st.spinner("🧠 Running persona analysis..."):
            persona_result = analyze_charter(charter_file)
            st.session_state.persona_result = persona_result
            st.session_state.analysis_complete = True
            st.success("✅ Persona analysis completed!")
            st.rerun()
    
    except Exception as e:
        st.error(f"❌ Persona analysis failed: {str(e)}")
        with st.expander("🔍 Debug Details"):
            import traceback
            st.code(traceback.format_exc())


def generate_wbs_analysis():
    """Execute WBS generation"""
    try:
        with st.spinner("📋 Generating Work Breakdown Structure..."):
            persona_result = st.session_state.persona_result
            wbs_result = generate_wbs(persona_result)
            st.session_state.wbs_result = wbs_result
            st.success("✅ WBS generation completed!")
            st.rerun()
    
    except Exception as e:
        st.error(f"❌ WBS generation failed: {str(e)}")
        with st.expander("🔍 Debug Details"):
            import traceback
            st.code(traceback.format_exc())


def display_persona_analysis():
    """Display persona analysis results"""
    persona_result = st.session_state.persona_result
    
    with st.expander("🧠 Persona Analysis Results", expanded=True):
        # Project overview
        st.subheader(f"Project: {persona_result.get('project_name', 'Unknown')}")
        
        # Format results for display
        formatted = format_persona_results(persona_result)
        
        # High priority goals
        if formatted and formatted['goals_df'] is not None:
            st.write("**🎯 High Priority Goals:**")
            st.dataframe(
                formatted['goals_df'],
                use_container_width=True,
                hide_index=True
            )
        
        # Risks
        if formatted and formatted['risks_df'] is not None:
            st.write("**⚠️ Potential Risks:**")
            
            # Make risks editable
            edited_risks_df = st.data_editor(
                formatted['risks_df'],
                use_container_width=True,
                hide_index=True,
                num_rows="dynamic",
                column_config={
                    "risk": st.column_config.TextColumn("Risk", width="medium"),
                    "impact": st.column_config.SelectboxColumn(
                        "Impact", 
                        options=["低", "中", "高"],
                        width="small"
                    ),
                    "suggested_mitigation": st.column_config.TextColumn("Mitigation", width="large")
                },
                key="risks_editor"
            )
            
            # Update session state with edited risks
            if not edited_risks_df.empty:
                st.session_state.persona_result["potential_risks"] = edited_risks_df.to_dict('records')
        
        # Milestones
        if formatted and formatted['milestones_df'] is not None:
            st.write("**📅 Recommended Milestones:**")
            
            # Make milestones editable
            edited_milestones_df = st.data_editor(
                formatted['milestones_df'],
                use_container_width=True,
                hide_index=True,
                num_rows="dynamic",
                column_config={
                    "Due Date": st.column_config.DateColumn("Due Date", width="small"),
                    "Milestone": st.column_config.TextColumn("Milestone", width="large")
                },
                key="milestones_editor"
            )
            
            # Update session state with edited milestones
            if not edited_milestones_df.empty:
                milestones_data = []
                for row in edited_milestones_df.to_dict('records'):
                    due_date = row['Due Date']
                    if hasattr(due_date, 'strftime'):
                        due_str = due_date.strftime('%Y-%m-%d')
                    else:
                        due_str = str(due_date)
                    
                    milestones_data.append({
                        "due": due_str,
                        "title": row['Milestone']
                    })
                
                st.session_state.persona_result["recommended_milestones"] = milestones_data
        
        # Persona comment
        if formatted and formatted['comment']:
            st.write("**💭 AI Persona Comment:**")
            st.info(formatted['comment'])


def display_wbs_analysis():
    """Display WBS analysis results with editable data_editor"""
    wbs_result = st.session_state.wbs_result
    
    with st.expander("📋 Work Breakdown Structure (WBS)", expanded=True):
        if not wbs_result:
            st.warning("No WBS data available")
            return
        
        # Summary statistics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Tasks", len(wbs_result))
        with col2:
            tasks_with_deps = sum(1 for task in wbs_result if task.get('depends_on'))
            st.metric("Tasks with Dependencies", tasks_with_deps)
        with col3:
            # Calculate date range
            from datetime import datetime
            dates = []
            for task in wbs_result:
                try:
                    date_obj = datetime.strptime(task['suggested_due_date'], '%Y-%m-%d')
                    dates.append(date_obj)
                except (ValueError, KeyError):
                    continue
            
            if dates:
                duration_days = (max(dates) - min(dates)).days
                st.metric("Project Duration (days)", duration_days)
        
        # Format WBS for editing
        wbs_df = format_wbs_for_editor(wbs_result)
        
        if not wbs_df.empty:
            st.write("**📝 Editable Task List:**")
            
            # Make WBS editable
            edited_wbs_df = st.data_editor(
                wbs_df,
                use_container_width=True,
                hide_index=True,
                num_rows="dynamic",
                column_config={
                    'ID': st.column_config.NumberColumn("ID", width="small", disabled=True),
                    'Task Name': st.column_config.TextColumn("Task Name", width="medium"),
                    'Description': st.column_config.TextColumn("Description", width="large"),
                    'Due Date': st.column_config.DateColumn("Due Date", width="small"),
                    'Dependencies': st.column_config.TextColumn("Dependencies", width="medium"),
                    'Status': st.column_config.SelectboxColumn(
                        "Status",
                        options=["Pending", "In Progress", "Completed", "Blocked"],
                        width="small"
                    ),
                    'Assigned To': st.column_config.TextColumn("Assigned To", width="small"),
                    'Priority': st.column_config.SelectboxColumn(
                        "Priority",
                        options=["Low", "Medium", "High", "Critical"],
                        width="small"
                    )
                },
                key="wbs_editor"
            )
            
            # Store edited WBS in session state
            st.session_state.edited_wbs_df = edited_wbs_df
            
            # Show task timeline visualization
            if len(wbs_result) > 0:
                st.write("**📊 Task Timeline:**")
                timeline_data = []
                for _, row in edited_wbs_df.iterrows():
                    try:
                        if pd.notna(row['Due Date']):
                            if hasattr(row['Due Date'], 'strftime'):
                                date_obj = row['Due Date']
                            else:
                                date_obj = datetime.strptime(str(row['Due Date']), '%Y-%m-%d')
                            
                            task_name = row['Task Name'][:40] + '...' if len(row['Task Name']) > 40 else row['Task Name']
                            
                            timeline_data.append({
                                'Task': task_name,
                                'Due Date': date_obj,
                                'Priority': row.get('Priority', 'Medium')
                            })
                    except (ValueError, TypeError):
                        continue
                
                if timeline_data:
                    timeline_df = pd.DataFrame(timeline_data)
                    timeline_df = timeline_df.sort_values('Due Date')
                    
                    # Create a simple bar chart
                    st.bar_chart(
                        timeline_df.set_index('Task')['Due Date'],
                        height=400
                    )


def display_save_section(charter_file: str):
    """Display save results section"""
    st.header("💾 Save Analysis Results")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Preview what will be saved
        with st.expander("📄 Preview JSON Output"):
            save_data = {
                "charter_file": charter_file,
                "analysis_timestamp": st.session_state.get("analysis_timestamp", ""),
                "persona_analysis": st.session_state.get("persona_result"),
                "wbs": st.session_state.get("wbs_result")
            }
            
            # Add edited WBS if available
            if st.session_state.get("edited_wbs_df") is not None:
                save_data["edited_wbs"] = st.session_state.edited_wbs_df.to_dict('records')
            
            st.json(save_data, expanded=False)
    
    with col2:
        if st.button("💾 Save Results", type="primary", use_container_width=True):
            save_analysis_results(charter_file)
        
        # Reset analysis button
        if st.button("🔄 Reset Analysis", use_container_width=True):
            reset_analysis_state()
            st.rerun()


def save_analysis_results(charter_file: str):
    """Save analysis results to JSON"""
    try:
        persona_result = st.session_state.get("persona_result")
        wbs_result = st.session_state.get("wbs_result")
        edited_wbs_df = st.session_state.get("edited_wbs_df")
        
        output_path = save_results_to_json(
            charter_file, 
            persona_result, 
            wbs_result, 
            edited_wbs_df
        )
        
        if output_path:
            st.success(f"✅ Results saved successfully!")
            st.info(f"📁 **File:** {output_path}")
            
            # Show file info
            file_size = Path(output_path).stat().st_size
            st.caption(f"File size: {file_size:,} bytes")
        else:
            st.error("❌ Failed to save results")
    
    except Exception as e:
        st.error(f"❌ Error saving results: {str(e)}")


def reset_analysis_state():
    """Reset analysis state"""
    keys_to_reset = [
        "persona_result",
        "wbs_result", 
        "edited_wbs_df",
        "analysis_complete"
    ]
    
    for key in keys_to_reset:
        if key in st.session_state:
            del st.session_state[key]
    
    st.success("🔄 Analysis state reset! You can run new analysis.")