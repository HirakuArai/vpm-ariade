# --- pages/6_System_Monitor.py ---
"""
System Monitor - システム監視ダッシュボード
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

from core.health_check import HealthChecker

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

st.set_page_config(
    page_title="System Monitor",
    page_icon="⚡",
    layout="wide"
)

st.title("⚡ システム監視ダッシュボード")

# ヘルスチェッカーの初期化
@st.cache_resource
def get_health_checker():
    return HealthChecker()

health_checker = get_health_checker()

# === リアルタイムステータス ===
st.header("🔍 リアルタイムシステム状態")

# ヘルスチェック実行
if st.button("🔄 ヘルスチェック実行") or st.session_state.get("auto_refresh", False):
    with st.spinner("システム状態をチェック中..."):
        health = health_checker.check_system_health()
        st.session_state["last_health_check"] = health

# 最新のヘルスチェック結果を表示
if "last_health_check" in st.session_state:
    health = st.session_state["last_health_check"]
    
    # 全体ステータス
    status_colors = {
        "healthy": "🟢",
        "degraded": "🟡",
        "unhealthy": "🔴"
    }
    
    st.subheader(f"{status_colors.get(health.overall_status, '⚪')} 全体ステータス: {health.overall_status.upper()}")
    
    # コンポーネント別ステータス
    st.subheader("📋 コンポーネント別状態")
    
    status_data = []
    for component in health.components:
        status_data.append({
            "コンポーネント": component.component,
            "ステータス": f"{status_colors.get(component.status, '⚪')} {component.status}",
            "メッセージ": component.message,
            "チェック時刻": utc_to_jst_string(component.checked_at)
        })
    
    status_df = pd.DataFrame(status_data)
    st.dataframe(status_df, use_container_width=True)
    
    # 詳細情報
    st.subheader("📊 詳細情報")
    
    for component in health.components:
        with st.expander(f"🔧 {component.component} - 詳細"):
            st.write(f"**ステータス**: {component.status}")
            st.write(f"**メッセージ**: {component.message}")
            st.write(f"**チェック時刻**: {component.checked_at}")
            
            if component.details:
                st.write("**詳細データ**:")
                for key, value in component.details.items():
                    if isinstance(value, (int, float)):
                        if key.endswith("_percent"):
                            st.metric(key, f"{value:.1f}%")
                        elif key.endswith("_gb"):
                            st.metric(key, f"{value:.2f} GB")
                        elif key.endswith("_mb"):
                            st.metric(key, f"{value:.1f} MB")
                        else:
                            st.metric(key, value)
                    else:
                        st.write(f"- **{key}**: {value}")

else:
    st.info("ヘルスチェックを実行してシステム状態を確認してください")

# === システムメトリクス ===
st.header("📈 システムメトリクス")

if "last_health_check" in st.session_state:
    metrics = st.session_state["last_health_check"].metrics
    
    if metrics and "error" not in metrics:
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "稼働時間",
                f"{metrics.get('uptime_hours', 0):.1f} 時間"
            )
        
        with col2:
            st.metric(
                "プロセスメモリ",
                f"{metrics.get('process_memory_mb', 0):.1f} MB"
            )
        
        with col3:
            st.metric(
                "プロセスCPU",
                f"{metrics.get('process_cpu_percent', 0):.1f}%"
            )
        
        with col4:
            st.metric(
                "スレッド数",
                metrics.get('total_threads', 0)
            )
        
        # システム負荷（Linuxの場合のみ）
        if metrics.get('system_load') is not None:
            st.metric("システム負荷", f"{metrics['system_load']:.2f}")

# === 履歴とトレンド ===
st.header("📊 履歴とトレンド")

try:
    # 24時間の履歴を取得
    history = health_checker.get_health_history(hours=24)
    
    if history:
        # 履歴データをDataFrameに変換
        history_data = []
        for entry in history:
            history_data.append({
                "時刻": utc_to_jst_string(entry["timestamp"]),
                "ステータス": entry["overall_status"],
                "稼働時間(h)": entry["metrics"].get("uptime_hours", 0),
                "メモリ(MB)": entry["metrics"].get("process_memory_mb", 0),
                "CPU(%)": entry["metrics"].get("process_cpu_percent", 0)
            })
        
        history_df = pd.DataFrame(history_data)
        
        # ステータス履歴チャート
        st.subheader("📈 ステータス履歴")
        
        # ステータスを数値に変換してプロット
        status_mapping = {"healthy": 3, "degraded": 2, "unhealthy": 1}
        history_df["ステータス値"] = history_df["ステータス"].map(status_mapping)
        
        fig_status = px.line(
            history_df,
            x="時刻",
            y="ステータス値",
            title="システムステータス履歴",
            labels={"ステータス値": "ステータス"}
        )
        
        # Y軸のラベルをカスタマイズ
        fig_status.update_layout(
            yaxis=dict(
                tickmode='array',
                tickvals=[1, 2, 3],
                ticktext=['Unhealthy', 'Degraded', 'Healthy']
            )
        )
        
        st.plotly_chart(fig_status, use_container_width=True)
        
        # メトリクス履歴チャート
        if len(history_df) > 1:
            st.subheader("💹 パフォーマンスメトリクス")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # メモリ使用量
                fig_memory = px.line(
                    history_df,
                    x="時刻",
                    y="メモリ(MB)",
                    title="メモリ使用量推移"
                )
                st.plotly_chart(fig_memory, use_container_width=True)
            
            with col2:
                # CPU使用率
                fig_cpu = px.line(
                    history_df,
                    x="時刻",
                    y="CPU(%)",
                    title="CPU使用率推移"
                )
                st.plotly_chart(fig_cpu, use_container_width=True)
        
        # 履歴テーブル
        with st.expander("📋 詳細履歴"):
            st.dataframe(history_df, use_container_width=True)
    
    else:
        st.info("履歴データがありません。時間経過とともにデータが蓄積されます。")

except Exception as e:
    st.error(f"履歴データの取得に失敗しました: {str(e)}")

# === ヘルスレポート出力 ===
st.header("📄 ヘルスレポート出力")

col1, col2 = st.columns(2)

with col1:
    if st.button("📋 ヘルスレポート生成"):
        try:
            report_path = Path("logs") / f"health_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            report_path.parent.mkdir(exist_ok=True)
            
            with st.spinner("レポートを生成中..."):
                health_checker.export_health_report(report_path)
            
            st.success(f"ヘルスレポートを生成しました: {report_path}")
            
            # ダウンロードリンクを提供
            with open(report_path, 'r', encoding='utf-8') as f:
                report_content = f.read()
            
            st.download_button(
                label="📥 レポートをダウンロード",
                data=report_content,
                file_name=report_path.name,
                mime="application/json"
            )
            
        except Exception as e:
            st.error(f"レポート生成に失敗しました: {str(e)}")

with col2:
    # 自動更新設定
    auto_refresh = st.checkbox("🔄 自動更新 (30秒間隔)")
    st.session_state["auto_refresh"] = auto_refresh
    
    if auto_refresh:
        import time
        time.sleep(30)
        st.rerun()

# === システム設定 ===
st.header("⚙️ システム設定")

with st.expander("🔧 設定詳細"):
    try:
        config_path = Path("config/production.yml")
        if config_path.exists():
            import yaml
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            st.json(config)
        else:
            st.warning("設定ファイルが見つかりません")
    
    except Exception as e:
        st.error(f"設定の読み込みに失敗しました: {str(e)}")

# === アラートと通知 ===
st.header("🚨 アラートと通知")

if "last_health_check" in st.session_state:
    health = st.session_state["last_health_check"]
    
    # 重要なアラートを表示
    critical_issues = [comp for comp in health.components if comp.status == "unhealthy"]
    warning_issues = [comp for comp in health.components if comp.status == "degraded"]
    
    if critical_issues:
        st.error("🔴 緊急対応が必要な問題があります")
        for issue in critical_issues:
            st.write(f"- **{issue.component}**: {issue.message}")
    
    if warning_issues:
        st.warning("🟡 注意が必要な問題があります")
        for issue in warning_issues:
            st.write(f"- **{issue.component}**: {issue.message}")
    
    if not critical_issues and not warning_issues:
        st.success("🟢 システムは正常に動作しています")

# === フッター ===
st.divider()
st.caption("⚡ System Monitor v1.0 - リアルタイムシステム監視")

# 最終更新時刻を表示
if "last_health_check" in st.session_state:
    last_check = st.session_state["last_health_check"].generated_at
    st.caption(f"最終チェック: {utc_to_jst_string(last_check)}")