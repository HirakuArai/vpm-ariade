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
from .navigation import PageType

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
    from .navigation import navigator
    
    # Ensure navigation state is properly initialized
    if not hasattr(st.session_state, 'navigation_state') or st.session_state.navigation_state is None:
        navigator.initialize_session_state()
    
    # セッション履歴にユーザー入力を追加
    if "history" not in st.session_state:
        st.session_state["history"] = []
    st.session_state["history"].append({"role": "user", "content": user_input})
    
    # ログへ保存
    _append_log("user", user_input)
    
    # プロジェクト固有ログも保存
    if current_project_id:
        _append_project_log(current_project_id, "user", user_input)
        st.session_state["current_project_id"] = current_project_id
        # プロジェクト会話の場合：現在のページ状態を保持
        st.session_state.navigation_state.selected_project_id = current_project_id
    else:
        # ホーム会話の場合のみナビゲーション状態をリセット
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
        result = execute_action_plan(action_plan, current_project_id)
        
        # プロジェクト作成の場合、新しいプロジェクトIDを取得
        if action_plan.action_type == "create_project":
            # セッションから新しく作成されたプロジェクトIDを取得
            new_project_id = st.session_state.get("current_project_id")
            if new_project_id and new_project_id != current_project_id:
                current_project_id = new_project_id
                logger.info(f"Updated current_project_id to newly created project: {current_project_id}")
        
        assistant_reply = result
        
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
        
        # 詳細なエラー情報をログに出力
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"Detailed error trace: {error_trace}")
        print(f"🚨 AI処理エラーの詳細: {error_trace}", flush=True)
        
        assistant_reply = f"申し訳ありませんが、処理中にエラーが発生しました。再度お試しください。"
        
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
        
        elif action_plan.action_type == "create_project":
            return _execute_project_creation(action_plan, current_project_id)
        
        elif action_plan.action_type == "update_project":
            return _execute_project_update(action_plan, current_project_id)
        
        elif action_plan.action_type == "general_discussion":
            return action_plan.response_content
        
        else:
            # 新しいアクションタイプに対応（AI的な創発性）
            logger.info(f"New action type detected: {action_plan.action_type}")
            return action_plan.response_content
            
    except Exception as e:
        logger.error(f"Action plan execution failed: {e}")
        
        # 詳細なエラー情報をログに出力
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"Action plan execution error trace: {error_trace}")
        print(f"🚨 アクションプラン実行エラー: {error_trace}", flush=True)
        
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
                description = params.get("description", "")
                due_date = params.get("due_date", "")
                
                # タスク説明が空の場合はスキップ（無意味なタスクを作成しない）
                if not description or description.strip() == "":
                    logger.warning(f"タスク作成スキップ: 説明が空です。Parameters: {params}")
                    continue
                
                # 期日が空の場合は「未設定」ではなく適切なデフォルトを設定
                if not due_date or due_date.strip() == "":
                    due_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
                
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
        from .project_service import remove_task, remove_duplicate_tasks, remove_task_by_description, get_project
        
        removed_count = 0
        for item in action_plan.target_items:
            if item.get("type") == "task":
                action = item.get("action", "")
                if "duplicate" in action.lower():
                    removed_count += remove_duplicate_tasks(current_project_id)
                else:
                    params = item.get("parameters", {})
                    task_id = params.get("task_id")
                    task_description = params.get("description", "")
                    
                    # IDベースの削除を優先的に試行
                    if task_id and remove_task(current_project_id, int(task_id)):
                        removed_count += 1
                    # IDが無い場合は説明文ベースで削除を試行
                    elif task_description and remove_task_by_description(current_project_id, task_description):
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
    """
    ステータス更新の実行 (DEPRECATED)
    
    ⚠️ DEPRECATED: この関数は非推奨です。新しいupdate_projectアクションを使用してください。
    Project Update Spec v1.0に従い、今後は汎用的なupdate_projectアクションを使用することを推奨します。
    """
    # Log deprecation warning
    logger.warning("🚨 DEPRECATED: update_status action used. Please migrate to update_project action with properties parameter.")
    
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

def _execute_project_creation(action_plan, current_project_id: Optional[str]) -> str:
    """プロジェクト作成の実行"""
    try:
        from .project_service import create_project
        from .navigation import navigator
        
        created_projects = []
        for item in action_plan.target_items:
            if item.get("type") == "project":
                params = item.get("parameters", {})
                project_name = params.get("name", "")
                project_description = params.get("description", "")
                
                # プロジェクト名が空の場合はスキップ
                if not project_name or project_name.strip() == "":
                    logger.warning(f"プロジェクト作成スキップ: 名前が空です。Parameters: {params}")
                    continue
                
                # プロジェクト作成
                project = create_project(
                    identifier=None,  # 自動生成
                    overview=project_description or project_name,  # 説明がなければ名前を使用
                    created_by="AI Assistant",
                    display_name=project_name
                )
                project_id = project.identifier
                created_projects.append({
                    "id": project_id,
                    "name": project_name,
                    "description": project_description
                })
                
                # 最初に作成されたプロジェクトを自動選択
                if len(created_projects) == 1:
                    # ナビゲーション状態を更新
                    if hasattr(st.session_state, 'navigation_state'):
                        st.session_state.navigation_state.selected_project_id = project_id
                        st.session_state["current_project_id"] = project_id
                    
                    logger.info(f"Created and selected project: {project_id}")
                    
                    # 新しく作成されたプロジェクトをGitにコミット
                    try:
                        from .git_ops import commit_and_push_project_data
                        commit_and_push_project_data(project_id)
                        logger.info(f"Successfully committed new project {project_id} to Git")
                    except Exception as e:
                        logger.error(f"Failed to commit new project {project_id} to Git: {e}")
        
        if created_projects:
            # 複数プロジェクト作成時もGitコミット
            if len(created_projects) > 1:
                for project in created_projects:
                    try:
                        from .git_ops import commit_and_push_project_data
                        commit_and_push_project_data(project['id'])
                        logger.info(f"Successfully committed project {project['id']} to Git")
                    except Exception as e:
                        logger.error(f"Failed to commit project {project['id']} to Git: {e}")
            
            if len(created_projects) == 1:
                project = created_projects[0]
                return f"{action_plan.response_content}\n\n✅ プロジェクト「{project['name']}」（ID: {project['id']}）を作成し、選択しました。"
            else:
                project_list = "\n".join([f"• {p['name']} (ID: {p['id']})" for p in created_projects])
                return f"{action_plan.response_content}\n\n✅ 以下のプロジェクトを作成しました:\n{project_list}"
        else:
            return action_plan.response_content
            
    except Exception as e:
        logger.error(f"Project creation failed: {e}")
        return f"プロジェクト作成中にエラーが発生しました: {str(e)}"

def _execute_project_update(action_plan, current_project_id: Optional[str]) -> str:
    """
    Generic Project Update Handler - Implements Project Update Spec v1.0
    
    Args:
        action_plan: ActionPlan with update_project action
        current_project_id: Current project ID
        
    Returns:
        str: User response message
    """
    if not current_project_id:
        return "プロジェクトを更新するには、まずプロジェクトを選択してください。"
    
    try:
        from .project_service import apply_property_patch
        
        total_updates = 0
        update_errors = []
        success_messages = []
        
        for item in action_plan.target_items:
            if item.get("type") == "project" and item.get("action") == "set_properties":
                params = item.get("parameters", {})
                project_id = params.get("identifier", current_project_id)
                properties = params.get("properties", {})
                
                if not properties:
                    logger.warning("No properties provided for project update")
                    continue
                
                # Apply the property patch
                result = apply_property_patch(project_id, properties)
                
                if result.get("success"):
                    changed_fields = result.get("changed_fields", [])
                    total_updates += len(changed_fields)
                    
                    # Generate user-friendly update messages
                    field_messages = []
                    for field in changed_fields:
                        value = properties[field]
                        if field == "start_date":
                            field_messages.append(f"開始日: {value}")
                        elif field == "end_date":
                            field_messages.append(f"終了日: {value}")
                        elif field == "participants_count":
                            field_messages.append(f"参加者数: {value}名")
                        elif field == "participants":
                            field_messages.append(f"参加者リスト: {len(value) if isinstance(value, list) else 1}名追加")
                        elif field == "status":
                            field_messages.append(f"ステータス: {value}")
                        elif field == "phase":
                            field_messages.append(f"フェーズ: {value}")
                        elif field == "budget":
                            field_messages.append(f"予算: {value}")
                        elif field == "location":
                            field_messages.append(f"場所: {value}")
                        elif field == "priority":
                            field_messages.append(f"優先度: {value}")
                        else:
                            field_messages.append(f"{field}: {value}")
                    
                    if field_messages:
                        success_messages.append("✅ 更新完了: " + "、".join(field_messages))
                    
                    logger.info(f"Successfully updated project {project_id}: {changed_fields}")
                    
                    # Handle warnings from the update
                    if result.get("warnings"):
                        update_errors.extend(result["warnings"])
                        
                else:
                    error_msg = result.get("error", "Unknown error")
                    error_type = result.get("error_type", "unknown")
                    update_errors.append(f"更新エラー ({error_type}): {error_msg}")
                    logger.error(f"Failed to update project {project_id}: {error_msg}")
        
        # Generate response message
        if total_updates > 0:
            response_parts = [action_plan.response_content]
            if success_messages:
                response_parts.extend(success_messages)
            
            if update_errors:
                response_parts.append("⚠️ 一部更新で問題が発生:")
                response_parts.extend([f"  - {error}" for error in update_errors])
            
            return "\n\n".join(response_parts)
        
        elif update_errors:
            return f"{action_plan.response_content}\n\n❌ 更新に失敗しました:\n" + "\n".join([f"  - {error}" for error in update_errors])
        
        else:
            return action_plan.response_content
            
    except Exception as e:
        logger.error(f"Project update execution failed: {e}")
        
        # Detailed error logging
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"Project update error trace: {error_trace}")
        print(f"🚨 プロジェクト更新エラー: {error_trace}", flush=True)
        
        return f"プロジェクト更新中にエラーが発生しました: {str(e)}"

def _finalize_conversation(assistant_reply: str, current_project_id: Optional[str]):
    """会話の最終処理"""
    # 会話履歴の更新
    if "history" not in st.session_state:
        st.session_state["history"] = []
    
    # アシスタントの応答を追加
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
    
    from .navigation import PageType
    
    # プロジェクト会話の場合は現在のページ状態を保持し、ホーム会話の場合のみHOMEに設定
    if not current_project_id:
        st.session_state.navigation_state.current_page = PageType.HOME
        st.session_state.navigation_state.selected_project_id = None
        if "page" in st.query_params:
            st.query_params.clear()
        # ホーム会話の場合のみ st.rerun() を実行
        st.rerun()
    else:
        # プロジェクト会話の場合は現在のページ状態を維持
        # （PROJECT_CHATページから呼ばれた場合はそのページに留まる）
        st.session_state.navigation_state.selected_project_id = current_project_id
        st.session_state["current_project_id"] = current_project_id
        
        # プロジェクト会話の場合も、ナビゲーション状態を明示的に保持
        if hasattr(st.session_state, 'navigation_state') and st.session_state.navigation_state.current_page:
            # 現在のページタイプを保持（PROJECT_CHATならそのまま維持）
            current_page = st.session_state.navigation_state.current_page
            if current_page == PageType.PROJECT_CHAT:
                # PROJECT_CHATページの場合はそのまま維持
                pass
            else:
                # 他のプロジェクトページからの場合はHOMEに戻さずに現在のページを維持
                pass
        # プロジェクト会話の場合は呼び出し元（pages.py）でページ更新を処理