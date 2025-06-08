"""
Streamlit UI for Kai VPM v2
Charter analysis and WBS generation interface
"""

import streamlit as st
import pandas as pd
import json
from pathlib import Path
from datetime import datetime
import traceback
import sys

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.v2.persona_core import analyze_charter
from core.v2.planning_core import generate_wbs


def main():
    """Main Streamlit application"""
    st.set_page_config(
        page_title="Kai VPM v2 - Project Charter Analysis",
        page_icon="🌟",
        layout="wide"
    )
    
    st.title("🌟 Kai VPM v2 - Project Charter Analysis")
    st.markdown("---")
    
    # Initialize session state
    if 'persona_result' not in st.session_state:
        st.session_state.persona_result = None
    if 'wbs_result' not in st.session_state:
        st.session_state.wbs_result = None
    if 'selected_charter' not in st.session_state:
        st.session_state.selected_charter = None
    
    # Charter file selection
    charter_file = select_charter_file()
    
    if charter_file:
        # Display charter info
        display_charter_info(charter_file)
        
        # Analysis section
        col1, col2 = st.columns([1, 1])
        
        with col1:
            if st.button("🧠 Analyze Charter", type="primary", use_container_width=True):
                analyze_charter_ui(charter_file)
        
        with col2:
            if st.session_state.persona_result and st.button("📋 Generate WBS", use_container_width=True):
                generate_wbs_ui()
        
        # Results display
        if st.session_state.persona_result:
            display_persona_results()
        
        if st.session_state.wbs_result:
            display_wbs_results()
        
        # Save results section
        if st.session_state.persona_result or st.session_state.wbs_result:
            save_results_ui(charter_file)


def select_charter_file():
    """Charter file selection interface"""
    st.header("📋 Charter File Selection")
    
    charters_dir = Path("data/charters")
    
    # Check if directory exists
    if not charters_dir.exists():
        st.error(f"Charter directory not found: {charters_dir}")
        st.info("Please create the directory and add charter YAML files")
        return None
    
    # Get available charter files
    charter_files = list(charters_dir.glob("*.yaml")) + list(charters_dir.glob("*.yml"))
    
    if not charter_files:
        st.warning("No charter files found in data/charters/")
        st.info("Create charter files using: `python scripts/gen_charter.py`")
        return None
    
    # File selection
    charter_names = [f.name for f in charter_files]
    selected_name = st.selectbox(
        "Select a charter file:",
        charter_names,
        help="Choose a YAML charter file to analyze"
    )
    
    if selected_name:
        selected_file = charters_dir / selected_name
        st.session_state.selected_charter = selected_file
        return selected_file
    
    return None


def display_charter_info(charter_file):
    """Display basic charter information"""
    try:
        import yaml
        with open(charter_file, 'r', encoding='utf-8') as f:
            charter_data = yaml.safe_load(f)
        
        with st.expander("📄 Charter Overview", expanded=True):
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.write("**Project Name:**", charter_data.get('name', 'N/A'))
                st.write("**Purpose:**", charter_data.get('purpose', 'N/A'))
                
                outcomes = charter_data.get('outcomes', [])
                if outcomes:
                    st.write("**Outcomes:**")
                    for outcome in outcomes:
                        st.write(f"- {outcome}")
            
            with col2:
                constraints = charter_data.get('constraints', {})
                st.write("**Budget:**", constraints.get('budget', 'N/A'))
                st.write("**Deadline:**", constraints.get('deadline', 'N/A'))
                
                stakeholders = charter_data.get('stakeholders', [])
                if stakeholders:
                    st.write("**Stakeholders:**")
                    for stakeholder in stakeholders:
                        if isinstance(stakeholder, dict):
                            name = stakeholder.get('name', 'Unknown')
                            role = stakeholder.get('role', 'Unknown')
                            st.write(f"- {name} ({role})")
                        else:
                            st.write(f"- {stakeholder}")
    
    except Exception as e:
        st.error(f"Error reading charter file: {str(e)}")


def analyze_charter_ui(charter_file):
    """Execute charter analysis and update UI"""
    try:
        with st.spinner("Analyzing charter..."):
            persona_result = analyze_charter(str(charter_file))
            st.session_state.persona_result = persona_result
            st.success("✅ Charter analysis completed!")
    
    except Exception as e:
        st.error(f"❌ Analysis failed: {str(e)}")
        st.code(traceback.format_exc())


def generate_wbs_ui():
    """Execute WBS generation and update UI"""
    try:
        with st.spinner("Generating Work Breakdown Structure..."):
            wbs_result = generate_wbs(st.session_state.persona_result)
            st.session_state.wbs_result = wbs_result
            st.success("✅ WBS generation completed!")
    
    except Exception as e:
        st.error(f"❌ WBS generation failed: {str(e)}")
        st.code(traceback.format_exc())


def display_persona_results():
    """Display persona analysis results"""
    persona_result = st.session_state.persona_result
    
    with st.expander("🧠 Persona Analysis Results", expanded=True):
        # Project overview
        st.subheader(f"Project: {persona_result.get('project_name', 'Unknown')}")
        
        # High priority goals
        goals = persona_result.get('high_priority_goals', [])
        if goals:
            st.write("**🎯 High Priority Goals:**")
            for i, goal in enumerate(goals, 1):
                st.write(f"{i}. {goal}")
        
        # Risks
        risks = persona_result.get('potential_risks', [])
        if risks:
            st.write("**⚠️ Potential Risks:**")
            risk_df = pd.DataFrame(risks)
            if not risk_df.empty:
                st.dataframe(
                    risk_df,
                    use_container_width=True,
                    hide_index=True
                )
        
        # Recommended milestones
        milestones = persona_result.get('recommended_milestones', [])
        if milestones:
            st.write("**📅 Recommended Milestones:**")
            milestone_df = pd.DataFrame(milestones)
            if not milestone_df.empty:
                # Reorder columns for better display
                if 'title' in milestone_df.columns and 'due' in milestone_df.columns:
                    milestone_df = milestone_df[['due', 'title']]
                    milestone_df.columns = ['Due Date', 'Milestone']
                st.dataframe(
                    milestone_df,
                    use_container_width=True,
                    hide_index=True
                )
        
        # Persona comment
        comment = persona_result.get('persona_comment', '')
        if comment:
            st.write("**💭 AI Persona Comment:**")
            st.info(comment)


def display_wbs_results():
    """Display WBS results"""
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
        
        # Task list as DataFrame
        st.write("**📝 Task List:**")
        
        # Prepare data for display
        display_data = []
        for i, task in enumerate(wbs_result, 1):
            display_data.append({
                '#': i,
                'Task Name': task.get('name', ''),
                'Description': task.get('description', ''),
                'Due Date': task.get('suggested_due_date', ''),
                'Dependencies': ', '.join(task.get('depends_on', [])) if task.get('depends_on') else 'None'
            })
        
        if display_data:
            wbs_df = pd.DataFrame(display_data)
            st.dataframe(
                wbs_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    '#': st.column_config.NumberColumn(width="small"),
                    'Task Name': st.column_config.TextColumn(width="medium"),
                    'Description': st.column_config.TextColumn(width="large"),
                    'Due Date': st.column_config.DateColumn(width="small"),
                    'Dependencies': st.column_config.TextColumn(width="medium")
                }
            )
        
        # Task timeline visualization
        if len(wbs_result) > 0:
            st.write("**📊 Task Timeline:**")
            timeline_data = []
            for task in wbs_result:
                try:
                    date_obj = datetime.strptime(task['suggested_due_date'], '%Y-%m-%d')
                    timeline_data.append({
                        'Task': task['name'][:50] + '...' if len(task['name']) > 50 else task['name'],
                        'Due Date': date_obj
                    })
                except (ValueError, KeyError):
                    continue
            
            if timeline_data:
                timeline_df = pd.DataFrame(timeline_data)
                timeline_df = timeline_df.sort_values('Due Date')
                st.bar_chart(
                    timeline_df.set_index('Task')['Due Date'],
                    height=400
                )


def save_results_ui(charter_file):
    """Save results interface"""
    st.header("💾 Save Results")
    
    # Create results directory if needed
    results_dir = Path("data/results")
    results_dir.mkdir(exist_ok=True)
    
    # Generate output filename
    charter_name = charter_file.stem  # filename without extension
    output_filename = f"{charter_name}_analysis.json"
    output_path = results_dir / output_filename
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.write(f"**Output file:** `{output_path}`")
        
        # Preview what will be saved
        save_data = {
            "charter_file": str(charter_file),
            "analysis_timestamp": datetime.now().isoformat(),
            "persona_analysis": st.session_state.persona_result,
            "wbs": st.session_state.wbs_result
        }
        
        with st.expander("Preview JSON Output"):
            st.json(save_data, expanded=False)
    
    with col2:
        if st.button("💾 Save to JSON", type="primary", use_container_width=True):
            try:
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(save_data, f, ensure_ascii=False, indent=2)
                
                st.success(f"✅ Results saved to {output_path}")
                
                # Show file info
                file_size = output_path.stat().st_size
                st.info(f"File size: {file_size:,} bytes")
                
            except Exception as e:
                st.error(f"❌ Failed to save: {str(e)}")


def handle_errors():
    """Global error handling"""
    try:
        main()
    except Exception as e:
        st.error("An unexpected error occurred:")
        st.code(traceback.format_exc())
        
        st.write("**Debugging Information:**")
        st.write(f"- Error type: {type(e).__name__}")
        st.write(f"- Error message: {str(e)}")
        st.write(f"- Python version: {sys.version}")
        st.write(f"- Working directory: {Path.cwd()}")


if __name__ == "__main__":
    handle_errors()