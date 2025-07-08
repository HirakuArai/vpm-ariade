# --- pages/4_Progress_Dashboard.py ---
"""
Progress Monitoring Dashboard - リアルタイム進捗モニタリング
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.progress_monitor import ProgressMonitor, AlertLevel
from core.project_service import list_projects
from core.schedule_manager import ScheduleManager

# JST timezone
JST = ZoneInfo("Asia/Tokyo")

def utc_to_jst_string(utc_timestamp_str):
    """UTC timestamp string を JST の文字列に変換"""
    try:
        # ISO format の UTC timestamp をパース
        if utc_timestamp_str.endswith('Z'):
            utc_timestamp_str = utc_timestamp_str[:-1] + '+00:00'
        
        utc_dt = datetime.fromisoformat(utc_timestamp_str)
        
        # UTC timezone を明示的に設定（naive datetime の場合）
        if utc_dt.tzinfo is None:
            utc_dt = utc_dt.replace(tzinfo=timezone.utc)
        
        # JST に変換
        jst_dt = utc_dt.astimezone(JST)
        
        # YYYY-MM-DD HH:MM:SS 形式で返す
        return jst_dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception as e:
        # フォールバック: 元の文字列を返す
        return utc_timestamp_str
from core.notification_system import NotificationSystem

st.set_page_config(
    page_title="Progress Dashboard",
    page_icon="📊",
    layout="wide"
)

st.title("📊 プロジェクト進捗ダッシュボード")

# プロジェクト監視システムの初期化
@st.cache_resource
def get_monitoring_systems():
    return {
        'progress_monitor': ProgressMonitor(),
        'schedule_manager': ScheduleManager(),
        'notification_system': NotificationSystem()
    }

systems = get_monitoring_systems()
progress_monitor = systems['progress_monitor']
schedule_manager = systems['schedule_manager']
notification_system = systems['notification_system']

# === 全体サマリー ===
st.header("🌟 全体プロジェクト状況")

try:
    # 全プロジェクトの健康状態サマリー
    health_summary = progress_monitor.get_project_health_summary()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "総プロジェクト数", 
            health_summary["total_projects"]
        )
    
    with col2:
        st.metric(
            "健康なプロジェクト", 
            health_summary["health_distribution"]["healthy"],
            delta=None
        )
    
    with col3:
        st.metric(
            "注意が必要", 
            health_summary["health_distribution"]["at_risk"] + health_summary["health_distribution"]["critical"],
            delta=health_summary["health_distribution"]["critical"],
            delta_color="inverse"
        )
    
    with col4:
        st.metric(
            "総アラート数", 
            health_summary["total_alerts"],
            delta=health_summary["critical_alerts"],
            delta_color="inverse"
        )
    
    # 健康状態分布チャート
    if health_summary["total_projects"] > 0:
        fig_health = px.pie(
            values=list(health_summary["health_distribution"].values()),
            names=["Healthy", "At Risk", "Critical"],
            title="プロジェクト健康状態分布",
            color_discrete_map={
                "Healthy": "#00CC88",
                "At Risk": "#FFB84D", 
                "Critical": "#FF6B6B"
            }
        )
        st.plotly_chart(fig_health, use_container_width=True)

except Exception as e:
    st.error(f"全体サマリーの取得に失敗しました: {str(e)}")

# === プロジェクト別詳細 ===
st.header("📋 プロジェクト別詳細")

try:
    # アクティブプロジェクトの取得
    projects = list_projects()
    active_projects = [p for p in projects if p.get("status") == "ACTIVE"]
    
    if not active_projects:
        st.info("アクティブなプロジェクトがありません")
    else:
        # プロジェクト選択
        project_options = [f"{p['identifier']} - {p.get('overview', '')[:50]}" for p in active_projects]
        selected_project_display = st.selectbox("詳細を表示するプロジェクトを選択", project_options)
        
        if selected_project_display:
            # 選択されたプロジェクトのIDを取得
            selected_project_id = selected_project_display.split(" - ")[0]
            
            # プロジェクト詳細レポートを生成
            try:
                report = progress_monitor.monitor_project(selected_project_id)
                
                # === プロジェクト概要 ===
                st.subheader(f"🎯 {selected_project_id} - 概要")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    health_color = {
                        "healthy": "🟢",
                        "at_risk": "🟡",
                        "critical": "🔴"
                    }
                    st.metric(
                        "健康状態", 
                        f"{health_color.get(report.overall_health, '⚪')} {report.overall_health}"
                    )
                
                with col2:
                    st.metric(
                        "完了率", 
                        f"{report.completion_percentage:.1f}%"
                    )
                
                with col3:
                    st.metric(
                        "リスクスコア", 
                        f"{report.metrics.get('risk_score', 0):.2f}"
                    )
                
                # === タスク進捗チャート ===
                st.subheader("📈 タスク進捗")
                
                if report.task_summary:
                    task_data = report.task_summary
                    
                    # タスク状況バーチャート
                    task_status_df = pd.DataFrame([
                        {"Status": "完了", "Count": task_data.get("completed", 0), "Color": "#00CC88"},
                        {"Status": "未完了", "Count": task_data.get("pending", 0), "Color": "#4A90E2"},
                        {"Status": "遅延", "Count": task_data.get("overdue", 0), "Color": "#FF6B6B"}
                    ])
                    
                    fig_tasks = px.bar(
                        task_status_df, 
                        x="Status", 
                        y="Count", 
                        color="Status",
                        color_discrete_map={
                            "完了": "#00CC88",
                            "未完了": "#4A90E2", 
                            "遅延": "#FF6B6B"
                        },
                        title="タスク状況"
                    )
                    st.plotly_chart(fig_tasks, use_container_width=True)
                
                # === アラート一覧 ===
                st.subheader("⚠️ アラート")
                
                if report.alerts:
                    alert_data = []
                    for alert in report.alerts:
                        alert_data.append({
                            "レベル": alert.level.value,
                            "タイトル": alert.title,
                            "説明": alert.description,
                            "影響": alert.impact,
                            "作成日時": utc_to_jst_string(alert.created_at)
                        })
                    
                    alert_df = pd.DataFrame(alert_data)
                    
                    # レベル別でフィルタリング
                    level_filter = st.multiselect(
                        "アラートレベルでフィルタ",
                        options=["critical", "warning", "info"],
                        default=["critical", "warning", "info"]
                    )
                    
                    filtered_alerts = alert_df[alert_df["レベル"].isin(level_filter)]
                    st.dataframe(filtered_alerts, use_container_width=True)
                    
                    # 推奨アクション
                    if not filtered_alerts.empty:
                        st.subheader("💡 推奨アクション")
                        for alert in report.alerts[:3]:  # 最大3件の推奨を表示
                            if alert.level.value in level_filter:
                                with st.expander(f"🔧 {alert.title} - 対応策"):
                                    for rec in alert.recommendations:
                                        st.write(f"• {rec}")
                else:
                    st.success("現在アラートはありません 🎉")
                
                # === 完了予測 ===
                if report.predictions:
                    st.subheader("🔮 完了予測")
                    
                    predictions = report.predictions
                    if "estimated_completion_date" in predictions:
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.metric(
                                "完了予定日",
                                predictions["estimated_completion_date"][:10]
                            )
                        
                        with col2:
                            st.metric(
                                "残り日数",
                                f"{predictions.get('estimated_days_remaining', 0)}日"
                            )
                        
                        with col3:
                            confidence_color = {
                                "high": "🟢",
                                "medium": "🟡", 
                                "low": "🔴"
                            }
                            confidence = predictions.get("confidence", "low")
                            st.metric(
                                "予測信頼度",
                                f"{confidence_color.get(confidence, '⚪')} {confidence}"
                            )
                
            except Exception as e:
                st.error(f"プロジェクト {selected_project_id} の監視に失敗しました: {str(e)}")

except Exception as e:
    st.error(f"プロジェクト詳細の取得に失敗しました: {str(e)}")

# === 今後の期限 ===
st.header("📅 今後の期限")

try:
    deadlines = schedule_manager.get_upcoming_deadlines(days_ahead=14)
    
    if deadlines:
        deadline_data = []
        for deadline in deadlines:
            urgency = "🔴" if deadline["days_remaining"] <= 1 else "🟡" if deadline["days_remaining"] <= 3 else "🟢"
            deadline_data.append({
                "緊急度": urgency,
                "プロジェクト": deadline["project_name"][:30],
                "タスク": deadline["event_title"],
                "期限": deadline["deadline"],
                "残り日数": deadline["days_remaining"],
                "完了率": f"{deadline['completion_percentage']:.0f}%"
            })
        
        deadline_df = pd.DataFrame(deadline_data)
        st.dataframe(deadline_df, use_container_width=True)
        
        # 期限チャート
        fig_timeline = px.scatter(
            deadline_df, 
            x="期限", 
            y="プロジェクト",
            size="残り日数",
            color="残り日数",
            hover_data=["タスク", "完了率"],
            title="期限タイムライン"
        )
        st.plotly_chart(fig_timeline, use_container_width=True)
    else:
        st.info("今後14日以内の期限はありません")

except Exception as e:
    st.error(f"期限情報の取得に失敗しました: {str(e)}")

# === リアルタイム更新 ===
st.header("🔄 リアルタイム更新")

# 自動更新機能
auto_refresh = st.checkbox("自動更新 (30秒間隔)")

if auto_refresh:
    # Streamlitの自動更新
    import time
    time.sleep(30)
    st.rerun()

# 手動更新ボタン
if st.button("🔄 今すぐ更新"):
    st.rerun()

st.caption("📊 Progress Dashboard v1.0 - リアルタイム監視システム")