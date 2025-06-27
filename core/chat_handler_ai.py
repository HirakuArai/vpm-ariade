# -*- coding: utf-8 -*-
"""
AI-First Chat Handler - 真のAI的チャット処理モジュール
統一されたAI判断による自然な会話処理
"""

import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
import streamlit as st
from zoneinfo import ZoneInfo

try:
    import openai
except ImportError:
    openai = None

# AI統合
from .ai_project_manager import create_ai_project_manager
from .enhanced_ui_components import InteractiveComponents, NotificationComponents

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

def process_chat_input_ai(user_input: str, current_project_id: Optional[str] = None):
    """
    AI-First チャット入力処理
    統一されたAI判断による自然な会話管理
    
    Args:
        user_input: ユーザーの入力
        current_project_id: 現在のプロジェクトID
    """
    from .navigation import navigator, PageType
    
    # Ensure navigation state is properly initialized
    if not hasattr(st.session_state, 'navigation_state') or st.session_state.navigation_state is None:
        navigator.initialize_session_state()
    
    # ログへ保存
    _append_log("user", user_input)
    
    # プロジェクト固有ログも保存
    if current_project_id:
        _append_project_log(current_project_id, "user", user_input)
        st.session_state["current_project_id"] = current_project_id
    else:
        st.session_state.navigation_state.current_page = PageType.HOME
        st.session_state.navigation_state.selected_project_id = None
        st.session_state["current_project_id"] = None

    # AI Project Manager の初期化
    api_key = get_openai_api_key()
    if not api_key:
        assistant_reply = "❌ OpenAI API キーが設定されていません。"
        _finalize_conversation(assistant_reply, current_project_id)
        return

    if "ai_project_manager" not in st.session_state:
        st.session_state["ai_project_manager"] = create_ai_project_manager(api_key)
    
    ai_pm = st.session_state["ai_project_manager"]
    
    # プロジェクト文脈の準備
    project_context = {}
    if current_project_id:
        try:
            from .project_service import get_project
            project_context = get_project(current_project_id) or {}
        except Exception as e:
            logger.error(f"Failed to get project context: {e}")
    
    # 会話履歴の準備
    conversation_history = st.session_state.get("history", [])
    
    # タイピングインジケータ表示
    typing_placeholder = st.empty()
    with typing_placeholder:
        st.info("🤖 AI プロジェクトマネージャーが分析中...")
    
    try:
        # 統一されたAI判断
        action_plan = ai_pm.process_user_input(
            user_input=user_input,
            project_context=project_context,
            conversation_history=conversation_history
        )
        
        # タイピングインジケータを削除
        typing_placeholder.empty()
        
        # アクションプランの実行
        assistant_reply = execute_action_plan(action_plan, current_project_id)
        
        # 学習データの表示（デバッグ用）
        if action_plan.confidence < 0.7:
            st.warning(f"⚠️ AI判断の信頼度が低いです（{action_plan.confidence:.2f}）")
            with st.expander("🔍 AI判断の詳細", expanded=False):
                st.write(f"**意図**: {action_plan.intent}")
                st.write(f"**アクション**: {action_plan.action_type}")
                st.write(f"**推論**: {action_plan.reasoning}")
                if action_plan.suggested_follow_ups:
                    st.write("**推奨される次の質問**:")
                    for follow_up in action_plan.suggested_follow_ups:
                        if st.button(f"💡 {follow_up}", key=f"follow_up_{hash(follow_up)}"):
                            # 推奨質問を自動入力（将来実装）
                            st.info(f"推奨質問: {follow_up}")
        
    except Exception as e:
        typing_placeholder.empty()
        logger.error(f"AI-first chat processing failed: {e}")
        assistant_reply = f"申し訳ありませんが、処理中にエラーが発生しました: {str(e)}"
        
        # エラー通知
        NotificationComponents.render_toast_notification(
            f"AI処理エラー: {str(e)}", 
            "error", 
            duration=5
        )
    
    # 会話の最終処理
    _finalize_conversation(assistant_reply, current_project_id)

def execute_action_plan(action_plan, current_project_id: Optional[str]) -> str:
    """
    AIが生成したアクションプランを実行
    
    Args:
        action_plan: AIが生成したアクションプラン
        current_project_id: 現在のプロジェクトID
        
    Returns:
        str: ユーザーへの応答メッセージ
    """
    try:
        if action_plan.action_type == "create_task":
            return _execute_task_creation(action_plan, current_project_id)
        
        elif action_plan.action_type == "remove_task":
            return _execute_task_removal(action_plan, current_project_id)
        
        elif action_plan.action_type == "update_status":
            return _execute_status_update(action_plan, current_project_id)
        
        elif action_plan.action_type == "information_request":
            return _execute_information_request(action_plan, current_project_id)
        
        elif action_plan.action_type == "general_discussion":
            return action_plan.response_content
        
        else:
            # 新しいアクションタイプに対応（AI的な創発性）
            logger.info(f"New action type detected: {action_plan.action_type}")
            return action_plan.response_content
            
    except Exception as e:
        logger.error(f"Action plan execution failed: {e}")
        return f"アクションの実行中にエラーが発生しました: {str(e)}"

def _execute_task_creation(action_plan, current_project_id: Optional[str]) -> str:
    """タスク作成の実行"""
    if not current_project_id:
        return "タスクを作成するには、まずプロジェクトを選択してください。"
    
    try:
        from .project_service import add_task, get_project
        
        success_count = 0
        for item in action_plan.target_items:
            if item.get("type") == "task":
                params = item.get("parameters", {})
                description = params.get("description", "新しいタスク")
                due_date = params.get("due_date", (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d"))
                
                add_task(current_project_id, description, due_date)
                success_count += 1
        
        if success_count > 0:
            # 現在のタスク一覧を取得
            project_data = get_project(current_project_id)
            tasks = project_data.get("tasks", []) if project_data else []
            
            task_list = "\n".join([f"[{t['id']}] {t['description']} (期日: {t['due_date']})" for t in tasks])
            return f"{action_plan.response_content}\n\n現在のタスク一覧:\n{task_list}"
        else:
            return action_plan.response_content
            
    except Exception as e:
        logger.error(f"Task creation failed: {e}")
        return f"タスク作成中にエラーが発生しました: {str(e)}"

def _execute_task_removal(action_plan, current_project_id: Optional[str]) -> str:
    """タスク削除の実行"""
    if not current_project_id:
        return "タスクを削除するには、プロジェクトを選択してください。"
    
    try:
        from .project_service import remove_task, remove_duplicate_tasks, get_project
        
        removed_count = 0
        for item in action_plan.target_items:
            if item.get("type") == "task":
                action = item.get("action", "")
                if "duplicate" in action.lower():
                    removed_count += remove_duplicate_tasks(current_project_id)
                else:
                    params = item.get("parameters", {})
                    task_id = params.get("task_id")
                    if task_id and remove_task(current_project_id, int(task_id)):
                        removed_count += 1
        
        if removed_count > 0:
            # 更新されたタスク一覧を取得
            project_data = get_project(current_project_id)
            tasks = project_data.get("tasks", []) if project_data else []
            
            task_list = "\n".join([f"[{t['id']}] {t['description']} (期日: {t['due_date']})" for t in tasks])
            return f"{removed_count}個のタスクを削除しました。\n\n現在のタスク一覧:\n{task_list}"
        else:
            return action_plan.response_content
            
    except Exception as e:
        logger.error(f"Task removal failed: {e}")
        return f"タスク削除中にエラーが発生しました: {str(e)}"

def _execute_status_update(action_plan, current_project_id: Optional[str]) -> str:
    """ステータス更新の実行"""
    if not current_project_id:
        return "ステータスを更新するには、プロジェクトを選択してください。"
    
    try:
        from .project_service import set_status
        
        for item in action_plan.target_items:
            if item.get("type") == "project":
                params = item.get("parameters", {})
                new_status = params.get("status")
                if new_status:
                    set_status(current_project_id, new_status)
        
        return action_plan.response_content
        
    except Exception as e:
        logger.error(f"Status update failed: {e}")
        return f"ステータス更新中にエラーが発生しました: {str(e)}"

def _execute_information_request(action_plan, current_project_id: Optional[str]) -> str:
    """情報リクエストの実行"""
    try:
        if current_project_id:
            from .project_service import get_project
            project_data = get_project(current_project_id)
            tasks = project_data.get("tasks", []) if project_data else []
            
            if tasks:
                task_list = "\n".join([f"[{t['id']}] {t['description']} (期日: {t['due_date']})" for t in tasks])
                return f"{action_plan.response_content}\n\n現在のタスク一覧:\n{task_list}"
        
        return action_plan.response_content
        
    except Exception as e:
        logger.error(f"Information request failed: {e}")
        return action_plan.response_content

def _finalize_conversation(assistant_reply: str, current_project_id: Optional[str]):
    """会話の最終処理"""
    # 会話履歴の更新
    if "history" not in st.session_state:
        st.session_state["history"] = []
    
    # ユーザー入力は既に追加されている想定
    if st.session_state["history"] and st.session_state["history"][-1]["role"] != "assistant":
        st.session_state["history"].append({"role": "assistant", "content": assistant_reply})
    
    # ログに保存
    _append_log("assistant", assistant_reply)
    if current_project_id:
        _append_project_log(current_project_id, "assistant", assistant_reply)
    
    # Git操作（既存機能維持）
    try:
        from .git_ops import commit_and_push_log, commit_and_push_project_data
        commit_and_push_log()
        if current_project_id:
            commit_and_push_project_data(current_project_id)
    except Exception as e:
        logger.error(f"Error pushing to git: {e}")
    
    # ナビゲーション状態の保持
    if not hasattr(st.session_state, 'navigation_state') or st.session_state.navigation_state is None:
        from .navigation import navigator
        navigator.initialize_session_state()
    
    if not current_project_id:
        st.session_state.navigation_state.current_page = PageType.HOME
        st.session_state.navigation_state.selected_project_id = None
        if "page" in st.query_params:
            st.query_params.clear()
    
    # ページ更新
    st.rerun()