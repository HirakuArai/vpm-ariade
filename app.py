"""app.py – Kai Streamlit UI with JSON conversation logging + auto‑push
-----------------------------------------------------------------------------
* 1‑day‑per‑file JSON logs (conversations/conversation_YYYYMMDD.json)
* After each user↔assistant exchange, the updated log file is git‑add / commit / push
  via core.git_ops.commit_and_push_log().
"""
from __future__ import annotations

import json
import os
import sys
import traceback
import logging
from datetime import date, datetime
from pathlib import Path
from textwrap import dedent
from zoneinfo import ZoneInfo
from typing import Optional, List, Dict
import yaml, pandas as pd
import streamlit as st

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="Kai VPM - AI-First Virtual Project Manager", 
    page_icon="🧠", 
    initial_sidebar_state="expanded",
    layout="wide"
)

# モダンなグローバルスタイルを適用
st.markdown("""
<style>
/* グローバルフォントとカラーテーマ */
.stApp {
    background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
}

/* サイドバーのスタイリング */
.css-1d391kg {
    background: linear-gradient(180deg, #667eea 0%, #764ba2 100%);
}

/* サイドバーボタンの色による選択状態表現 */
.stButton > button[data-baseweb="button"][kind="secondary"] {
    background: rgba(66, 133, 244, 0.5) !important;  /* 50% 透明度 */
    color: rgba(255, 255, 255, 0.9) !important;
    border: 1px solid rgba(66, 133, 244, 0.3) !important;
    transition: all 0.3s ease !important;
}

.stButton > button[data-baseweb="button"][kind="primary"] {
    background: rgba(66, 133, 244, 1.0) !important;  /* 100% 濃度 */
    color: white !important;
    border: 2px solid rgba(66, 133, 244, 1.0) !important;
    font-weight: 600 !important;
    box-shadow: 0 4px 15px rgba(66, 133, 244, 0.4) !important;
    transition: all 0.3s ease !important;
}

.stButton > button[data-baseweb="button"][kind="primary"]:hover {
    background: rgba(66, 133, 244, 1.0) !important;
    box-shadow: 0 6px 20px rgba(66, 133, 244, 0.5) !important;
    transform: translateY(-2px) !important;
}

.stButton > button[data-baseweb="button"][kind="secondary"]:hover {
    background: rgba(66, 133, 244, 0.7) !important;  /* ホバー時は70% */
    transform: translateY(-1px) !important;
    box-shadow: 0 2px 10px rgba(66, 133, 244, 0.3) !important;
}

/* メインコンテンツエリア */
.main .block-container {
    background: rgba(255, 255, 255, 0.95);
    border-radius: 20px;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
    backdrop-filter: blur(10px);
    padding: 2rem;
    margin-top: 1rem;
}

/* チャットメッセージのスタイリング */
.stChatMessage {
    border-radius: 15px;
    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
    margin: 8px 0;
}

/* ボタンのモダンスタイル */
.stButton > button {
    border-radius: 25px;
    border: none;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    font-weight: 600;
    transition: all 0.3s ease;
    box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
}

.stButton > button:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
}

/* インプットフィールドのスタイリング */
.stTextInput > div > div > input {
    border-radius: 15px;
    border: 2px solid #e1e5e9;
    transition: all 0.3s ease;
}

.stTextInput > div > div > input:focus {
    border-color: #667eea;
    box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

/* カードスタイルコンポーネント */
.stExpander {
    border-radius: 15px;
    border: 1px solid #e1e5e9;
    background: rgba(255, 255, 255, 0.8);
    backdrop-filter: blur(5px);
}

/* メトリクスのスタイリング */
.metric-container {
    background: linear-gradient(135deg, #ff9a9e 0%, #fecfef 50%, #fecfef 100%);
    border-radius: 15px;
    padding: 1rem;
    margin: 0.5rem 0;
    color: white;
    text-align: center;
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
}

/* アニメーション */
@keyframes fadeInUp {
    from {
        opacity: 0;
        transform: translateY(20px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.fade-in {
    animation: fadeInUp 0.6s ease-out;
}

/* レスポンシブデザイン */
@media (max-width: 768px) {
    .main .block-container {
        padding: 1rem;
        margin: 0.5rem;
        border-radius: 15px;
    }
}

/* プロジェクト選択の強調 */
.project-highlight {
    background: linear-gradient(135deg, #84fab0 0%, #8fd3f4 100%);
    border-radius: 12px;
    padding: 1rem;
    margin: 1rem 0;
    color: white;
    font-weight: 600;
    text-align: center;
    box-shadow: 0 4px 15px rgba(132, 250, 176, 0.3);
}
</style>
""", unsafe_allow_html=True)

# Streamlitのマルチページ機能を無効化
# pagesディレクトリの存在による自動ページ検出を防ぐ
if hasattr(st, '_is_running_with_streamlit'):
    st._is_running_with_streamlit = True

# ────────────────────────────────────────────────────────────────────────────
# Kai modules
# ────────────────────────────────────────────────────────────────────────────
try:
    from core.git_ops import commit_and_push_log, commit_and_push_project_data  # ← NEW: auto‑push helpers
    from core.minutes_utils import generate_daily_minutes, safe_push_minutes
    from utils.render_minutes import render_md
    from core.project_service import create_project, set_status, add_task, apply_updates
    # from core.project_diff import generate_update_candidates, extract_new_data_from_chat, generate_diff_summary, validate_update_candidate
    from core.project_prompt import get_project_prompt, get_available_project_ids, get_project_summary
    from core.lifecycle_manager import ProjectLifecycleManager
    from core.conversation_engine import PhaseAwareConversationEngine
    from core.auto_update_engine import AutoUpdateEngine
    from core.progress_monitor import ProgressMonitor
    from core.notification_system import NotificationSystem
    from core.models import ProjectPhase
    from core.ui_components import ProjectVisualization, QuestionVisualization, InteractiveComponents, StatusIndicators
    from core.enhanced_ui_components import NotificationComponents, ResponsiveLayout
    from core.ai_quality_manager import create_quality_manager
    from core.navigation import navigator, PageType
    from core.pages import ProjectDetailsPage, ProjectChatPage, ConversationHistoryPage
    from core.ai_intent_detector import AIIntentDetector
except (ImportError, KeyError) as e:
    logger.error(f"Failed to import Kai modules: {e}")
    st.error(f"モジュールの読み込みに失敗しました: {e}")
    # Try adding path and reimport
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    # Import minimal required modules
    from core.project_service import create_project, set_status, add_task
    from core.project_prompt import get_project_prompt, get_available_project_ids
    from core.navigation import navigator, PageType

# ────────────────────────────────────────────────────────────────────────────
# Paths & basic setup
# ────────────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent
DOCS = ROOT / "docs"
DSL_DIR = ROOT / "dsl"
CONV_DIR = ROOT / "conversations"
CONV_DIR.mkdir(parents=True, exist_ok=True)

# ────────────────────────────────────────────────────────────────────────────
# OpenAI API key (ENV > Streamlit secrets)
# ────────────────────────────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv("config/.env")  # config/.envを明示的に指定
except ImportError:
    pass

def get_openai_api_key():
    # 1. 環境変数
    key = os.getenv("OPENAI_API_KEY")
    if key:
        return key
    # 2. Streamlit secrets
    if st is not None:
        try:
            return st.secrets["OPENAI_API_KEY"]
        except Exception:
            pass
    # 3. .env直読（開発用の最終保険）
    try:
        with open(".env") as f:
            for line in f:
                if line.strip().startswith("OPENAI_API_KEY="):
                    return line.strip().split("=", 1)[1].strip().strip('"').strip("'")
    except Exception:
        pass
    return None

openai_api_key = get_openai_api_key()

if not openai_api_key:
    # この場所だけはstreamlitで出す
    if st is not None:
        st.error("❌ OpenAI API キーが見つかりません。")
    else:
        raise RuntimeError("OpenAI APIキーが見つかりません。")
else:
    import openai
    openai.api_key = openai_api_key

# ────────────────────────────────────────────────────────────────────────────
# Conversation‑log helpers (JSON, 1‑day‑per‑file)
# ────────────────────────────────────────────────────────────────────────────
_JST = ZoneInfo("Asia/Tokyo")

def _today_log_path() -> Path:
    """Return Path for today's conversation log."""
    today = datetime.now(_JST).strftime("%Y%m%d")
    return CONV_DIR / f"conversation_{today}.json"

def _append_log(role: str, content: str) -> None:
    """Append a single message to today's JSON log."""
    log_path = _today_log_path()
    now_iso = datetime.now(_JST).isoformat(timespec="seconds")
    if log_path.exists():
        with log_path.open(encoding="utf-8") as fp:
            data = json.load(fp)
    else:
        data = {"log_id": datetime.now(_JST).strftime("%Y%m%d"), "messages": []}
    data["messages"].append({"role": role, "content": content, "ts": now_iso})
    with log_path.open("w", encoding="utf-8") as fp:
        json.dump(data, fp, ensure_ascii=False, indent=2)


def _project_log_path(project_id: str) -> Path:
    """Return Path for today's project-specific conversation log."""
    today = datetime.now(_JST).strftime("%Y%m%d")
    project_conv_dir = Path(f"data/conversations/{project_id}")
    project_conv_dir.mkdir(parents=True, exist_ok=True)
    return project_conv_dir / f"{today}.jsonl"


def _append_project_log(project_id: str, role: str, content: str) -> None:
    """Append a single message to today's project-specific JSONL log."""
    log_path = _project_log_path(project_id)
    now_iso = datetime.now(_JST).isoformat(timespec="seconds")
    
    # Create JSONL entry
    log_entry = {
        "project_id": project_id,
        "role": role,
        "content": content,
        "timestamp": now_iso
    }
    
    # Append to JSONL file
    with log_path.open("a", encoding="utf-8") as fp:
        fp.write(json.dumps(log_entry, ensure_ascii=False) + "\n")


def load_project_conversation_history(project_id: str) -> List[Dict]:
    """プロジェクト固有の会話履歴を読み込み"""
    project_conv_dir = Path(f"data/conversations/{project_id}")
    history = []
    
    if project_conv_dir.exists():
        # 全ての会話ログファイルを取得して日付順にソート
        log_files = sorted([f for f in project_conv_dir.glob("*.jsonl")])
        
        # 最近の3日分のファイルのみを読み込み（パフォーマンス考慮）
        recent_files = log_files[-3:] if len(log_files) > 3 else log_files
        
        for log_file in recent_files:
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():  # 空行をスキップ
                            entry = json.loads(line.strip())
                            history.append({
                                "role": entry["role"],
                                "content": entry["content"]
                            })
            except Exception as e:
                print(f"Error loading project history from {log_file}: {e}")
    
    return history

# ────────────────────────────────────────────────────────────────────────────
# Small utils
# ────────────────────────────────────────────────────────────────────────────

def _read(path: Path | str) -> str:
    return Path(path).read_text(encoding="utf-8")

def _extract_section(md_path: Path, headings: list[str]) -> str:
    """Extract only specified headings from markdown (unused but kept)."""
    lines = _read(md_path).splitlines()
    keep, buf = False, []
    for line in lines:
        if line.startswith("#"):
            title = line.lstrip("# ").strip()
            keep = title in headings
        if keep:
            buf.append(line)
    return "\n".join(buf)

# ────────────────────────────────────────────────────────────────────────────
# Phase Management UI
# ────────────────────────────────────────────────────────────────────────────

def render_phase_management_ui(project_id: str):
    """プロジェクトフェーズ管理UIの表示"""
    try:
        lifecycle_manager = ProjectLifecycleManager()
        
        # 現在のフェーズ表示
        current_phase = lifecycle_manager.get_current_phase(project_id)
        
        # フェーズ進捗の表示
        progress_info = lifecycle_manager.get_phase_progress(project_id)
        completion = progress_info.get("completion_percentage", 0.0)
        
        # フェーズプログレスバー
        phase_names = ["INCEPTION", "DEFINITION", "PLANNING", "EXECUTION", "MONITORING", "CLOSURE"]
        current_index = phase_names.index(current_phase.value) if current_phase.value in phase_names else 0
        progress_percentage = (current_index + 1) / len(phase_names)
        
        st.progress(progress_percentage, text=f"フェーズ進捗: {current_index + 1}/{len(phase_names)}")
        
        # 現在フェーズの表示
        phase_emoji = {
            "INCEPTION": "💡",
            "DEFINITION": "📋", 
            "PLANNING": "📅",
            "EXECUTION": "🚀",
            "MONITORING": "📊",
            "CLOSURE": "✅"
        }
        
        st.info(f"{phase_emoji.get(current_phase.value, '📌')} **現在**: {current_phase.value}")
        st.metric("完了率", f"{completion:.1f}%")
        
        # フェーズ進行チェック
        can_advance = progress_info.get("can_advance", False)
        missing_requirements = progress_info.get("missing_requirements", [])
        next_phase = progress_info.get("next_phase")
        
        if next_phase:
            if can_advance:
                if st.button(f"📈 次フェーズへ進む\n({next_phase})", key="advance_phase"):
                    success = lifecycle_manager.advance_phase(project_id)
                    if success:
                        st.success(f"フェーズを {next_phase} に進めました！")
                        st.rerun()
                    else:
                        st.error("フェーズの進行に失敗しました")
            else:
                st.warning("**フェーズ進行の要件:**")
                for req in missing_requirements:
                    st.write(f"- {req}")
        else:
            st.success("🎉 プロジェクト完了！")
        
        # 要件チェックリスト（展開可能）
        with st.expander("📋 フェーズ要件チェックリスト"):
            checklist = lifecycle_manager.get_phase_requirements_checklist(project_id)
            if checklist:
                for item in checklist.get("status", []):
                    icon = "✅" if item["satisfied"] else "❌"
                    st.write(f"{icon} {item['requirement']}")
        
        # フェーズ履歴（展開可能）
        phase_history = progress_info.get("phase_history", [])
        if phase_history:
            with st.expander("📚 フェーズ履歴"):
                for entry in reversed(phase_history[-5:]):  # 最新5件
                    timestamp = entry.get("timestamp", "")
                    from_phase = entry.get("from_phase", "")
                    to_phase = entry.get("to_phase", "")
                    if timestamp:
                        date_str = timestamp[:10]  # YYYY-MM-DD部分
                        st.write(f"**{date_str}**: {from_phase} → {to_phase}")
        
    except Exception as e:
        st.error(f"フェーズ管理UI エラー: {str(e)}")
        st.exception(e)

# ────────────────────────────────────────────────────────────────────────────
# Prompt generator
# ────────────────────────────────────────────────────────────────────────────

# System prompt functions moved to core.project_prompt

# ────────────────────────────────────────────────────────────────────────────
# Hierarchical Navigation UI
# ────────────────────────────────────────────────────────────────────────────

# ナビゲーション状態の初期化を確実に行う
navigator.initialize_session_state()

# Streamlitのデフォルトページ制御を無効化（初期化後）
if "page" in st.query_params:
    st.query_params.clear()

# サイドバーナビゲーションの描画
nav_state = navigator.render_sidebar_navigation()

# デバッグ・リセット機能（JavaScriptエラー対処用）
with st.sidebar:
    st.divider()
    with st.expander("🔧 デバッグ・リセット", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔄 セッション\nリセット", help="JavaScriptエラー時に使用", use_container_width=True):
                # セッション状態をクリア
                keys_to_clear = [k for k in st.session_state.keys() if k not in ['navigation_state']]
                for key in keys_to_clear:
                    del st.session_state[key]
                st.success("セッション状態をリセットしました")
                st.rerun()
        
        with col2:
            if st.button("ℹ️ JS エラー\n対処法", help="JavaScript Failed to fetch対処法", use_container_width=True):
                st.info("""
                **JavaScriptエラー対処法:**
                1. ハードリフレッシュ:
                   - Ctrl+Shift+R (Win)
                   - Cmd+Shift+R (Mac)
                2. シークレット/プライベートモードで再試行
                3. ブラウザキャッシュクリア
                4. URL直接アクセス
                """)
        
        # Streamlit バージョン情報
        st.caption(f"Streamlit v{st.__version__}")
        
        # エラー診断
        if st.button("🔍 エラー診断", use_container_width=True):
            st.write("**ブラウザ情報:**")
            st.code("User-Agent取得にはJavaScriptが必要です")
            st.write("**推奨ブラウザ:** Chrome, Firefox, Safari最新版")

# ナビゲーション状態の妥当性チェック
navigator.validate_navigation_state()

# ナビゲーション状態を再確認（rerun後の状態を反映）
nav_state = st.session_state.navigation_state

# ページヘッダーの描画
navigator.render_page_header()

# ページコンテンツの描画
def render_page_content():
    """現在のページコンテンツを描画"""
    # 最新のナビゲーション状態を取得
    current_nav_state = st.session_state.navigation_state
    current_page = current_nav_state.current_page
    selected_project = current_nav_state.selected_project_id
    
    if current_page == PageType.PROJECT_DETAILS:
        if selected_project:
            ProjectDetailsPage.render(selected_project)
        else:
            st.warning("プロジェクトを選択してください")
    
    elif current_page == PageType.PROJECT_CHAT:
        if selected_project:
            ProjectChatPage.render(selected_project)
        else:
            st.warning("プロジェクトを選択してください")
    
    
    elif current_page == PageType.CONVERSATION_HISTORY:
        if selected_project:
            ConversationHistoryPage.render(selected_project)
        else:
            st.warning("プロジェクトを選択してください")
    
    else:  # PageType.HOME
        render_home_page()

def render_home_page():
    """ホームページ（メイン会話ページ）の描画"""
    # プロジェクト情報の視覚化（選択されている場合）
    current_project_id = nav_state.selected_project_id
    if current_project_id:
        try:
            from core.dynamic_schema import get_project_schema
            from core.lifecycle_manager import ProjectLifecycleManager
            
            # 動的スキーマ視覚化
            with st.expander("📊 プロジェクト情報収集状況", expanded=True):
                schema = get_project_schema(current_project_id)
                ProjectVisualization.render_schema_progress(schema)
                ProjectVisualization.render_field_cards(schema)
            
            # フェーズ進捗視覚化
            with st.expander("🗺️ フェーズ進捗", expanded=False):
                lifecycle_manager = ProjectLifecycleManager()
                current_phase = lifecycle_manager.get_current_phase(current_project_id)
                progress_info = lifecycle_manager.get_phase_progress(current_project_id)
                StatusIndicators.render_phase_progression(current_phase, progress_info)
                
                # フェーズ制御
                st.markdown("#### 🎮 フェーズ制御")
                col1, col2 = st.columns(2)
                
                can_advance = progress_info.get("can_advance", False)
                
                with col1:
                    if can_advance:
                        if st.button("⏭️ 次のフェーズへ進む", type="primary", key="home_advance_phase"):
                            try:
                                result = lifecycle_manager.advance_phase(current_project_id)
                                if result.get("success"):
                                    st.success(f"✅ {result.get('new_phase')} フェーズに進みました！")
                                    st.rerun()
                                else:
                                    st.error(f"❌ フェーズ進行に失敗: {result.get('message')}")
                            except Exception as e:
                                st.error(f"❌ エラーが発生しました: {e}")
                    else:
                        st.button("⏭️ 次のフェーズへ進む", disabled=True, key="home_advance_phase_disabled")
                        st.caption("進行条件が満たされていません")
                
                with col2:
                    if st.button("🔄 フェーズ条件を再評価", key="home_reevaluate_phase"):
                        try:
                            progress_info = lifecycle_manager.get_phase_progress(current_project_id)
                            if progress_info.get("can_advance"):
                                st.success("✅ 次のフェーズに進む準備ができています！")
                            else:
                                missing = progress_info.get("missing_requirements", [])
                                if missing:
                                    st.warning(f"⚠️ 不足要件: {', '.join(missing)}")
                                else:
                                    st.info("ℹ️ まだ進行条件が満たされていません")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ 評価中にエラーが発生しました: {e}")
            
            # 推奨アクション
            with st.expander("💡 推奨アクション", expanded=False):
                pending_questions = schema.get_pending_questions(max_questions=5)
                
                if pending_questions:
                    st.info("💬 **次の会話で聞いてみましょう:**")
                    for field_name, questions in pending_questions:
                        st.write(f"**{field_name}**: {questions[0]}")
                else:
                    st.success("🎉 必要な情報がすべて収集されています！")
            
            # プロジェクト削除
            with st.expander("🗑️ プロジェクト管理", expanded=False):
                st.warning("⚠️ **危険な操作**")
                
                # 削除確認の状態管理
                if f"confirm_delete_{current_project_id}" not in st.session_state:
                    st.session_state[f"confirm_delete_{current_project_id}"] = False
                
                if not st.session_state[f"confirm_delete_{current_project_id}"]:
                    if st.button("🗑️ このプロジェクトを削除する", type="secondary", key=f"delete_btn_{current_project_id}"):
                        st.session_state[f"confirm_delete_{current_project_id}"] = True
                        st.rerun()
                else:
                    st.error("**本当に削除しますか？**")
                    st.write("このプロジェクトはアーカイブされ、画面上から非表示になります。")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("✅ はい、削除する", type="primary", key=f"confirm_yes_{current_project_id}"):
                            try:
                                # プロジェクトをARCHIVEDステータスに変更
                                set_status(current_project_id, "ARCHIVED")
                                
                                # ナビゲーション状態をリセット
                                st.session_state.navigation_state.selected_project_id = None
                                st.session_state.navigation_state.current_page = PageType.HOME
                                st.session_state["current_project_id"] = None
                                
                                # 確認状態をリセット
                                st.session_state[f"confirm_delete_{current_project_id}"] = False
                                
                                st.success(f"プロジェクト {current_project_id} を削除しました")
                                st.rerun()
                                
                            except Exception as e:
                                st.error(f"削除に失敗しました: {e}")
                    
                    with col2:
                        if st.button("❌ いいえ、キャンセル", key=f"confirm_no_{current_project_id}"):
                            st.session_state[f"confirm_delete_{current_project_id}"] = False
                            st.rerun()
            
        except Exception as e:
            logger.error(f"Error rendering project visualization: {e}")
            st.warning("プロジェクト視覚化の表示でエラーが発生しました")
        
    else:
        # レスポンシブレイアウトでウェルカムメッセージを表示
        welcome_items = [
            lambda: st.info("💡 左サイドバーからプロジェクトを選択するか、自然な言葉でプロジェクト作成を依頼してください。"),
            lambda: st.markdown("**例:**\n- 「ウェブサイト開発プロジェクトを始めたい」\n- 「会社研修を企画したい」\n- 「新商品の開発プロジェクトを作成して」")
        ]
        
        ResponsiveLayout.render_adaptive_columns(welcome_items, max_cols=2)
        
        # 会話インターフェースの後にセッション履歴を表示
        # （render_chat_interface() が下で呼ばれる）


def render_chat_interface():
    """チャットインターフェースの描画"""
    # セッション履歴表示（プロジェクト未選択時のホーム画面）
    history = st.session_state.get("history", [])
    if history:
        st.markdown("### 💬 現在のセッション")
        for msg in history:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role and content:
                st.chat_message(role).markdown(content)
    else:
        # デバッグ情報（開発中のみ）
        with st.expander("🔍 デバッグ情報", expanded=False):
            st.write(f"履歴の長さ: {len(history)}")
            st.write(f"セッション状態のキー: {list(st.session_state.keys())}")
            if history:
                st.json(history[-1] if history else "履歴なし")
    
    st.divider()
    st.markdown("### 💬 AI との会話")
    
    # プロジェクト作成のヒント
    current_nav_state = st.session_state.navigation_state
    current_project_id = current_nav_state.selected_project_id
    if not current_project_id:
        st.info("💡 自然な言葉でプロジェクト作成やタスク追加を依頼してください。\n例：「ウェブサイト開発を始めたい」「データベース設計を来週までに完了したい」")
    
    # チャット入力
    user_input = st.chat_input("メッセージを入力してください…（自然な言葉でプロジェクト作成やタスク追加可能）")
    
    if user_input:
        # AI-First 会話処理を実行
        from core.chat_handler_ai import process_chat_input_ai
        process_chat_input_ai(user_input, current_project_id)

# Chat processing functions have been moved to core.chat_handler to prevent circular imports

# セッション状態の初期化
if "history" not in st.session_state:
    st.session_state["history"] = []
if "awaiting_project_overview" not in st.session_state:
    st.session_state["awaiting_project_overview"] = False
if "awaiting_activate_confirm" not in st.session_state:
    st.session_state["awaiting_activate_confirm"] = False
if "created_project_id" not in st.session_state:
    st.session_state["created_project_id"] = None
if "current_project_id" not in st.session_state:
    st.session_state["current_project_id"] = None
if "update_candidates" not in st.session_state:
    st.session_state["update_candidates"] = []

# AI Intent Detector初期化
if "ai_intent_detector" not in st.session_state:
    try:
        st.session_state["ai_intent_detector"] = AIIntentDetector(get_openai_api_key())
    except Exception as e:
        logger.error(f"Failed to initialize AI Intent Detector: {e}")
        st.session_state["ai_intent_detector"] = None

# メインコンテンツの描画
render_page_content()

# ホームページの場合のみ会話機能を表示（プロジェクト未選択時のみ）
# 最新のナビゲーション状態を取得
current_nav_state = st.session_state.navigation_state
if current_nav_state.current_page == PageType.HOME and not current_nav_state.selected_project_id:
    render_chat_interface()

# サイドバーに拡張機能を追加
with st.sidebar:
    st.divider()
    
    # システム状態表示
    with st.expander("⚙️ システム状態", expanded=False):
        NotificationComponents.render_system_status()
    
    # AI品質管理ダッシュボード
    if st.session_state.get("ai_quality_manager"):
        with st.expander("📊 AI品質管理", expanded=False):
            quality_manager = st.session_state["ai_quality_manager"]
            
            # 品質レポート表示
            report = quality_manager.get_quality_report()
            metrics = report["metrics"]
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("成功率", f"{(1-metrics['error_rate'])*100:.1f}%")
                st.metric("平均応答時間", f"{metrics['average_response_time']:.2f}s")
            
            with col2:
                st.metric("品質スコア", f"{metrics['average_quality_score']:.2f}")
                st.metric("24h リクエスト", metrics['last_24h_requests'])
            
            # 推奨事項
            recommendations = quality_manager.get_recommendations()
            if recommendations:
                st.markdown("**推奨事項:**")
                for rec in recommendations:
                    st.caption(rec)

# 履歴表示（プロジェクト固有履歴＋セッション履歴）  
