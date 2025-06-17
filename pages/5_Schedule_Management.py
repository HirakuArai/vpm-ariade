# --- pages/5_Schedule_Management.py ---
"""
Schedule Management - スケジュール管理システム
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from pathlib import Path
import sys
import calendar

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.schedule_manager import ScheduleManager, TaskPriority
from core.project_service import list_projects, get_project
from core.progress_monitor import ProgressMonitor

st.set_page_config(
    page_title="Schedule Management",
    page_icon="📅",
    layout="wide"
)

st.title("📅 スケジュール管理システム")

# スケジュールマネージャーの初期化
@st.cache_resource
def get_schedule_manager():
    return ScheduleManager()

schedule_manager = get_schedule_manager()

# === プロジェクト選択 ===
st.header("🎯 プロジェクト選択")

try:
    projects = list_projects()
    active_projects = [p for p in projects if p.get("status") == "ACTIVE"]
    
    if not active_projects:
        st.warning("アクティブなプロジェクトがありません")
        st.stop()
    
    project_options = ["全プロジェクト"] + [f"{p['identifier']} - {p.get('overview', '')[:50]}" for p in active_projects]
    selected_option = st.selectbox("スケジュールを表示するプロジェクトを選択", project_options)
    
except Exception as e:
    st.error(f"プロジェクトの取得に失敗しました: {str(e)}")
    st.stop()

# === 全プロジェクトビュー ===
if selected_option == "全プロジェクト":
    st.header("🌐 全プロジェクトスケジュール概要")
    
    # 今後の期限一覧
    st.subheader("📅 今後の期限 (30日以内)")
    
    try:
        deadlines = schedule_manager.get_upcoming_deadlines(days_ahead=30)
        
        if deadlines:
            # 期限データを整理
            deadline_data = []
            for deadline in deadlines:
                urgency_level = (
                    "緊急" if deadline["days_remaining"] <= 1 
                    else "重要" if deadline["days_remaining"] <= 3 
                    else "通常" if deadline["days_remaining"] <= 7 
                    else "余裕"
                )
                
                deadline_data.append({
                    "プロジェクト": deadline["project_name"][:30],
                    "タスク": deadline["event_title"],
                    "期限": deadline["deadline"],
                    "残り日数": deadline["days_remaining"],
                    "緊急度": urgency_level,
                    "完了率": deadline["completion_percentage"],
                    "優先度": deadline.get("priority", "normal")
                })
            
            deadline_df = pd.DataFrame(deadline_data)
            
            # フィルタリング
            col1, col2 = st.columns(2)
            with col1:
                urgency_filter = st.multiselect(
                    "緊急度でフィルタ",
                    options=["緊急", "重要", "通常", "余裕"],
                    default=["緊急", "重要", "通常", "余裕"]
                )
            with col2:
                priority_filter = st.multiselect(
                    "優先度でフィルタ",
                    options=["urgent", "high", "normal", "low"],
                    default=["urgent", "high", "normal", "low"]
                )
            
            filtered_df = deadline_df[
                (deadline_df["緊急度"].isin(urgency_filter)) & 
                (deadline_df["優先度"].isin(priority_filter))
            ]
            
            # データテーブル表示
            st.dataframe(
                filtered_df.sort_values("残り日数"),
                use_container_width=True
            )
            
            # ガントチャート風の可視化
            if not filtered_df.empty:
                st.subheader("📊 期限タイムライン")
                
                fig = px.scatter(
                    filtered_df,
                    x="期限",
                    y="プロジェクト",
                    size="完了率",
                    color="緊急度",
                    hover_data=["タスク", "残り日数"],
                    color_discrete_map={
                        "緊急": "#FF4444",
                        "重要": "#FF8800", 
                        "通常": "#4488FF",
                        "余裕": "#44AA44"
                    },
                    title="プロジェクト期限一覧"
                )
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("今後30日以内の期限はありません")
    
    except Exception as e:
        st.error(f"期限情報の取得に失敗しました: {str(e)}")
    
    # リソース利用状況
    st.subheader("⚡ リソース利用状況")
    
    try:
        utilization = schedule_manager.get_resource_utilization()
        
        if utilization["overall_utilization"] > 0:
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric(
                    "全体リソース利用率",
                    f"{utilization['overall_utilization']:.1%}",
                    delta=None
                )
            
            with col2:
                st.metric(
                    "ボトルネック数",
                    len(utilization["bottlenecks"]),
                    delta_color="inverse"
                )
            
            # ボトルネック警告
            if utilization["bottlenecks"]:
                st.warning("⚠️ リソースボトルネックが検出されました")
                for bottleneck in utilization["bottlenecks"]:
                    st.write(f"- {bottleneck['resource_id']}: {bottleneck['utilization_rate']:.1%}")
        else:
            st.info("リソース利用データがありません")
    
    except Exception as e:
        st.error(f"リソース情報の取得に失敗しました: {str(e)}")

# === 個別プロジェクトビュー ===
else:
    selected_project_id = selected_option.split(" - ")[0]
    st.header(f"📋 {selected_project_id} - 詳細スケジュール")
    
    try:
        # プロジェクトデータ取得
        project_data = get_project(selected_project_id)
        if not project_data:
            st.error("プロジェクトデータが見つかりません")
            st.stop()
        
        # スケジュール生成・取得
        col1, col2 = st.columns([3, 1])
        with col1:
            st.subheader("🔄 スケジュール操作")
        with col2:
            if st.button("🔄 スケジュール再生成"):
                with st.spinner("スケジュールを生成中..."):
                    schedule = schedule_manager.generate_project_schedule(selected_project_id)
                    st.success("スケジュールを更新しました")
                    st.rerun()
        
        # 既存スケジュールを読み込み
        schedule = schedule_manager._load_schedule(selected_project_id)
        
        if not schedule:
            st.info("スケジュールが見つかりません。スケジュールを生成してください。")
            if st.button("📅 初回スケジュール生成"):
                with st.spinner("スケジュールを生成中..."):
                    schedule = schedule_manager.generate_project_schedule(selected_project_id)
                    st.success("スケジュールを生成しました")
                    st.rerun()
        else:
            # === スケジュール概要 ===
            st.subheader("📊 スケジュール概要")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    "開始日",
                    schedule.get("start_date", "未設定")
                )
            
            with col2:
                st.metric(
                    "完了予定日",
                    schedule.get("estimated_completion", "未設定")
                )
            
            metrics = schedule.get("schedule_metrics", {})
            with col3:
                st.metric(
                    "総タスク数",
                    metrics.get("total_tasks", 0)
                )
            
            with col4:
                st.metric(
                    "完了率",
                    f"{metrics.get('completion_rate', 0):.1%}"
                )
            
            # === タスク一覧 ===
            st.subheader("📋 タスク詳細")
            
            events = schedule.get("events", [])
            if events:
                task_data = []
                for event in events:
                    status_icon = {
                        "completed": "✅",
                        "in_progress": "🟡",
                        "planned": "⚪"
                    }
                    
                    priority_icon = {
                        "urgent": "🔴",
                        "high": "🟠",
                        "normal": "🟡",
                        "low": "🟢"
                    }
                    
                    task_data.append({
                        "ステータス": status_icon.get(event.get("status", "planned"), "⚪"),
                        "タスク名": event.get("title", ""),
                        "開始日": event.get("start_date", ""),
                        "終了日": event.get("end_date", ""),
                        "優先度": priority_icon.get(event.get("priority", "normal"), "🟡"),
                        "完了率": f"{event.get('completion_percentage', 0):.0f}%",
                        "担当者": ", ".join(event.get("assigned_to", []))
                    })
                
                task_df = pd.DataFrame(task_data)
                
                # ステータスフィルタ
                status_filter = st.multiselect(
                    "ステータスでフィルタ",
                    options=["✅", "🟡", "⚪"],
                    default=["✅", "🟡", "⚪"],
                    help="✅=完了, 🟡=進行中, ⚪=計画中"
                )
                
                filtered_task_df = task_df[task_df["ステータス"].isin(status_filter)]
                st.dataframe(filtered_task_df, use_container_width=True)
                
                # ガントチャート
                st.subheader("📈 ガントチャート")
                
                try:
                    # ガントチャート用データ準備
                    gantt_data = []
                    for event in events:
                        if event.get("start_date") and event.get("end_date"):
                            gantt_data.append({
                                "Task": event.get("title", ""),
                                "Start": event.get("start_date"),
                                "Finish": event.get("end_date"),
                                "Resource": ", ".join(event.get("assigned_to", ["未割当"]))
                            })
                    
                    if gantt_data:
                        gantt_df = pd.DataFrame(gantt_data)
                        gantt_df["Start"] = pd.to_datetime(gantt_df["Start"])
                        gantt_df["Finish"] = pd.to_datetime(gantt_df["Finish"])
                        
                        fig = px.timeline(
                            gantt_df,
                            x_start="Start",
                            x_end="Finish", 
                            y="Task",
                            color="Resource",
                            title="プロジェクトガントチャート"
                        )
                        fig.update_layout(height=max(400, len(gantt_data) * 30))
                        st.plotly_chart(fig, use_container_width=True)
                
                except Exception as e:
                    st.error(f"ガントチャートの表示に失敗しました: {str(e)}")
            
            # === マイルストーン ===
            st.subheader("🎯 マイルストーン")
            
            milestones = schedule.get("milestones", [])
            if milestones:
                milestone_data = []
                for milestone in milestones:
                    milestone_data.append({
                        "マイルストーン": milestone.get("title", ""),
                        "日付": milestone.get("date", ""),
                        "説明": milestone.get("description", ""),
                        "目標完了率": f"{milestone.get('target_completion', 0)}%"
                    })
                
                milestone_df = pd.DataFrame(milestone_data)
                st.dataframe(milestone_df, use_container_width=True)
            else:
                st.info("マイルストーンが設定されていません")
            
            # === クリティカルパス ===
            st.subheader("🔴 クリティカルパス")
            
            critical_path = schedule.get("critical_path", [])
            if critical_path:
                st.write("以下のタスクがクリティカルパスです：")
                for i, task_id in enumerate(critical_path):
                    # task_idに対応するタスク名を検索
                    task_name = task_id
                    for event in events:
                        if event.get("id") == task_id:
                            task_name = event.get("title", task_id)
                            break
                    st.write(f"{i+1}. {task_name}")
            else:
                st.info("クリティカルパスが特定されていません")
            
            # === 推奨事項 ===
            st.subheader("💡 スケジュール推奨事項")
            
            try:
                recommendations = schedule_manager.generate_schedule_recommendations(selected_project_id)
                
                if recommendations:
                    for rec in recommendations:
                        priority_color = {
                            95: "🔴",
                            90: "🟠", 
                            80: "🟡",
                            70: "🟢"
                        }
                        
                        priority_icon = priority_color.get(rec.priority, "🔵")
                        
                        with st.expander(f"{priority_icon} {rec.title}"):
                            st.write(f"**説明**: {rec.description}")
                            st.write(f"**影響**: {rec.impact}")
                            st.write("**推奨アクション**:")
                            for action in rec.suggested_actions:
                                st.write(f"• {action}")
                else:
                    st.success("現在特別な推奨事項はありません 🎉")
            
            except Exception as e:
                st.error(f"推奨事項の生成に失敗しました: {str(e)}")
    
    except Exception as e:
        st.error(f"スケジュール情報の取得に失敗しました: {str(e)}")

# === スケジュール競合チェック ===
st.header("⚠️ スケジュール競合チェック")

if st.button("🔍 競合をチェック"):
    try:
        with st.spinner("競合をチェック中..."):
            conflicts = schedule_manager.check_schedule_conflicts()
        
        if conflicts:
            st.warning(f"{len(conflicts)}件の競合が検出されました")
            
            for conflict in conflicts:
                severity_icon = {
                    "high": "🔴",
                    "medium": "🟡",
                    "low": "🟢"
                }
                
                with st.expander(f"{severity_icon.get(conflict.severity, '⚪')} {conflict.description}"):
                    st.write(f"**競合タイプ**: {conflict.conflict_type}")
                    st.write(f"**影響プロジェクト**: {', '.join(conflict.affected_projects)}")
                    st.write(f"**検出日時**: {conflict.detected_at[:16]}")
                    st.write("**推奨対応策**:")
                    for suggestion in conflict.suggestions:
                        st.write(f"• {suggestion}")
        else:
            st.success("競合は検出されませんでした 🎉")
    
    except Exception as e:
        st.error(f"競合チェックに失敗しました: {str(e)}")

st.caption("📅 Schedule Management v1.0 - 統合スケジュール管理システム")