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
from datetime import date, datetime
from pathlib import Path
from textwrap import dedent
from zoneinfo import ZoneInfo
import yaml, pandas as pd
import streamlit as st

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
# Prompt generator
# ────────────────────────────────────────────────────────────────────────────

def get_system_prompt() -> str:
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
    
    # Add project context if available
    project_context = ""
    current_project_id = st.session_state.get("current_project_id")
    if current_project_id:
        project_context = get_project_prompt(current_project_id)
    
    base_prompt = "\n\n".join([rules, dsl_block, proj, arch])
    
    if project_context:
        return f"{base_prompt}\n\n{project_context}"
    else:
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

# 履歴表示（セッション全件を常時下スクロール表示）
for msg in st.session_state["history"]:
    st.chat_message("user" if msg["role"] == "user" else "assistant").markdown(msg["content"])

# ユーザー入力
if not st.session_state.get("current_project_id"):
    st.warning("⚠️ まずプロジェクトを選択してください。")
    user_input = None
else:
    user_input = st.chat_input("あなたの発言を入力してください…")

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
            system_prompt = get_system_prompt()
            messages = [{"role": "system", "content": system_prompt}] + \
                      st.session_state["history"] + \
                      [{"role": "user", "content": user_input}]
            response = openai.chat.completions.create(
                model="gpt-4.1",
                messages=messages,
            )
            assistant_reply = response.choices[0].message.content.strip()
        except Exception as e:
            st.error(f"❌ OpenAI 呼び出し失敗: {e}")
            traceback.print_exc()
            assistant_reply = "[ERROR]"

    # Hook: Generate update candidates from chat content
    if st.session_state.get("current_project_id") and assistant_reply != "[ERROR]":
        try:
            # Extract potential project updates from both user input and assistant reply
            combined_content = f"{user_input} {assistant_reply}"
            new_data = extract_new_data_from_chat(combined_content, st.session_state["current_project_id"])
            
            if new_data:
                # Generate update candidates
                candidates = generate_update_candidates(st.session_state["current_project_id"], new_data)
                
                # Validate candidates before adding
                valid_candidates = [c for c in candidates if validate_update_candidate(c)]
                
                if valid_candidates:
                    # Store in session state for UI display
                    st.session_state["update_candidates"] = valid_candidates
        except Exception as e:
            # Silently ignore errors in update candidate generation
            print(f"Error generating update candidates: {e}")

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

# --- サイドバーにタブを追加 ---
with st.sidebar:
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
st.caption("version: 2025-05-19 JSON‑log + auto‑push enabled")
