"""
Common UI layout and helper functions for Kai VPM multipage Streamlit app
"""

import streamlit as st
import pandas as pd
import yaml
import json
from datetime import datetime
from pathlib import Path
import traceback
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def setup_page_config(title: str, icon: str = "🌟", layout: str = "wide"):
    """Setup common page configuration"""
    st.set_page_config(
        page_title=f"Kai VPM v2 - {title}",
        page_icon=icon,
        layout=layout,
        initial_sidebar_state="expanded"
    )


def setup_sidebar():
    """Setup common sidebar navigation"""
    with st.sidebar:
        st.title("🌟 Kai VPM v2")
        st.markdown("**AIプロジェクトマネージャー**")
        st.markdown("---")
        
        # Navigation menu
        pages = {
            "1️⃣ 新規プロジェクト": "1_new_project",
            "2️⃣ チャーター確認": "2_preview_charter", 
            "3️⃣ 分析とWBS": "3_persona_and_wbs"
        }
        
        selected_page = st.selectbox(
            "ページ選択:",
            list(pages.keys()),
            index=_get_current_page_index(pages),
            help="移動したいページを選択してください"
        )
        
        # Update session state
        if selected_page:
            st.session_state["current_page"] = pages[selected_page]
        
        st.markdown("---")
        
        # Show current charter info if available
        display_current_charter_info()
        
        # Progress indicator
        display_progress_indicator()
        
        return pages[selected_page]


def _get_current_page_index(pages: dict) -> int:
    """Get the index of current page for selectbox"""
    current_page = st.session_state.get("current_page", "1_new_project")
    page_list = list(pages.values())
    try:
        return page_list.index(current_page)
    except ValueError:
        return 0


def display_current_charter_info():
    """Display information about the currently selected charter"""
    charter_file = st.session_state.get("selected_charter_file")
    
    if charter_file:
        st.write("**現在のチャーター:**")
        charter_path = Path(charter_file)
        st.write(f"📄 {charter_path.name}")
        
        # Show charter basic info
        try:
            with open(charter_path, 'r', encoding='utf-8') as f:
                charter_data = yaml.safe_load(f) or {}
            
            project_name = charter_data.get('name', 'Unknown')
            deadline = charter_data.get('constraints', {}).get('deadline', 'Not set')
            
            st.write(f"**プロジェクト:** {project_name}")
            st.write(f"**期限:** {deadline}")
            
        except Exception:
            st.write("⚠️ チャーター読み込みエラー")
    else:
        st.write("**チャーターが選択されていません**")
        st.write("新しいプロジェクトを作成して始めてください")


def display_progress_indicator():
    """Display progress through the workflow"""
    st.write("**進捗:**")
    
    steps = [
        ("チャーター作成", st.session_state.get("charter_created", False)),
        ("チャーター確認", st.session_state.get("charter_reviewed", False)),
        ("分析完了", st.session_state.get("analysis_complete", False))
    ]
    
    for step_name, completed in steps:
        icon = "✅" if completed else "⏳"
        st.write(f"{icon} {step_name}")


def navigation_buttons(current_page: str):
    """Display navigation buttons at the bottom of pages"""
    col1, col2, col3 = st.columns([1, 1, 1])
    
    # Define page order
    page_order = ["1_new_project", "2_preview_charter", "3_persona_and_wbs"]
    current_index = page_order.index(current_page) if current_page in page_order else 0
    
    with col1:
        if current_index > 0:
            if st.button("⬅️ 前のページ", use_container_width=True):
                st.session_state["current_page"] = page_order[current_index - 1]
                st.rerun()
    
    with col2:
        if st.button("🏠 ホーム", use_container_width=True):
            st.session_state["current_page"] = "1_new_project"
            st.rerun()
    
    with col3:
        if current_index < len(page_order) - 1:
            if st.button("次のページ ➡️", use_container_width=True):
                st.session_state["current_page"] = page_order[current_index + 1]
                st.rerun()


def error_boundary(func):
    """Decorator for error handling in pages"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            st.error("予期しないエラーが発生しました:")
            st.code(traceback.format_exc())
            
            with st.expander("🔍 デバッグ情報"):
                st.write(f"**エラータイプ:** {type(e).__name__}")
                st.write(f"**エラーメッセージ:** {str(e)}")
                st.write(f"**Pythonバージョン:** {sys.version}")
                st.write(f"**作業ディレクトリ:** {Path.cwd()}")
                st.write(f"**セッション状態キー:** {list(st.session_state.keys())}")
    
    return wrapper


def load_charter_data(charter_file: str) -> dict:
    """Load charter data with error handling"""
    try:
        with open(charter_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        st.error(f"チャーター読み込みエラー: {str(e)}")
        return {}


def save_charter_data(charter_file: str, charter_data: dict) -> bool:
    """Save charter data with error handling"""
    try:
        with open(charter_file, 'w', encoding='utf-8') as f:
            yaml.dump(charter_data, f, default_flow_style=False, allow_unicode=True)
        return True
    except Exception as e:
        st.error(f"チャーター保存エラー: {str(e)}")
        return False


def display_charter_overview(charter_data: dict):
    """Display charter overview in a nice format"""
    if not charter_data:
        st.warning("チャーターデータがありません")
        return
    
    with st.expander("📋 チャーター概要", expanded=True):
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.write("**プロジェクト名:**", charter_data.get('name', 'N/A'))
            st.write("**目的:**", charter_data.get('purpose', 'N/A'))
            
            outcomes = charter_data.get('outcomes', [])
            if outcomes:
                st.write("**成果物:**")
                for outcome in outcomes:
                    st.write(f"- {outcome}")
        
        with col2:
            constraints = charter_data.get('constraints', {})
            st.write("**予算:**", constraints.get('budget', 'N/A'))
            st.write("**期限:**", constraints.get('deadline', 'N/A'))
            
            stakeholders = charter_data.get('stakeholders', [])
            if stakeholders:
                st.write("**ステークホルダー:**")
                for stakeholder in stakeholders:
                    if isinstance(stakeholder, dict):
                        name = stakeholder.get('name', 'Unknown')
                        role = stakeholder.get('role', 'Unknown')
                        st.write(f"- {name} ({role})")
                    else:
                        st.write(f"- {stakeholder}")


def format_persona_results(persona_result: dict):
    """Format persona analysis results for display"""
    if not persona_result:
        return None
    
    # High priority goals
    goals_df = None
    goals = persona_result.get('high_priority_goals', [])
    if goals:
        goals_df = pd.DataFrame([{"優先目標": goal} for goal in goals])
    
    # Risks
    risks_df = None
    risks = persona_result.get('potential_risks', [])
    if risks:
        risks_df = pd.DataFrame(risks)
    
    # Milestones
    milestones_df = None
    milestones = persona_result.get('recommended_milestones', [])
    if milestones:
        milestones_df = pd.DataFrame(milestones)
        if not milestones_df.empty and 'title' in milestones_df.columns and 'due' in milestones_df.columns:
            milestones_df = milestones_df[['due', 'title']]
            milestones_df.columns = ['期限', 'マイルストーン']
    
    return {
        'goals_df': goals_df,
        'risks_df': risks_df,
        'milestones_df': milestones_df,
        'comment': persona_result.get('persona_comment', '')
    }


def format_wbs_for_editor(wbs_result: list) -> pd.DataFrame:
    """Format WBS results for st.data_editor"""
    if not wbs_result:
        return pd.DataFrame()
    
    # Prepare data for editing
    edit_data = []
    for i, task in enumerate(wbs_result, 1):
        edit_data.append({
            'ID': i,
            'Task Name': task.get('name', ''),
            'Description': task.get('description', ''),
            'Due Date': task.get('suggested_due_date', ''),
            'Dependencies': ', '.join(task.get('depends_on', [])),
            'Status': '待機中',  # Default status for new tasks
            'Assigned To': '',     # Empty for user to fill
            'Priority': '中'   # Default priority
        })
    
    return pd.DataFrame(edit_data)


def save_results_to_json(charter_file: str, persona_result: dict, wbs_result: list, edited_wbs_df: pd.DataFrame = None) -> str:
    """Save analysis results to JSON file"""
    results_dir = Path("data/results")
    results_dir.mkdir(exist_ok=True)
    
    charter_name = Path(charter_file).stem
    output_filename = f"{charter_name}_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_path = results_dir / output_filename
    
    # Prepare save data
    save_data = {
        "charter_file": str(charter_file),
        "analysis_timestamp": datetime.now().isoformat(),
        "persona_analysis": persona_result,
        "wbs": wbs_result
    }
    
    # Add edited WBS if available
    if edited_wbs_df is not None and not edited_wbs_df.empty:
        save_data["edited_wbs"] = edited_wbs_df.to_dict('records')
    
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2)
        return str(output_path)
    except Exception as e:
        st.error(f"結果の保存に失敗しました: {str(e)}")
        return None


def check_prerequisites(required_keys: list) -> bool:
    """Check if required session state keys exist"""
    missing_keys = [key for key in required_keys if key not in st.session_state or not st.session_state[key]]
    
    if missing_keys:
        st.error(f"必要な前提条件が不足: {', '.join(missing_keys)}")
        st.info("まず前のステップを完了してください。")
        return False
    
    return True


def initialize_session_state():
    """Initialize session state with default values"""
    defaults = {
        "current_page": "1_new_project",
        "selected_charter_file": None,
        "charter_created": False,
        "charter_reviewed": False,
        "analysis_complete": False,
        "persona_result": None,
        "wbs_result": None
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_session_state():
    """Reset session state (useful for starting over)"""
    keys_to_reset = [
        "selected_charter_file",
        "charter_created", 
        "charter_reviewed",
        "analysis_complete",
        "persona_result",
        "wbs_result"
    ]
    
    for key in keys_to_reset:
        if key in st.session_state:
            del st.session_state[key]
    
    st.success("セッションがリセットされました！新しいプロジェクトを始められます。")
    st.rerun()


# Utility functions for charter creation
def get_charter_questions() -> list:
    """Load charter questions from YAML file"""
    try:
        questions_file = Path("data/charter_questions.yaml")
        with open(questions_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        return data.get('questions', [])
    except Exception as e:
        st.error(f"チャーター質問の読み込みに失敗しました: {str(e)}")
        return []


def generate_charter_filename() -> str:
    """Generate a unique charter filename"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"charter_{timestamp}.yaml"