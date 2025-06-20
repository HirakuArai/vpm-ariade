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
import yaml, pandas as pd
import streamlit as st

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(page_title="Kai VPM", page_icon="💬", initial_sidebar_state="collapsed")

# ────────────────────────────────────────────────────────────────────────────
# Kai modules
# ────────────────────────────────────────────────────────────────────────────
from core.git_ops import commit_and_push_log  # ← NEW: auto‑push helper
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
    load_dotenv()
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

@st.cache_data(ttl=60)  # Cache for 1 minute
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
    
    current_project_id = st.session_state.get("current_project_id")
    if current_project_id:
        project_context = get_cached_project_context(current_project_id)
        if project_context:
            return f"{base_prompt}\n\n{project_context}"
    
    return base_prompt

# ────────────────────────────────────────────────────────────────────────────
# Streamlit UI
# ────────────────────────────────────────────────────────────────────────────
st.title("Kai – Virtual Project Manager Chat")

# ────────────────────────────────────────────────────────────────────────────
# Project Selector UI
# ────────────────────────────────────────────────────────────────────────────
project_ids = get_available_project_ids()
if project_ids:
    # Create options for selectbox
    project_options = ["プロジェクトを選択してください"] + [
        get_project_summary(pid) for pid in project_ids
    ]
    
    # Map display names back to IDs
    display_to_id = {get_project_summary(pid): pid for pid in project_ids}
    
    selected_display = st.selectbox("💼 プロジェクトを選択", project_options)
    
    if selected_display != "プロジェクトを選択してください":
        st.session_state["current_project_id"] = display_to_id[selected_display]
        st.success(f"✅ プロジェクト '{display_to_id[selected_display]}' を選択しました")
    else:
        if "current_project_id" in st.session_state:
            del st.session_state["current_project_id"]
else:
    st.info("📝 まずプロジェクトを作成してください。下記の「プロジェクト作成」コマンドを使用できます。")

if "history" not in st.session_state:
    st.session_state["history"] = []

# Project creation flow state
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

# 履歴表示（プロジェクト固有履歴＋セッション履歴）
def load_project_conversation_history(project_id: str) -> list:
    """プロジェクト固有の会話履歴を読み込み"""
    project_conv_dir = Path(f"data/conversations/{project_id}")
    history = []
    
    if project_conv_dir.exists():
        # 最新の会話ログファイルを取得
        today = datetime.now(_JST).strftime("%Y%m%d")
        log_file = project_conv_dir / f"{today}.jsonl"
        
        if log_file.exists():
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        entry = json.loads(line.strip())
                        history.append({
                            "role": entry["role"],
                            "content": entry["content"]
                        })
            except Exception as e:
                print(f"Error loading project history: {e}")
    
    return history

# プロジェクト固有の履歴を表示
current_project_id = st.session_state.get("current_project_id")
if current_project_id:
    project_history = load_project_conversation_history(current_project_id)
    if project_history:
        st.markdown("### 📜 プロジェクト会話履歴")
        for msg in project_history[-10:]:  # 最新10件を表示
            st.chat_message("user" if msg["role"] == "user" else "assistant").markdown(msg["content"])
        
        if len(project_history) > 10:
            st.caption(f"（{len(project_history)}件中、最新10件を表示）")

# セッション履歴表示
if st.session_state["history"]:
    st.markdown("### 💬 現在のセッション")
    for msg in st.session_state["history"]:
        st.chat_message("user" if msg["role"] == "user" else "assistant").markdown(msg["content"])

# ユーザー入力
if not st.session_state.get("current_project_id"):
    st.info("💡 プロジェクト作成は下記の入力欄で「プロジェクト作成」と入力してください。")

# チャット入力は常に有効（プロジェクト作成のため）
user_input = st.chat_input("メッセージを入力してください…（プロジェクト作成は「プロジェクト作成」と入力）")

if user_input:
    # 1) ログへ保存
    _append_log("user", user_input)
    
    # Also log to project-specific log if project is selected
    current_project_id = st.session_state.get("current_project_id")
    if current_project_id:
        _append_project_log(current_project_id, "user", user_input)

    # Handle project creation flow
    assistant_reply = None
    
    # Check if we're waiting for project overview
    if st.session_state["awaiting_project_overview"]:
        try:
            # Create project with auto-generated ID
            project = create_project(None, user_input, "human_user")
            st.session_state["created_project_id"] = project.identifier
            st.session_state["current_project_id"] = project.identifier  # Set as current project
            st.session_state["awaiting_project_overview"] = False
            st.session_state["awaiting_activate_confirm"] = True
            assistant_reply = f"プロジェクト **{project.identifier}** を DRAFT で作成しました。次は ACTIVE にしますか？"
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
                if st.session_state["current_project_id"]:
                    try:
                        task = add_task(st.session_state["current_project_id"], description, due_date)
                        
                        # Get current tasks for display
                        import json
                        path = Path(f"data/projects/{st.session_state['current_project_id']}.json")
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
        assistant_reply = "プロジェクトの概要を一行で教えてください。"
    
    # Default GPT handling if no project creation flow
    if assistant_reply is None:
        try:
            system_prompt = get_full_system_prompt()
            messages = [{"role": "system", "content": system_prompt}] + \
                      st.session_state["history"] + \
                      [{"role": "user", "content": user_input}]
            
            # Performance optimization: limit history to last 10 exchanges
            if len(st.session_state["history"]) > 20:  # 20 messages = 10 exchanges
                recent_history = st.session_state["history"][-20:]
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
        except Exception as e:
            logger.error(f"OpenAI API call failed: {str(e)}")
            st.error(f"❌ OpenAI 呼び出し失敗: {e}")
            assistant_reply = "[ERROR]"

    # 自動更新は一時無効化（手動更新のみ）
    # Hook: Manual update candidates generation only
    if st.session_state.get("current_project_id") and assistant_reply != "[ERROR]":
        try:
            combined_content = f"{user_input} {assistant_reply}"
            new_data = extract_new_data_from_chat(combined_content, st.session_state["current_project_id"])
            
            if new_data:
                candidates = generate_update_candidates(st.session_state["current_project_id"], new_data)
                valid_candidates = [c for c in candidates if validate_update_candidate(c)]
                
                if valid_candidates:
                    st.session_state["update_candidates"] = valid_candidates
        except Exception as e:
            print(f"Manual update generation error: {e}")

    # 3) UI 表示
    st.chat_message("user").markdown(user_input)
    st.chat_message("assistant").markdown(assistant_reply)

    # 4) 履歴保存 & ログへ保存
    st.session_state["history"].extend([
        {"role": "user", "content": user_input},
        {"role": "assistant", "content": assistant_reply},
    ])
    _append_log("assistant", assistant_reply)
    
    # Also log assistant reply to project-specific log
    if current_project_id:
        _append_project_log(current_project_id, "assistant", assistant_reply)

    # 5) Git push (conversation log only)
    try:
        commit_and_push_log(_today_log_path())
    except Exception as e:
        st.warning(f"⚠️ Git push failed: {e}")

# --- 更新案 UI (Update Proposals) ---
if st.session_state.get("update_candidates"):
    with st.expander("📝 更新案を確認・承認", expanded=True):
        st.write("チャット中に確認された新情報に基づく更新候補です：")
        
        # Display update candidates
        for i, diff in enumerate(st.session_state["update_candidates"]):
            st.write(f"**{diff['field']}**: {diff['old']} → {diff['new']}")
        
        # Show summary
        summary = generate_diff_summary(st.session_state["update_candidates"])
        st.markdown(summary)
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            if st.button("✅ 承認して反映", type="primary"):
                if st.session_state.get("current_project_id"):
                    try:
                        result = apply_updates(
                            st.session_state["current_project_id"], 
                            st.session_state["update_candidates"]
                        )
                        
                        if result["success"]:
                            success_msg = f"✅ {result['updates_applied']} 件の更新を適用しました。"
                            if result.get("git_committed"):
                                success_msg += " Git にもコミットしました。"
                            elif "git_error" in result:
                                success_msg += f" Git コミットに失敗: {result['git_error']}"
                            
                            st.success(success_msg)
                            # Clear update candidates after applying
                            st.session_state["update_candidates"] = []
                            st.rerun()
                        else:
                            st.error(f"❌ 更新の適用に失敗しました: {result.get('error', '不明なエラー')}")
                    except Exception as e:
                        st.error(f"❌ 更新適用中にエラーが発生しました: {str(e)}")
                else:
                    st.error("❌ 現在のプロジェクトが選択されていません。")
        
        with col2:
            if st.button("❌ キャンセル"):
                st.session_state["update_candidates"] = []
                st.rerun()

# --- 通知システム UI ---
if st.session_state.get("current_project_id"):
    try:
        notification_system = NotificationSystem()
        
        # 最新の通知を表示（実際の実装では通知キューから取得）
        if hasattr(notification_system, 'notification_queue') and not notification_system.notification_queue.empty():
            with st.expander("🔔 最新の通知", expanded=False):
                st.write("新しい通知があります")
                # 実際の通知内容表示は notification_system の実装に依存
        
        # 進捗アラートをチェックして通知を生成
        try:
            progress_monitor = ProgressMonitor()
            report = progress_monitor.monitor_project(st.session_state["current_project_id"])
            
            if report.alerts:
                # 重要なアラートを通知として処理
                critical_alerts = [a for a in report.alerts if a.level.value == "critical"]
                if critical_alerts:
                    notification_system.process_progress_alerts(
                        st.session_state["current_project_id"], 
                        critical_alerts
                    )
                    
                    # 通知バッジ表示
                    if len(critical_alerts) > 0:
                        st.error(f"🚨 {len(critical_alerts)}件の重要なアラートがあります")
        
        except Exception as e:
            # 通知システムエラーは非表示にして続行
            pass
            
    except Exception as e:
        # 通知システム全体のエラーも非表示にして続行
        pass

# --- サイドバーにタブを追加 ---
with st.sidebar:
    # プロジェクトフェーズ管理UI
    if st.session_state.get("current_project_id"):
        st.markdown("## 🔄 プロジェクトフェーズ")
        render_phase_management_ui(st.session_state["current_project_id"])
        
        # 進捗モニタリング情報（パフォーマンス最適化）
        st.markdown("## 📊 プロジェクト健康状態")
        try:
            progress_monitor = ProgressMonitor()
            report = progress_monitor.monitor_project(st.session_state["current_project_id"])
            
            # 健康状態表示
            health_color = {
                "healthy": "🟢",
                "at_risk": "🟡", 
                "critical": "🔴"
            }
            st.write(f"{health_color.get(report.overall_health, '⚪')} **状態**: {report.overall_health}")
            
            # メトリクス表示
            col1, col2 = st.columns(2)
            with col1:
                completion_rate = report.metrics.get("task_completion_rate", 0)
                st.metric("完了率", f"{completion_rate:.1%}")
            with col2:
                risk_score = report.metrics.get("risk_score", 0)
                st.metric("リスクスコア", f"{risk_score:.2f}")
            
            # アラート表示
            if report.alerts:
                st.markdown("### ⚠️ アラート")
                for alert in report.alerts[:3]:  # 最大3件表示
                    level_icon = {"critical": "🔴", "warning": "🟡", "info": "🔵"}
                    st.write(f"{level_icon.get(alert.level.value, '⚪')} {alert.title}")
                
        except Exception as e:
            st.error(f"進捗監視エラー: {str(e)}")
        
        # 今後の期限表示（最適化）
        with st.expander("📅 今後の期限", expanded=False):
            try:
                from core.schedule_manager import ScheduleManager
                # Cache deadline data
                @st.cache_data(ttl=300)  # Cache for 5 minutes
                def get_project_deadlines(project_id: str):
                    schedule_manager = ScheduleManager()
                    deadlines = schedule_manager.get_upcoming_deadlines(days_ahead=7)
                    return [d for d in deadlines if d["project_id"] == project_id]
                
                project_deadlines = get_project_deadlines(st.session_state["current_project_id"])
                
                if project_deadlines:
                    for deadline in project_deadlines[:3]:  # 最大3件
                        days_remaining = deadline["days_remaining"]
                        urgency_icon = "🔴" if days_remaining <= 1 else "🟡" if days_remaining <= 3 else "🟢"
                        st.write(f"{urgency_icon} **{deadline['event_title']}**")
                        st.write(f"   期限: {deadline['deadline']} ({days_remaining}日後)")
                else:
                    st.write("今後7日以内の期限はありません")
                    
            except Exception as e:
                st.write("スケジュール情報の取得に失敗しました")
    
    st.markdown("## 📑 議事録")
    sel_day = st.date_input("対象日を選択", value=date.today())
    if st.button("📝 minutes生成/再生成"):
        minutes_path = generate_daily_minutes(sel_day, force=True)
        st.success(f"minutes を再生成しました: {minutes_path.name}")

# --- メイン領域に minutes 表示 ---
if "minutes" not in st.session_state:
    st.session_state["minutes"] = None

minutes_path = Path(f"docs/minutes/{sel_day.year}/minutes_{sel_day:%Y%m%d}.yaml")
if minutes_path.exists():
    minutes_yaml = yaml.safe_load(minutes_path.read_text())
    st.session_state["minutes"] = minutes_yaml

    st.markdown(render_md(minutes_path), unsafe_allow_html=True)

    # Decisions 編集
    df = pd.DataFrame(minutes_yaml["decisions"])
    edited = st.data_editor(df,
        column_config={"status": st.column_config.SelectboxColumn(
            options=["AUTO", "CONFIRMED", "CANCELLED"])},
        use_container_width=True,
        key="minutes_edit")
    if st.button("💾 Save & Commit"):
        minutes_yaml["decisions"] = edited.to_dict("records")
        minutes_path.write_text(yaml.safe_dump(minutes_yaml, sort_keys=False))
        safe_push_minutes(f"docs: update minutes {sel_day:%Y-%m-%d}")
        st.success("minutes saved & pushed")

# ────────────────────────────────────────────────────────────────────────────
# Footer / debug info (optional)
# ────────────────────────────────────────────────────────────────────────────
st.caption("version: 2025-06-21 統合版 - 会話記録・プロジェクト更新システム修正済み")