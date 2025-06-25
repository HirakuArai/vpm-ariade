# --- core/chat_processor.py ---
"""
Chat Processing Module - 会話処理モジュール
プロジェクト専用会話機能の共通ロジック
"""

import json
import streamlit as st
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from typing import Optional
import openai
import logging

logger = logging.getLogger(__name__)

_JST = ZoneInfo("Asia/Tokyo")

def _today_log_path() -> Path:
    """Return Path for today's conversation log."""
    CONV_DIR = Path(__file__).resolve().parent.parent / "conversations"
    CONV_DIR.mkdir(parents=True, exist_ok=True)
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

def _append_project_log(project_id: str, role: str, content: str) -> None:
    """Append a single message to today's project-specific JSONL log."""
    today = datetime.now(_JST).strftime("%Y%m%d")
    project_conv_dir = Path(f"data/conversations/{project_id}")
    project_conv_dir.mkdir(parents=True, exist_ok=True)
    log_path = project_conv_dir / f"{today}.jsonl"
    
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

def process_project_chat_input(project_id: str, user_input: str):
    """プロジェクト専用チャット入力の処理"""
    # ナビゲーション状態を更新
    if hasattr(st.session_state, 'navigation_state'):
        st.session_state.navigation_state.selected_project_id = project_id
    st.session_state["current_project_id"] = project_id  # 後方互換性
    
    # 1) ログへ保存
    _append_log("user", user_input)
    _append_project_log(project_id, "user", user_input)
    
    # Handle project creation flow (プロジェクトが既に存在するので基本的にスキップ)
    assistant_reply = None
    
    # Check for task addition command: "タスク <説明> <YYYY-MM-DD>"
    if user_input.startswith("タスク "):
        assistant_reply = _handle_task_command(user_input, project_id)
    
    # Enhanced conversation flow with question generation
    if assistant_reply is None:
        assistant_reply = _process_ai_conversation(user_input, project_id)
    
    # Update conversation history
    if "history" not in st.session_state:
        st.session_state["history"] = []
    
    st.session_state["history"].append({"role": "user", "content": user_input})
    st.session_state["history"].append({"role": "assistant", "content": assistant_reply})
    
    # Also log assistant reply
    _append_log("assistant", assistant_reply)
    _append_project_log(project_id, "assistant", assistant_reply)
    
    # Display messages
    st.chat_message("user").markdown(user_input)
    st.chat_message("assistant").markdown(assistant_reply)
    
    # Auto-push after conversation
    try:
        from core.git_ops import commit_and_push_log, commit_and_push_project_data
        
        # Push global conversation log
        success = commit_and_push_log()
        if success:
            logger.info("Successfully pushed conversation log to git")
        else:
            logger.warning("Failed to push conversation log to git")
        
        # Push project-specific data
        project_success = commit_and_push_project_data(project_id)
        if project_success:
            logger.info(f"Successfully pushed project {project_id} data to git")
        else:
            logger.warning(f"Failed to push project {project_id} data to git")
            
    except Exception as e:
        logger.error(f"Error pushing to git: {e}")
    
    # Rerun to display the new messages
    st.rerun()

def _handle_task_command(user_input: str, project_id: str) -> str:
    """タスク追加コマンドの処理"""
    import re
    from core.project_service import add_task
    
    # Parse task command: タスク <description> <YYYY-MM-DD>
    parts = user_input[3:].strip().split()  # Remove "タスク " prefix
    if len(parts) >= 2:
        # Last part should be date, everything else is description
        due_date = parts[-1]
        description = " ".join(parts[:-1])
        
        # Validate date format
        if re.match(r'\d{4}-\d{2}-\d{2}', due_date):
            try:
                task = add_task(project_id, description, due_date)
                
                # Get current tasks for display
                path = Path(f"data/projects/{project_id}.json")
                data = json.loads(path.read_text())
                tasks = data.get("tasks", [])
                
                task_list = "\n".join([f"- {t['id']}: {t['description']} (期日: {t['due_date']})" for t in tasks])
                return f"タスクを追加しました。\n\n現在のタスク一覧:\n{task_list}"
            except Exception as e:
                return f"タスク追加中にエラーが発生しました: {str(e)}"
        else:
            return "日付は YYYY-MM-DD 形式で入力してください。"
    else:
        return "使用方法: タスク <説明> <YYYY-MM-DD>"

def get_full_system_prompt() -> str:
    """Get full system prompt including project context"""
    try:
        from core.project_prompt import get_project_prompt
        
        # 基本プロンプト（簡略版）
        base_prompt = "You are Kai, a Virtual Project Manager AI assistant. Help users manage their projects effectively."
        
        # 現在日時を明示的に追加
        current_time = datetime.now(_JST)
        date_context = f"\n\n**現在日時**: {current_time.strftime('%Y年%m月%d日 %H:%M')} (JST)\n今日は{current_time.strftime('%Y年%m月%d日')}です。"
        
        current_project_id = st.session_state.get("current_project_id")
        if current_project_id:
            try:
                project_context = get_project_prompt(current_project_id)
                if project_context:
                    return f"{base_prompt}{date_context}\n\n{project_context}"
            except Exception as e:
                logger.error(f"Error getting project context for {current_project_id}: {str(e)}")
        
        return f"{base_prompt}{date_context}"
    except Exception as e:
        logger.error(f"Error generating system prompt: {str(e)}")
        return "You are Kai, a Virtual Project Manager AI assistant."

def _process_ai_conversation(user_input: str, project_id: str) -> str:
    """AI会話処理"""
    try:
        # 1. 基本的なAI応答生成
        system_prompt = get_full_system_prompt()
        messages = [{"role": "system", "content": system_prompt}] + \
                  st.session_state.get("history", []) + \
                  [{"role": "user", "content": user_input}]
        
        # Performance optimization: limit history to last 10 exchanges
        if len(st.session_state.get("history", [])) > 20:  # 20 messages = 10 exchanges
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
        
        # 2. プロジェクトが選択されている場合、質問生成を実行
        if project_id and assistant_reply != "[ERROR]":
            try:
                from core.question_generator import AdaptiveQuestionGenerator, create_conversation_context
                from core.dynamic_schema import get_project_schema
                from core.models import ProjectPhase
                
                # AI依存の会話分析と情報抽出（再分析機能と同じアプローチ）
                from core.simple_conversation_analyzer import analyze_conversation_simple
                from core.dynamic_schema import add_missing_fields_to_project
                
                # 動的スキーマに不足フィールドを追加
                add_missing_fields_to_project(project_id)
                
                # 会話メッセージを準備
                conversation_messages = st.session_state.get("history", []) + [
                    {"role": "user", "content": user_input},
                    {"role": "assistant", "content": assistant_reply}
                ]
                
                # AI依存の情報抽出と更新（最新3往復を分析）
                result, updated_count = analyze_conversation_simple(
                    conversation_messages[-6:],  # 最新3往復
                    project_id
                )
                
                if updated_count > 0:
                    logger.info(f"AI analysis updated {updated_count} project fields from conversation")
                    if result.get("success"):
                        logger.info(f"Update summary: {result.get('summary', 'No summary')}")
                else:
                    logger.debug("AI analysis found no updates needed")
                
                # 質問生成の実行
                if "session_start_time" not in st.session_state:
                    st.session_state["session_start_time"] = datetime.now()
                
                # プロジェクトスキーマと会話文脈を取得
                project_schema = get_project_schema(project_id)
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