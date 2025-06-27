# -*- coding: utf-8 -*-
"""
Chat Handler - チャット処理モジュール
app.pyからチャット処理ロジックを分離して循環インポートを回避
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

# 新しいAI機能の統合
from .ai_context_manager import create_context_manager
from .ai_quality_manager import create_quality_manager
from .enhanced_ui_components import InteractiveComponents, FeedbackComponents, NotificationComponents

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
        # AI-based activation intent detection
        if st.session_state.get("ai_intent_detector"):
            detector = st.session_state["ai_intent_detector"]
            
            # Simple activation intent prompt
            activation_prompt = f"""
ユーザーの以下の発言は、プロジェクトをACTIVEにすることへの同意を示していますか？

発言: "{user_input}"

以下のJSONで回答してください：
{{
    "is_activation_intent": true/false,
    "confidence": 0.0-1.0,
    "reasoning": "判定理由"
}}

同意を示すパターン例：
- はい、アクティブにしてください
- yes, please activate
- 進めてください
- そうしましょう
- 承認します

質問や追加情報の場合は is_activation_intent: false にしてください。
"""
            
            try:
                if not openai:
                    raise ImportError("OpenAI not available")
                response = openai.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "あなたは意図検出の専門家です。ユーザーの発言からアクティベーション意図を正確に判定してください。"},
                        {"role": "user", "content": activation_prompt}
                    ],
                    temperature=0.1,
                    max_tokens=200
                )
                
                result = json.loads(response.choices[0].message.content.strip())
                
                if result.get("is_activation_intent", False) and result.get("confidence", 0) > 0.7:
                    try:
                        set_status(st.session_state["created_project_id"], "ACTIVE")
                        assistant_reply = f"プロジェクト **{st.session_state['created_project_id']}** を ACTIVE に設定しました！"
                    except Exception as e:
                        assistant_reply = f"ステータス更新中にエラーが発生しました: {str(e)}"
                    
                    # Reset flow state
                    st.session_state["awaiting_activate_confirm"] = False
                    st.session_state["created_project_id"] = None
                else:
                    # Continue conversation without activating, but provide context
                    assistant_reply = f"承知しました。プロジェクトは現在DRAFT状態です。\n\n{user_input}\n\nプロジェクトをACTIVEにする準備ができましたら「はい、アクティブにしてください」とお知らせください。"
                    # Don't reset the awaiting state - keep waiting for activation
                    
            except Exception as e:
                logger.error(f"AI activation intent detection failed: {e}")
                # Fallback to simple pattern matching
                user_lower = user_input.lower().strip()
                if any(word in user_lower for word in ["はい", "yes", "する", "active", "アクティブ"]):
                    try:
                        set_status(st.session_state["created_project_id"], "ACTIVE")
                        assistant_reply = f"プロジェクト **{st.session_state['created_project_id']}** を ACTIVE に設定しました！"
                    except Exception as e:
                        assistant_reply = f"ステータス更新中にエラーが発生しました: {str(e)}"
                    
                    # Reset flow state
                    st.session_state["awaiting_activate_confirm"] = False
                    st.session_state["created_project_id"] = None
                else:
                    assistant_reply = f"承知しました。プロジェクトは現在DRAFT状態です。\n\n{user_input}\n\nプロジェクトをACTIVEにする準備ができましたら「はい、アクティブにしてください」とお知らせください。"
                    # Don't reset the awaiting state - keep waiting for activation
        else:
            # Fallback when AI detector is not available
            user_lower = user_input.lower().strip()
            if any(word in user_lower for word in ["はい", "yes", "する", "active", "アクティブ"]):
                try:
                    set_status(st.session_state["created_project_id"], "ACTIVE")
                    assistant_reply = f"プロジェクト **{st.session_state['created_project_id']}** を ACTIVE に設定しました！"
                except Exception as e:
                    assistant_reply = f"ステータス更新中にエラーが発生しました: {str(e)}"
            else:
                assistant_reply = f"承知しました。プロジェクトは現在DRAFT状態です。\n\n{user_input}\n\nプロジェクトをACTIVEにする準備ができましたら「はい、アクティブにしてください」とお知らせください。"
            
            # Only reset flow state if activation was confirmed
            if any(word in user_input.lower().strip() for word in ["はい", "yes", "する", "active", "アクティブ"]):
                st.session_state["awaiting_activate_confirm"] = False
                st.session_state["created_project_id"] = None
    
    # AI-based task removal intent detection (check before task addition)
    elif current_project_id and st.session_state.get("ai_intent_detector"):
        from .project_service import remove_task, remove_duplicate_tasks, get_project
        detector = st.session_state["ai_intent_detector"]
        
        # Get current tasks for context
        project_data = get_project(current_project_id)
        current_tasks = project_data.get("tasks", []) if project_data else []
        
        # Check for task removal intent first
        removal_intent = detector.detect_task_removal_intent(user_input, current_tasks)
        
        if removal_intent["is_removal_intent"] and removal_intent["confidence"] > 0.7:
            try:
                if removal_intent["is_duplicate_removal"]:
                    # Remove duplicate tasks
                    removed_count = remove_duplicate_tasks(current_project_id)
                    if removed_count > 0:
                        # Get updated task list
                        updated_project = get_project(current_project_id)
                        updated_tasks = updated_project.get("tasks", [])
                        task_list = "\n".join([f"- [{t['id']}] {t['description']} (期日: {t['due_date']})" for t in updated_tasks])
                        assistant_reply = f"重複タスクを{removed_count}個削除しました。\n\n現在のタスク一覧:\n{task_list}"
                    else:
                        assistant_reply = "重複するタスクは見つかりませんでした。"
                
                elif removal_intent["target_task_ids"]:
                    # Remove specific tasks
                    removed_count = 0
                    for task_id in removal_intent["target_task_ids"]:
                        if remove_task(current_project_id, task_id):
                            removed_count += 1
                    
                    if removed_count > 0:
                        # Get updated task list
                        updated_project = get_project(current_project_id)
                        updated_tasks = updated_project.get("tasks", [])
                        task_list = "\n".join([f"- [{t['id']}] {t['description']} (期日: {t['due_date']})" for t in updated_tasks])
                        assistant_reply = f"タスクを{removed_count}個削除しました。\n\n現在のタスク一覧:\n{task_list}"
                    else:
                        assistant_reply = "指定されたタスクが見つかりませんでした。"
                
                else:
                    assistant_reply = "削除対象のタスクを明確に指定してください。例：「タスク1を削除」「重複を削除」"
                    
            except Exception as e:
                assistant_reply = f"タスク削除中にエラーが発生しました: {str(e)}"
        
        # If not removal intent, check for task addition
        elif not removal_intent["is_removal_intent"]:
            from .project_prompt import get_cached_project_context
            
            # Get project context for better task detection
            try:
                project_context = get_cached_project_context(current_project_id)
            except:
                project_context = None
                
            task_intent = detector.detect_task_addition_intent(user_input, project_context)
            
            if task_intent["is_task_intent"] and task_intent["confidence"] > 0.7:
                try:
                    from .project_service import add_task
                    
                    description = task_intent["task_description"]
                    due_date = task_intent["due_date"]
                    
                    if due_date:
                        # 期限付きタスク
                        add_task(current_project_id, description, due_date)
                    else:
                        # 期限なしタスク（現在のadd_task関数を拡張する必要がある場合）
                        default_due = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
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
    
    # Rerun to display the new messages
    st.rerun()

def process_ai_conversation(user_input: str, current_project_id: Optional[str]) -> str:
    """高度AI機能統合版の会話処理"""
    try:
        from .project_prompt import get_full_system_prompt
        
        # API キー確認
        api_key = get_openai_api_key()
        if not api_key:
            return "❌ OpenAI API キーが設定されていません。"
        
        # 品質管理システム初期化
        if "ai_quality_manager" not in st.session_state:
            st.session_state["ai_quality_manager"] = create_quality_manager(api_key)
        
        quality_manager = st.session_state["ai_quality_manager"]
        
        # コンテキスト管理システム初期化
        if "ai_context_manager" not in st.session_state:
            st.session_state["ai_context_manager"] = create_context_manager(api_key)
        
        context_manager = st.session_state["ai_context_manager"]
        
        # システムプロンプト取得
        system_prompt = get_full_system_prompt(current_project_id)
        
        # 現在の会話メッセージ
        current_messages = st.session_state.get("history", []) + [{"role": "user", "content": user_input}]
        
        # 最適化されたコンテキストウィンドウ構築
        context_window = context_manager.build_context_window(
            current_messages=current_messages,
            current_query=user_input,
            project_id=current_project_id,
            system_prompt=system_prompt
        )
        
        # メッセージ構築（コンテキストウィンドウを使用）
        messages = [{"role": "system", "content": context_window.system_prompt}]
        messages.extend(context_window.relevant_history)
        messages.extend(context_window.current_conversation)
        
        # タイピングインジケータ表示
        typing_indicator = InteractiveComponents.render_typing_indicator()
        typing_placeholder = st.empty()
        
        with typing_placeholder:
            st.info("🤖 AI が回答を生成中...")
        
        # 品質管理付きAIリクエスト実行
        ai_response = quality_manager.make_request_with_quality_check(
            messages=messages,
            model="gpt-4o",
            temperature=0.7,
            max_tokens=800
        )
        
        # タイピングインジケータを削除
        typing_placeholder.empty()
        
        # エラーハンドリング
        if ai_response.error_type:
            error_msg = ai_response.error_message or "不明なエラーが発生しました"
            
            # エラー通知表示
            NotificationComponents.render_toast_notification(
                f"エラー: {error_msg}", 
                "error", 
                duration=5
            )
            
            return f"❌ {error_msg}"
        
        # 品質チェック
        if ai_response.quality_score and ai_response.quality_score < 0.6:
            # 品質が低い場合の警告
            st.warning(f"⚠️ AI応答の品質が低い可能性があります（スコア: {ai_response.quality_score:.2f}）")
        
        # 会話をコンテキストに追加
        conversation_messages = [
            {"role": "user", "content": user_input},
            {"role": "assistant", "content": ai_response.response}
        ]
        context_manager.add_conversation(current_project_id, conversation_messages)
        
        # 成功通知（高品質な応答の場合）
        if ai_response.quality_score and ai_response.quality_score > 0.9:
            NotificationComponents.render_toast_notification(
                "✨ 高品質な応答が生成されました", 
                "success", 
                duration=2
            )
        
        logger.info(f"AI conversation processed successfully. Quality: {ai_response.quality_score:.2f}")
        return ai_response.response
        
    except Exception as e:
        logger.error(f"Enhanced AI conversation failed: {str(e)}")
        
        # エラー通知
        NotificationComponents.render_toast_notification(
            f"AI処理中にエラーが発生しました: {str(e)}", 
            "error", 
            duration=5
        )
        
        return f"❌ AI会話処理に失敗しました: {e}"