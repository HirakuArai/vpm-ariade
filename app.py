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

st.set_page_config(page_title="Kai VPM", page_icon="💬", initial_sidebar_state="expanded")

# ────────────────────────────────────────────────────────────────────────────
# Kai modules
# ────────────────────────────────────────────────────────────────────────────
from core.git_ops import commit_and_push_log, commit_and_push_project_data  # ← NEW: auto‑push helpers
from core.minutes_utils import generate_daily_minutes, safe_push_minutes
from utils.render_minutes import render_md
from core.project_service import create_project, set_status, add_task, apply_updates
from core.project_diff import generate_update_candidates, extract_new_data_from_chat, generate_diff_summary, validate_update_candidate
from core.project_prompt import get_project_prompt, get_available_project_ids, get_project_summary
from core.lifecycle_manager import ProjectLifecycleManager
from core.conversation_engine import PhaseAwareConversationEngine
from core.auto_update_engine import AutoUpdateEngine
from core.progress_monitor import ProgressMonitor
from core.notification_system import NotificationSystem
from core.models import ProjectPhase
from core.ui_components import ProjectVisualization, QuestionVisualization, InteractiveComponents, StatusIndicators
from core.navigation import navigator, PageType
from core.pages import ProjectInfoPage, PhaseProgressPage, ConversationHistoryPage

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

@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_system_prompt() -> str:
    """Get system prompt with caching for performance optimization"""
    try:
        rules = _read(DOCS / "base_os_rules.md")
        dsl_readme_path = DSL_DIR / "README.md"
        dsl_readme = dsl_readme_path.read_text(encoding="utf-8") if dsl_readme_path.exists() else ""
        dsl_lines: list[str] = []
        try:
            for raw in (DSL_DIR / "integrated_dsl.jsonl").read_text(encoding="utf-8").splitlines():
                item = json.loads(raw)
                name, desc = item.get("name"), item.get("description")
                if name and desc:
                    dsl_lines.append(f"- **{name}**: {desc}")
        except FileNotFoundError:
            pass
        dsl_block = "\n".join([dsl_readme.strip()] + dsl_lines if dsl_readme else dsl_lines)
        proj = _read(DOCS / "project_definition.md")
        arch = _read(DOCS / "architecture_overview.md")
        
        base_prompt = "\n\n".join([rules, dsl_block, proj, arch])
        return base_prompt
        
    except Exception as e:
        logger.error(f"Error generating system prompt: {str(e)}")
        return "You are Kai, a Virtual Project Manager AI assistant."

@st.cache_data(ttl=10)  # Cache for 10 seconds (shorter for frequent updates)
def get_cached_project_context(project_id: str) -> str:
    """Get project context with caching"""
    try:
        return get_project_prompt(project_id)
    except Exception as e:
        logger.error(f"Error getting project context for {project_id}: {str(e)}")
        return ""

def get_full_system_prompt() -> str:
    """Get full system prompt including project context"""
    base_prompt = get_system_prompt()
    
    # 現在日時を明示的に追加
    current_time = datetime.now(_JST)
    date_context = f"\n\n**現在日時**: {current_time.strftime('%Y年%m月%d日 %H:%M')} (JST)\n今日は{current_time.strftime('%Y年%m月%d日')}です。"
    
    current_project_id = st.session_state.get("current_project_id")
    if current_project_id:
        project_context = get_cached_project_context(current_project_id)
        if project_context:
            return f"{base_prompt}{date_context}\n\n{project_context}"
    
    return f"{base_prompt}{date_context}"

# ────────────────────────────────────────────────────────────────────────────
# Hierarchical Navigation UI
# ────────────────────────────────────────────────────────────────────────────

# サイドバーナビゲーションの描画
nav_state = navigator.render_sidebar_navigation()

# ナビゲーション状態の妥当性チェック
navigator.validate_navigation_state()

# ページヘッダーの描画
navigator.render_page_header()

# ページコンテンツの描画
def render_page_content():
    """現在のページコンテンツを描画"""
    current_page = nav_state.current_page
    selected_project = nav_state.selected_project_id
    
    if current_page == PageType.PROJECT_INFO:
        if selected_project:
            ProjectInfoPage.render(selected_project)
        else:
            st.warning("プロジェクトを選択してください")
    
    elif current_page == PageType.PHASE_PROGRESS:
        if selected_project:
            PhaseProgressPage.render(selected_project)
        else:
            st.warning("プロジェクトを選択してください")
    
    elif current_page == PageType.CONVERSATION_HISTORY:
        if selected_project:
            ConversationHistoryPage.render(selected_project)
        else:
            st.warning("プロジェクトを選択してください")
    
    elif current_page == PageType.PROGRESS_DASHBOARD:
        render_progress_dashboard()
    
    elif current_page == PageType.SCHEDULE_MANAGEMENT:
        render_schedule_management()
    
    elif current_page == PageType.SYSTEM_MONITOR:
        render_system_monitor()
    
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
            
        except Exception as e:
            logger.error(f"Error rendering project visualization: {e}")
            st.warning("プロジェクト視覚化の表示でエラーが発生しました")
        
        # 会話履歴
        project_history = load_project_conversation_history(current_project_id)
        if project_history:
            with st.expander("📜 プロジェクト会話履歴", expanded=False):
                # 最新5会話（10メッセージ）を表示
                recent_messages = project_history[-10:]
                for msg in recent_messages:
                    st.chat_message("user" if msg["role"] == "user" else "assistant").markdown(msg["content"])
                
                # 会話セット数を計算（質問と回答のペア数）
                # userメッセージの数を数える（会話セット数と一致）
                total_conversations = len([msg for msg in project_history if msg["role"] == "user"])
                displayed_conversations = len([msg for msg in recent_messages if msg["role"] == "user"])
                
                if len(project_history) > 10:
                    st.caption(f"（{total_conversations}会話中、最新{displayed_conversations}会話を表示）")
    else:
        st.info("💡 左サイドバーからプロジェクトを選択するか、「プロジェクト作成」と入力して新しいプロジェクトを作成してください。")
    
    # セッション履歴表示
    if st.session_state.get("history"):
        st.markdown("### 💬 現在のセッション")
        for msg in st.session_state["history"]:
            st.chat_message("user" if msg["role"] == "user" else "assistant").markdown(msg["content"])

def render_progress_dashboard():
    """進捗ダッシュボードページ"""
    st.info("🚧 進捗ダッシュボードページ（実装予定）")

def render_schedule_management():
    """スケジュール管理ページ"""
    st.info("🚧 スケジュール管理ページ（実装予定）")

def render_system_monitor():
    """システム監視ページ"""
    st.info("🚧 システム監視ページ（実装予定）")

def render_chat_interface():
    """チャットインターフェースの描画"""
    st.divider()
    st.markdown("### 💬 AI との会話")
    
    # プロジェクト作成のヒント
    current_project_id = nav_state.selected_project_id
    if not current_project_id:
        st.info("💡 プロジェクト作成は「プロジェクト作成」と入力してください。\n作成時は「タイトル: 詳細説明」の形式がおすすめです。")
    
    # チャット入力
    user_input = st.chat_input("メッセージを入力してください…（プロジェクト作成は「プロジェクト作成」と入力）")
    
    if user_input:
        # 会話処理を実行
        process_chat_input(user_input)

def process_chat_input(user_input: str):
    """チャット入力の処理"""
    # 1) ログへ保存
    _append_log("user", user_input)
    
    # Also log to project-specific log if project is selected
    current_project_id = nav_state.selected_project_id
    if current_project_id:
        _append_project_log(current_project_id, "user", user_input)
        # Backward compatibility
        st.session_state["current_project_id"] = current_project_id

    # Handle project creation flow
    assistant_reply = None
    
    # Check if we're waiting for project overview
    if st.session_state["awaiting_project_overview"]:
        try:
            # Extract display name from input if provided in format "title: description"
            if ":" in user_input:
                parts = user_input.split(":", 1)
                display_name = parts[0].strip()
                overview = parts[1].strip()
            else:
                # Use first part as display name if it's short, otherwise use entire input as overview
                if len(user_input.strip()) <= 30:
                    display_name = user_input.strip()
                    overview = user_input.strip()
                else:
                    # Try to extract a meaningful title from the beginning
                    words = user_input.strip().split()
                    if len(words) <= 5:
                        display_name = user_input.strip()
                    else:
                        display_name = " ".join(words[:5]) + "..."
                    overview = user_input.strip()
            
            # Create project with auto-generated ID
            project = create_project(None, overview, "human_user", display_name)
            st.session_state["created_project_id"] = project.identifier
            
            # Update navigation state
            st.session_state.navigation_state.selected_project_id = project.identifier
            st.session_state["current_project_id"] = project.identifier  # Backward compatibility
            
            st.session_state["awaiting_project_overview"] = False
            st.session_state["awaiting_activate_confirm"] = True
            assistant_reply = f"プロジェクト **{display_name}** を DRAFT で作成しました。次は ACTIVE にしますか？"
        except Exception as e:
            assistant_reply = f"プロジェクト作成中にエラーが発生しました: {str(e)}"
            st.session_state["awaiting_project_overview"] = False
    
    # Check if we're waiting for activation confirmation
    elif st.session_state["awaiting_activate_confirm"]:
        user_lower = user_input.lower().strip()
        if any(word in user_lower for word in ["はい", "yes", "する", "active", "アクティブ"]):
            try:
                set_status(st.session_state["created_project_id"], "ACTIVE")
                assistant_reply = f"プロジェクト **{st.session_state['created_project_id']}** を ACTIVE に設定しました！"
            except Exception as e:
                assistant_reply = f"ステータス更新中にエラーが発生しました: {str(e)}"
        else:
            assistant_reply = "プロジェクトは DRAFT のままです。後でステータスを変更できます。"
        
        # Reset flow state
        st.session_state["awaiting_activate_confirm"] = False
        st.session_state["created_project_id"] = None
    
    # Check for task addition command: "タスク <説明> <YYYY-MM-DD>"
    elif user_input.startswith("タスク "):
        import re
        # Parse task command: タスク <description> <YYYY-MM-DD>
        parts = user_input[3:].strip().split()  # Remove "タスク " prefix
        if len(parts) >= 2:
            # Last part should be date, everything else is description
            due_date = parts[-1]
            description = " ".join(parts[:-1])
            
            # Validate date format
            if re.match(r'\d{4}-\d{2}-\d{2}', due_date):
                if current_project_id:
                    try:
                        task = add_task(current_project_id, description, due_date)
                        
                        # Get current tasks for display
                        import json
                        path = Path(f"data/projects/{current_project_id}.json")
                        data = json.loads(path.read_text())
                        tasks = data.get("tasks", [])
                        
                        task_list = "\n".join([f"- {t['id']}: {t['description']} (期日: {t['due_date']})" for t in tasks])
                        assistant_reply = f"タスクを追加しました。\n\n現在のタスク一覧:\n{task_list}"
                    except Exception as e:
                        assistant_reply = f"タスク追加中にエラーが発生しました: {str(e)}"
                else:
                    assistant_reply = "まずプロジェクトを作成または選択してください。"
            else:
                assistant_reply = "日付は YYYY-MM-DD 形式で入力してください。"
        else:
            assistant_reply = "使用方法: タスク <説明> <YYYY-MM-DD>"
    
    # Check for project creation trigger
    elif "プロジェクト作成" in user_input:
        st.session_state["awaiting_project_overview"] = True
        assistant_reply = "プロジェクトの概要を教えてください。\n\n**入力形式:**\n- 短い名前: `会社研修`\n- タイトル付き: `会社研修: 新入社員向けの研修プログラムを企画・実施する`\n- 詳細のみ: `新入社員向けの研修プログラムを企画・実施する`"
    
    # Enhanced conversation flow with question generation
    if assistant_reply is None:
        assistant_reply = process_ai_conversation(user_input, current_project_id)
    
    # Update conversation history
    st.session_state["history"].append({"role": "user", "content": user_input})
    st.session_state["history"].append({"role": "assistant", "content": assistant_reply})
    
    # Also log assistant reply
    _append_log("assistant", assistant_reply)
    if current_project_id:
        _append_project_log(current_project_id, "assistant", assistant_reply)
    
    # Auto-push after conversation
    try:
        # Push global conversation log
        success = commit_and_push_log()
        if success:
            logger.info("Successfully pushed conversation log to git")
        else:
            logger.warning("Failed to push conversation log to git")
        
        # Push project-specific data if project is selected
        if current_project_id:
            project_success = commit_and_push_project_data(current_project_id)
            if project_success:
                logger.info(f"Successfully pushed project {current_project_id} data to git")
            else:
                logger.warning(f"Failed to push project {current_project_id} data to git")
    except Exception as e:
        logger.error(f"Error pushing to git: {e}")
    
    # Rerun to display the new messages
    st.rerun()

def process_ai_conversation(user_input: str, current_project_id: Optional[str]) -> str:
    """AI会話処理"""
    try:
        # 1. 基本的なAI応答生成
        system_prompt = get_full_system_prompt()
        messages = [{"role": "system", "content": system_prompt}] + \
                  st.session_state["history"] + \
                  [{"role": "user", "content": user_input}]
        
        # Performance optimization: limit history to last 5 exchanges to reduce old data influence
        if len(st.session_state["history"]) > 10:  # 10 messages = 5 exchanges
            recent_history = st.session_state["history"][-10:]
            messages = [{"role": "system", "content": system_prompt}] + \
                      recent_history + \
                      [{"role": "user", "content": user_input}]
        
        response = openai.chat.completions.create(
            model="gpt-4.1",
            messages=messages,
            max_tokens=2000,  # Limit response length for performance
            temperature=0.7
        )
        assistant_reply = response.choices[0].message.content.strip()
        
        # 2. プロジェクトが選択されている場合、質問生成を実行
        if current_project_id and assistant_reply != "[ERROR]":
            try:
                from core.question_generator import AdaptiveQuestionGenerator, create_conversation_context
                from core.dynamic_schema import get_project_schema
                from core.models import ProjectPhase
                
                # 会話分析と情報抽出
                from core.conversation_analyzer import analyze_conversation_and_update_project
                
                # 会話メッセージを準備
                conversation_messages = st.session_state["history"] + [
                    {"role": "user", "content": user_input},
                    {"role": "assistant", "content": assistant_reply}
                ]
                
                # 情報抽出と更新
                updated_count, conflicts = analyze_conversation_and_update_project(
                    conversation_messages[-6:],  # 最新3往復
                    current_project_id
                )
                
                if updated_count > 0:
                    logger.info(f"Updated {updated_count} project fields from conversation")
                
                # 質問生成の実行
                if "session_start_time" not in st.session_state:
                    st.session_state["session_start_time"] = datetime.now()
                
                # プロジェクトスキーマと会話文脈を取得
                project_schema = get_project_schema(current_project_id)
                conversation_context = create_conversation_context(
                    conversation_messages,
                    ProjectPhase.DEFINITION,  # デフォルトフェーズ
                    st.session_state["session_start_time"]
                )
                
                # 質問生成
                question_generator = AdaptiveQuestionGenerator()
                candidate_questions = question_generator.generate_contextual_questions(
                    project_schema, conversation_context, max_questions=2
                )
                
                # タイミング判定
                timed_questions = question_generator.determine_question_timing(
                    candidate_questions, conversation_context
                )
                
                # 質問をセッション状態に保存（応答には含めない）
                if timed_questions:
                    st.session_state["generated_questions"] = timed_questions
                else:
                    st.session_state["generated_questions"] = []
                
            except Exception as e:
                logger.error(f"Question generation failed: {e}")
                # エラーが発生しても基本応答は返す
                pass
        
        return assistant_reply
        
    except Exception as e:
        logger.error(f"OpenAI API call failed: {str(e)}")
        return f"❌ AI応答の生成に失敗しました: {e}"

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

# メインコンテンツの描画
render_page_content()

# ホームページの場合のみ会話機能を表示
if nav_state.current_page == PageType.HOME:
    render_chat_interface()

# 履歴表示（プロジェクト固有履歴＋セッション履歴）  
