# -*- coding: utf-8 -*-
"""
Chat Handler - チャット処理モジュール
app.pyからチャット処理ロジックを分離して循環インポートを回避
"""

import json
import logging
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
import streamlit as st
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

# JST timezone
_JST = ZoneInfo("Asia/Tokyo")

def get_openai_api_key():
    """OpenAI API キーの取得"""
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

def _today_log_path() -> Path:
    """Return Path for today's conversation log."""
    today = datetime.now(_JST).strftime("%Y%m%d")
    conv_dir = Path("conversations")
    conv_dir.mkdir(parents=True, exist_ok=True)
    return conv_dir / f"conversation_{today}.json"

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

def process_chat_input(user_input: str, current_project_id: Optional[str] = None):
    """
    チャット入力の処理（app.pyから分離）
    
    Args:
        user_input: ユーザーの入力
        current_project_id: 現在のプロジェクトID（プロジェクトページからの場合）
    """
    from .navigation import navigator, PageType
    from .project_service import create_project, set_status, add_task
    
    # Ensure navigation state is properly initialized
    if not hasattr(st.session_state, 'navigation_state') or st.session_state.navigation_state is None:
        navigator.initialize_session_state()
    
    # 1) ログへ保存
    _append_log("user", user_input)
    
    # Also log to project-specific log if project is selected
    if current_project_id:
        _append_project_log(current_project_id, "user", user_input)
        # Backward compatibility
        st.session_state["current_project_id"] = current_project_id
    else:
        # ホームページでの会話を明示的に保持
        st.session_state.navigation_state.current_page = PageType.HOME
        st.session_state.navigation_state.selected_project_id = None
        st.session_state["current_project_id"] = None

    # Handle project creation flow
    assistant_reply = None
    
    # Check if we're waiting for project overview
    if st.session_state.get("awaiting_project_overview", False):
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
    elif st.session_state.get("awaiting_activate_confirm", False):
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
    
    # AI-based task addition intent detection
    elif current_project_id and st.session_state.get("ai_intent_detector"):
        from .project_prompt import get_cached_project_context
        detector = st.session_state["ai_intent_detector"]
        
        # Get project context for better task detection
        try:
            project_context = get_cached_project_context(current_project_id)
        except:
            project_context = None
            
        task_intent = detector.detect_task_addition_intent(user_input, project_context)
        
        if task_intent["is_task_intent"] and task_intent["confidence"] > 0.7:
            try:
                description = task_intent["task_description"]
                due_date = task_intent["due_date"]
                
                if due_date:
                    # 期限付きタスク
                    add_task(current_project_id, description, due_date)
                else:
                    # 期限なしタスク（現在のadd_task関数を拡張する必要がある場合）
                    import datetime
                    default_due = (datetime.datetime.now() + datetime.timedelta(days=7)).strftime("%Y-%m-%d")
                    add_task(current_project_id, description, default_due)
                
                # Get current tasks for display
                path = Path(f"data/projects/{current_project_id}.json")
                data = json.loads(path.read_text())
                tasks = data.get("tasks", [])
                
                task_list = "\n".join([f"- {t['id']}: {t['description']} (期日: {t['due_date']})" for t in tasks])
                
                # 抽出されたデータがあれば追加情報として表示
                extracted_info = ""
                if task_intent["extracted_data"]:
                    extracted_info = "\n\n**検出された情報:**\n"
                    for key, value in task_intent["extracted_data"].items():
                        if value:
                            extracted_info += f"- {key}: {value}\n"
                
                assistant_reply = f"タスクを追加しました: **{description}**\n\n現在のタスク一覧:\n{task_list}{extracted_info}"
                
            except Exception as e:
                assistant_reply = f"タスク追加中にエラーが発生しました: {str(e)}"
    
    # Fallback: Check for traditional task command pattern
    elif user_input.startswith("タスク "):
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
                        add_task(current_project_id, description, due_date)
                        
                        # Get current tasks for display
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
    
    # AI-based project creation intent detection
    elif st.session_state.get("ai_intent_detector"):
        detector = st.session_state["ai_intent_detector"]
        project_intent = detector.detect_project_creation_intent(user_input)
        
        if project_intent["is_creation_intent"] and project_intent["confidence"] > 0.8:
            try:
                display_name = project_intent["project_name"]
                overview = project_intent["project_description"]
                
                # Create project directly
                project = create_project(None, overview, "human_user", display_name)
                st.session_state["created_project_id"] = project.identifier
                
                # Update navigation state
                st.session_state.navigation_state.selected_project_id = project.identifier
                st.session_state["current_project_id"] = project.identifier
                
                st.session_state["awaiting_activate_confirm"] = True
                
                # 抽出されたデータがあれば追加情報として表示
                extracted_info = ""
                if project_intent["extracted_data"]:
                    extracted_info = "\n\n**検出された情報:**\n"
                    for key, value in project_intent["extracted_data"].items():
                        if value:
                            extracted_info += f"- {key}: {value}\n"
                
                assistant_reply = f"プロジェクト **{display_name}** を DRAFT で作成しました。次は ACTIVE にしますか？{extracted_info}"
                
            except Exception as e:
                assistant_reply = f"プロジェクト作成中にエラーが発生しました: {str(e)}"
    
    # Enhanced conversation flow with question generation
    if assistant_reply is None:
        assistant_reply = process_ai_conversation(user_input, current_project_id)
    
    # Update conversation history
    if "history" not in st.session_state:
        st.session_state["history"] = []
    st.session_state["history"].append({"role": "user", "content": user_input})
    st.session_state["history"].append({"role": "assistant", "content": assistant_reply})
    
    # Also log assistant reply
    _append_log("assistant", assistant_reply)
    if current_project_id:
        _append_project_log(current_project_id, "assistant", assistant_reply)
    
    # Auto-push after conversation
    try:
        from .git_ops import commit_and_push_log, commit_and_push_project_data
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
    
    # Ensure navigation state is preserved before rerun
    if not hasattr(st.session_state, 'navigation_state') or st.session_state.navigation_state is None:
        navigator.initialize_session_state()
    
    # Explicitly maintain home page state for non-project conversations
    if not current_project_id:
        st.session_state.navigation_state.current_page = PageType.HOME
        st.session_state.navigation_state.selected_project_id = None
        # Also clear any potential URL parameters that might interfere
        if "page" in st.query_params:
            st.query_params.clear()

def process_ai_conversation(user_input: str, current_project_id: Optional[str]) -> str:
    """AI会話処理"""
    try:
        from .project_prompt import get_full_system_prompt
        import openai
        
        # OpenAI クライアント設定
        api_key = get_openai_api_key()
        if not api_key:
            return "❌ OpenAI API キーが設定されていません。"
        
        # 1. 基本的なAI応答生成
        system_prompt = get_full_system_prompt()
        messages = [{"role": "system", "content": system_prompt}] + \
                  st.session_state.get("history", []) + \
                  [{"role": "user", "content": user_input}]
        
        # Performance optimization: limit history to last 5 exchanges to reduce old data influence
        if len(st.session_state.get("history", [])) > 10:  # 10 messages = 5 exchanges
            recent_history = st.session_state["history"][-10:]
            messages = [{"role": "system", "content": system_prompt}] + \
                      recent_history + \
                      [{"role": "user", "content": user_input}]
        
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            max_tokens=800,
            temperature=0.7
        )
        
        assistant_reply = response.choices[0].message.content.strip()
        
        return assistant_reply
        
    except Exception as e:
        logger.error(f"OpenAI API call failed: {str(e)}")
        return f"❌ AI応答の生成に失敗しました: {e}"