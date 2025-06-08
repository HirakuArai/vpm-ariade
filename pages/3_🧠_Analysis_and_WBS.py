"""
🧠 Analysis and WBS - AI-powered analysis and work breakdown structure
"""

import streamlit as st

# Set page config first, before any other Streamlit commands
st.set_page_config(
    page_title="Kai VPM v2 - 分析とWBS",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

import pandas as pd
from pathlib import Path
import sys
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.v2.persona_core import analyze_charter
from core.v2.planning_core import generate_wbs

from libs.ui_layout import (
    format_persona_results, format_wbs_for_editor, save_results_to_json
)

# Main page content
st.title("🧠 分析と作業分解構造")
st.markdown("AI による分析と詳細な作業分解構造の生成")

# Check prerequisites
charter_file = st.session_state.get("selected_charter_file")

if not charter_file:
    st.info("👈 まずチャーターを作成・確認してください")
    st.stop()

charter_path = Path(charter_file)

# Show charter file info
st.info(f"📄 **分析対象チャーター:** {charter_path.name}")

if not charter_path.exists():
    st.error(f"❌ チャーターファイルが見つかりません: {charter_file}")
    st.stop()

# Analysis buttons
col1, col2 = st.columns([1, 1])

with col1:
    if st.button("🧠 ペルソナ分析実行", type="primary", use_container_width=True):
        try:
            with st.spinner("🧠 ペルソナ分析実行中..."):
                persona_result = analyze_charter(str(charter_path))
                st.session_state.persona_result = persona_result
                st.session_state.analysis_complete = True
                st.success("✅ ペルソナ分析が完了しました！")
                st.rerun()
        except Exception as e:
            st.error(f"❌ ペルソナ分析に失敗しました: {str(e)}")
            with st.expander("🔍 デバッグ詳細"):
                import traceback
                st.code(traceback.format_exc())

with col2:
    if (st.session_state.get("persona_result") and 
        st.button("📋 WBS生成", use_container_width=True)):
        try:
            with st.spinner("📋 作業分解構造生成中..."):
                persona_result = st.session_state.persona_result
                wbs_result = generate_wbs(persona_result)
                st.session_state.wbs_result = wbs_result
                st.success("✅ WBS生成が完了しました！")
                st.rerun()
        except Exception as e:
            st.error(f"❌ WBS生成に失敗しました: {str(e)}")
            with st.expander("🔍 デバッグ詳細"):
                import traceback
                st.code(traceback.format_exc())

# Display results
if st.session_state.get("persona_result"):
    persona_result = st.session_state.persona_result
    
    with st.expander("🧠 ペルソナ分析結果", expanded=True):
        # Project overview
        st.subheader(f"プロジェクト: {persona_result.get('project_name', '不明')}")
        
        # Format results for display
        formatted = format_persona_results(persona_result)
        
        # High priority goals
        if formatted and formatted['goals_df'] is not None:
            st.write("**🎯 高優先度目標:**")
            st.dataframe(
                formatted['goals_df'],
                use_container_width=True,
                hide_index=True
            )
        
        # Risks
        if formatted and formatted['risks_df'] is not None:
            st.write("**⚠️ 潜在的リスク:**")
            
            # Make risks editable
            edited_risks_df = st.data_editor(
                formatted['risks_df'],
                use_container_width=True,
                hide_index=True,
                num_rows="dynamic",
                column_config={
                    "risk": st.column_config.TextColumn("リスク", width="medium"),
                    "impact": st.column_config.SelectboxColumn(
                        "影響度", 
                        options=["低", "中", "高"],
                        width="small"
                    ),
                    "suggested_mitigation": st.column_config.TextColumn("対策", width="large")
                },
                key="risks_editor"
            )
            
            # Update session state with edited risks
            if not edited_risks_df.empty:
                st.session_state.persona_result["potential_risks"] = edited_risks_df.to_dict('records')
        
        # Milestones
        if formatted and formatted['milestones_df'] is not None:
            st.write("**📅 推奨マイルストーン:**")
            
            # Make milestones editable
            edited_milestones_df = st.data_editor(
                formatted['milestones_df'],
                use_container_width=True,
                hide_index=True,
                num_rows="dynamic",
                column_config={
                    "Due Date": st.column_config.DateColumn("期限", width="small"),
                    "Milestone": st.column_config.TextColumn("マイルストーン", width="large")
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
                        "title": row['マイルストーン']
                    })
                
                st.session_state.persona_result["recommended_milestones"] = milestones_data
        
        # Persona comment
        if formatted and formatted['comment']:
            st.write("**💭 AIペルソナコメント:**")
            st.info(formatted['comment'])

if st.session_state.get("wbs_result"):
    wbs_result = st.session_state.wbs_result
    
    with st.expander("📋 作業分解構造 (WBS)", expanded=True):
        if not wbs_result:
            st.warning("WBSデータがありません")
        else:
            # Summary statistics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("総タスク数", len(wbs_result))
            with col2:
                tasks_with_deps = sum(1 for task in wbs_result if task.get('depends_on'))
                st.metric("依存関係のあるタスク", tasks_with_deps)
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
                    st.metric("プロジェクト期間（日数）", duration_days)
            
            # Format WBS for editing
            wbs_df = format_wbs_for_editor(wbs_result)
            
            if not wbs_df.empty:
                st.write("**📝 編集可能タスクリスト:**")
                
                # Make WBS editable
                edited_wbs_df = st.data_editor(
                    wbs_df,
                    use_container_width=True,
                    hide_index=True,
                    num_rows="dynamic",
                    column_config={
                        'ID': st.column_config.NumberColumn("ID", width="small", disabled=True),
                        'Task Name': st.column_config.TextColumn("タスク名", width="medium"),
                        'Description': st.column_config.TextColumn("説明", width="large"),
                        'Due Date': st.column_config.DateColumn("期限", width="small"),
                        'Dependencies': st.column_config.TextColumn("依存関係", width="medium"),
                        'Status': st.column_config.SelectboxColumn(
                            "ステータス",
                            options=["待機中", "進行中", "完了", "ブロック"],
                            width="small"
                        ),
                        'Assigned To': st.column_config.TextColumn("担当者", width="small"),
                        'Priority': st.column_config.SelectboxColumn(
                            "優先度",
                            options=["低", "中", "高", "緊急"],
                            width="small"
                        )
                    },
                    key="wbs_editor"
                )
                
                # Store edited WBS in session state
                st.session_state.edited_wbs_df = edited_wbs_df
                
                # Show task timeline visualization
                if len(wbs_result) > 0:
                    st.write("**📊 タスクタイムライン:**")
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

# Save results section
if st.session_state.get("persona_result") or st.session_state.get("wbs_result"):
    st.header("💾 分析結果を保存")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Preview what will be saved
        with st.expander("📄 JSON出力プレビュー"):
            save_data = {
                "charter_file": str(charter_file),
                "analysis_timestamp": datetime.now().isoformat(),
                "persona_analysis": st.session_state.get("persona_result"),
                "wbs": st.session_state.get("wbs_result")
            }
            
            # Add edited WBS if available
            if st.session_state.get("edited_wbs_df") is not None:
                save_data["edited_wbs"] = st.session_state.edited_wbs_df.to_dict('records')
            
            st.json(save_data, expanded=False)
    
    with col2:
        if st.button("💾 結果を保存", type="primary", use_container_width=True):
            try:
                persona_result = st.session_state.get("persona_result")
                wbs_result = st.session_state.get("wbs_result")
                edited_wbs_df = st.session_state.get("edited_wbs_df")
                
                output_path = save_results_to_json(
                    str(charter_file), 
                    persona_result, 
                    wbs_result, 
                    edited_wbs_df
                )
                
                if output_path:
                    st.success(f"✅ 結果が正常に保存されました！")
                    st.info(f"📁 **ファイル:** {output_path}")
                    
                    # Show file info
                    file_size = Path(output_path).stat().st_size
                    st.caption(f"ファイルサイズ: {file_size:,} バイト")
                else:
                    st.error("❌ 結果の保存に失敗しました")
            except Exception as e:
                st.error(f"❌ 結果保存エラー: {str(e)}")
        
        # Reset analysis button
        if st.button("🔄 分析をリセット", use_container_width=True):
            keys_to_reset = [
                "persona_result",
                "wbs_result", 
                "edited_wbs_df",
                "analysis_complete"
            ]
            
            for key in keys_to_reset:
                if key in st.session_state:
                    del st.session_state[key]
            
            st.success("🔄 分析状態がリセットされました！新しい分析を実行できます。")
            st.rerun()