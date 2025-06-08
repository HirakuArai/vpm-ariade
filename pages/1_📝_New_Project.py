"""
📝 New Project - RAG-Enhanced Conversational Charter Generation with Draft Lifecycle
"""

import streamlit as st

# Set page config first, before any other Streamlit commands
st.set_page_config(
    page_title="Kai VPM v2 - 新規プロジェクト",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded"
)

import json
import os
import uuid
import asyncio
from pathlib import Path
from datetime import datetime
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from libs.openai_helper import (
    check_openai_key, ask_gpt, get_system_prompt_with_background, 
    extract_charter_json, generate_next_question
)
from libs.knowledge_rag import get_domain_info
from libs.ui_layout import generate_charter_filename, save_charter_data


def save_draft(draft_id: str, charter_data: dict, conversation: list, domain_info: str = None):
    """Save draft charter and conversation"""
    try:
        drafts_dir = Path("data/drafts")
        drafts_dir.mkdir(parents=True, exist_ok=True)
        
        draft_data = {
            "draft_id": draft_id,
            "timestamp": datetime.now().isoformat(),
            "charter": charter_data,
            "conversation": conversation,
            "domain_info": domain_info
        }
        
        draft_file = drafts_dir / f"draft_{draft_id}.json"
        with open(draft_file, 'w', encoding='utf-8') as f:
            json.dump(draft_data, f, ensure_ascii=False, indent=2)
        
        return str(draft_file)
    except Exception as e:
        st.error(f"ドラフト保存エラー: {str(e)}")
        return None


def load_draft(draft_id: str) -> dict:
    """Load draft data"""
    try:
        draft_file = Path("data/drafts") / f"draft_{draft_id}.json"
        if draft_file.exists():
            with open(draft_file, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def delete_draft(draft_id: str):
    """Delete draft files"""
    try:
        draft_file = Path("data/drafts") / f"draft_{draft_id}.json"
        if draft_file.exists():
            draft_file.unlink()
    except Exception:
        pass


def finalize_charter(draft_data: dict, filename: str):
    """Move draft to formal charter and conversation logs"""
    try:
        charter_data = draft_data.get("charter", {})
        conversation = draft_data.get("conversation", [])
        domain_info = draft_data.get("domain_info")
        
        # Add background info to charter if available
        if domain_info:
            charter_data["background"] = domain_info
        
        # Ensure filename has .yaml extension
        if not filename.endswith('.yaml'):
            filename += '.yaml'
        
        # Create directories
        charters_dir = Path("data/charters")
        conversations_dir = Path("data/conversations")
        charters_dir.mkdir(parents=True, exist_ok=True)
        conversations_dir.mkdir(parents=True, exist_ok=True)
        
        # Save charter
        charter_path = charters_dir / filename
        if save_charter_data(str(charter_path), charter_data):
            # Save conversation log
            conversation_file = conversations_dir / f"{Path(filename).stem}.json"
            with open(conversation_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "timestamp": datetime.now().isoformat(),
                    "charter_file": str(charter_path),
                    "conversation": conversation,
                    "domain_info": domain_info
                }, f, ensure_ascii=False, indent=2)
            
            # Update session state
            st.session_state.selected_charter_file = str(charter_path)
            st.session_state.charter_created = True
            
            # Delete draft
            draft_id = draft_data.get("draft_id")
            if draft_id:
                delete_draft(draft_id)
            
            return True
    except Exception as e:
        st.error(f"チャーター確定エラー: {str(e)}")
    
    return False


def parse_user_answer(user_input: str, context: str) -> dict:
    """Parse user answer and update charter data incrementally"""
    # This is a simplified parser - in practice, you might want more sophisticated NLP
    # For now, we'll let the AI handle the parsing through the conversation
    return {"raw_answer": user_input, "context": context}


# Main page content
st.title("📝 新規プロジェクト – RAG強化会話モード")
st.markdown("AIアシスタント Kai との自然な対話を通じて、背景情報を活用したプロジェクトチャーターを作成します")

# Check OpenAI API key
if not check_openai_key():
    st.error("❌ OPENAI_API_KEY 環境変数が設定されていません")
    st.info("OpenAI API キーを設定してから再度お試しください。")
    st.code("export OPENAI_API_KEY='your-api-key-here'")
    st.stop()

# Initialize session state
if "draft_id" not in st.session_state:
    st.session_state.draft_id = None
if "conversation" not in st.session_state:
    st.session_state.conversation = []
if "draft_charter" not in st.session_state:
    st.session_state.draft_charter = {}
if "domain_info" not in st.session_state:
    st.session_state.domain_info = None
if "conversation_complete" not in st.session_state:
    st.session_state.conversation_complete = False
if "turn_count" not in st.session_state:
    st.session_state.turn_count = 0

# Start conversation if empty
if not st.session_state.conversation:
    # Generate new draft ID
    st.session_state.draft_id = str(uuid.uuid4())
    st.session_state.turn_count = 0
    
    # Add initial greeting
    st.session_state.conversation = [{
        "role": "assistant",
        "content": "こんにちは！新しいプロジェクトのチャーター作成をお手伝いします。まず、どのようなプロジェクトを始めたいか、簡単に教えてください。",
        "timestamp": datetime.now().isoformat()
    }]

# Display conversation
st.markdown("### 💬 Kai との対話")

for message in st.session_state.conversation:
    role = message["role"]
    content = message["content"]
    
    if role == "user":
        with st.chat_message("user"):
            st.write(content)
    elif role == "assistant":
        with st.chat_message("assistant"):
            st.write(content)

# Show draft status
if st.session_state.draft_id:
    with st.sidebar:
        st.write("**ドラフト状態**")
        st.write(f"ID: {st.session_state.draft_id[:8]}...")
        st.write(f"ターン数: {st.session_state.turn_count}")
        if st.session_state.domain_info:
            with st.expander("🔍 背景情報"):
                st.write(st.session_state.domain_info[:200] + "..." if len(st.session_state.domain_info) > 200 else st.session_state.domain_info)

# Chat input (only if conversation not complete)
if not st.session_state.conversation_complete:
    user_input = st.chat_input("回答を入力してください...")
    
    if user_input:
        # Add user message to conversation
        st.session_state.conversation.append({
            "role": "user",
            "content": user_input,
            "timestamp": datetime.now().isoformat()
        })
        
        st.session_state.turn_count += 1
        
        try:
            with st.spinner("🤖 Kai が考えています..."):
                # First turn: Get domain info via RAG
                if st.session_state.turn_count == 1:
                    domain_info = get_domain_info(user_input)
                    st.session_state.domain_info = domain_info
                
                # Two-layer approach:
                # Pass #1: Generate next question (invisible)
                next_question = None
                try:
                    # Use asyncio to handle the async function
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    next_question = loop.run_until_complete(
                        generate_next_question(st.session_state.conversation, st.session_state.draft_charter)
                    )
                    loop.close()
                except Exception:
                    # Fallback if async fails
                    next_question = "次の質問をお聞かせください。"
                
                # Pass #2: Get AI response with background
                system_prompt = get_system_prompt_with_background(st.session_state.domain_info)
                
                # Prepare messages for OpenAI (exclude timestamps)
                openai_messages = [{"role": "system", "content": system_prompt}]
                for msg in st.session_state.conversation:
                    openai_messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })
                
                # Add the generated question as context (not visible to user)
                if next_question and next_question != "すべての情報が揃いました。":
                    openai_messages.append({
                        "role": "system",
                        "content": f"Focus on this aspect: {next_question}"
                    })
                
                # Get AI response
                ai_response = ask_gpt(openai_messages)
                
                # Add AI response to conversation
                st.session_state.conversation.append({
                    "role": "assistant",
                    "content": ai_response,
                    "timestamp": datetime.now().isoformat()
                })
                
                # Check if charter is complete
                charter_data = extract_charter_json(ai_response)
                if charter_data:
                    st.session_state.draft_charter = charter_data
                    st.session_state.conversation_complete = True
                else:
                    # Update draft charter incrementally (simplified)
                    # In a real implementation, you'd parse the user input more carefully
                    pass
                
                # Save draft after each turn
                save_draft(
                    st.session_state.draft_id,
                    st.session_state.draft_charter,
                    st.session_state.conversation,
                    st.session_state.domain_info
                )
                
                st.rerun()
        
        except Exception as e:
            st.error(f"❌ AI応答エラー: {str(e)}")

# Show charter completion and save options
if st.session_state.conversation_complete and st.session_state.draft_charter:
    st.markdown("---")
    st.success("🎉 チャーター作成完了！")
    
    charter_data = st.session_state.draft_charter
    
    # Show preview
    with st.expander("📋 チャータープレビュー", expanded=True):
        st.write("**プロジェクト名:**", charter_data.get('name', 'N/A'))
        st.write("**目的:**", charter_data.get('purpose', 'N/A'))
        
        outcomes = charter_data.get('outcomes', [])
        if outcomes:
            st.write("**成果物:**")
            for outcome in outcomes:
                st.write(f"- {outcome}")
        
        stakeholders = charter_data.get('stakeholders', [])
        if stakeholders:
            st.write("**ステークホルダー:**")
            for stakeholder in stakeholders:
                if isinstance(stakeholder, dict):
                    name = stakeholder.get('name', 'Unknown')
                    role = stakeholder.get('role', 'Unknown')
                    st.write(f"- {name} ({role})")
                else:
                    st.write(f"- {stakeholder}")
    
    # Save section
    col1, col2 = st.columns([2, 1])
    
    with col1:
        charter_filename = st.text_input(
            "チャーターファイル名:",
            value=generate_charter_filename(),
            help="チャーターのファイル名を入力してください (data/charters/に保存されます)"
        )
    
    with col2:
        if st.button("💾 保存して次へ", type="primary", use_container_width=True):
            draft_data = load_draft(st.session_state.draft_id)
            if finalize_charter(draft_data, charter_filename):
                st.success(f"✅ チャーターが正常に保存されました！")
                st.info("次のステップに進むことができます: ✏️ チャーター確認")
                st.balloons()

# Action buttons
st.markdown("---")
col1, col2 = st.columns([1, 1])

with col1:
    if st.button("🗑️ 破棄", help="現在のドラフトを削除して最初からやり直し"):
        if st.session_state.draft_id:
            delete_draft(st.session_state.draft_id)
        
        # Reset session state
        keys_to_reset = [
            "draft_id", "conversation", "draft_charter", 
            "domain_info", "conversation_complete", "turn_count"
        ]
        
        for key in keys_to_reset:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

with col2:
    if st.session_state.conversation and not st.session_state.conversation_complete:
        if st.button("💾 ドラフト保存", help="現在の状態を保存"):
            draft_file = save_draft(
                st.session_state.draft_id,
                st.session_state.draft_charter,
                st.session_state.conversation,
                st.session_state.domain_info
            )
            if draft_file:
                st.success(f"ドラフトを保存しました")

# Progress indicator
if st.session_state.conversation and not st.session_state.conversation_complete:
    # Estimate progress based on conversation length
    estimated_progress = min(st.session_state.turn_count / 10, 0.9)  # Assume ~10 exchanges needed
    st.progress(estimated_progress, text=f"進捗推定: {int(estimated_progress * 100)}% (ターン: {st.session_state.turn_count})")

# Show background info if available
if st.session_state.domain_info:
    with st.expander("🔍 プロジェクト背景情報", expanded=False):
        st.markdown(st.session_state.domain_info)