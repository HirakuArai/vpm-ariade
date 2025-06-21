"""
01_create_project.py - Simple Project Creation UI
"""

import streamlit as st
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.project_service import create_project

# Set page config
st.set_page_config(
    page_title="新規プロジェクト作成",
    page_icon="🆕", 
    layout="wide",
    initial_sidebar_state="expanded"
)

st.header("🆕 新規プロジェクト作成")

with st.form("new_project_form"):
    identifier = st.text_input("識別子（空欄で自動生成）", help="プロジェクトの一意識別子、例: project-alpha")
    overview = st.text_input("概要", help="プロジェクトの一行要約")
    submitted = st.form_submit_button("作成")

if submitted and overview:
    try:
        # Use None for identifier if empty, to trigger auto-generation
        proj_id = identifier.strip() if identifier.strip() else None
        proj = create_project(proj_id, overview, created_by="human_user")
        st.success(f"プロジェクト '{proj.identifier}' を DRAFT ステータスで作成しました。")
        st.json(proj.to_dict(), expanded=False)
        
        # Show next steps
        st.info("次のステップ: Kai との会話でプロジェクトチャーターを詳細化してください。")
        
    except Exception as e:
        st.error(f"プロジェクト作成エラー: {str(e)}")
elif submitted:
    st.warning("概要を入力してください。")

# Show existing projects
st.subheader("既存プロジェクト")
projects_dir = Path("data/projects")
if projects_dir.exists():
    project_files = list(projects_dir.glob("*.json"))
    if project_files:
        st.write(f"{len(project_files)} 個のプロジェクトが見つかりました:")
        for project_file in project_files:
            st.write(f"- {project_file.stem}")
    else:
        st.write("プロジェクトが見つかりません。")
else:
    st.write("プロジェクトディレクトリが見つかりません。")