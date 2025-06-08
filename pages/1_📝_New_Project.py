"""
📝 New Project - Conversational Charter Generation with AI
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
from pathlib import Path
from datetime import datetime
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from libs.openai_helper import check_openai_key, ask_gpt, get_system_prompt, extract_charter_json
from libs.ui_layout import generate_charter_filename, save_charter_data


def save_conversation(conversation: list, charter_filename: str):
    """Save conversation log to file"""
    try:
        conversations_dir = Path("data/conversations")
        conversations_dir.mkdir(parents=True, exist_ok=True)
        
        conversation_file = conversations_dir / f"{Path(charter_filename).stem}.json"
        
        with open(conversation_file, 'w', encoding='utf-8') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "charter_file": charter_filename,
                "conversation": conversation
            }, f, ensure_ascii=False, indent=2)
        
        return str(conversation_file)
    except Exception as e:
        st.error(f"会話ログの保存に失敗しました: {str(e)}")
        return None


def save_charter(charter_data: dict, filename: str, conversation: list):
    """Save charter to file and update session state"""
    try:
        # Ensure filename has .yaml extension
        if not filename.endswith('.yaml'):
            filename += '.yaml'
        
        # Create charters directory if needed
        charters_dir = Path("data/charters")
        charters_dir.mkdir(parents=True, exist_ok=True)
        
        # Save charter
        charter_path = charters_dir / filename
        if save_charter_data(str(charter_path), charter_data):
            # Save conversation log
            conversation_file = save_conversation(conversation, filename)
            
            # Update session state
            st.session_state.selected_charter_file = str(charter_path)
            st.session_state.charter_created = True
            
            st.success(f"✅ チャーターが正常に保存されました: {charter_path}")
            if conversation_file:
                st.info(f"📝 会話ログも保存されました: {conversation_file}")
            st.info("次のステップに進むことができます: ✏️ チャーター確認")
            
            # Auto-navigate to next page after a short delay
            st.balloons()
        else:
            st.error("❌ チャーターの保存に失敗しました")
    
    except Exception as e:
        st.error(f"❌ チャーター保存エラー: {str(e)}")


# Main page content
st.title("📝 新規プロジェクト – 会話モード")
st.markdown("AIアシスタント Kai との自然な対話を通じてプロジェクトチャーターを作成します")

# Check OpenAI API key
if not check_openai_key():
    st.error("❌ OPENAI_API_KEY 環境変数が設定されていません")
    st.info("OpenAI API キーを設定してから再度お試しください。")
    st.code("export OPENAI_API_KEY='your-api-key-here'")
    st.stop()

# Initialize conversation state
if "conversation" not in st.session_state:
    st.session_state.conversation = []
if "charter_data" not in st.session_state:
    st.session_state.charter_data = None
if "conversation_complete" not in st.session_state:
    st.session_state.conversation_complete = False

# If conversation is empty, start with system prompt and first question
if not st.session_state.conversation:
    try:
        with st.spinner("🤖 Kai を起動中..."):
            # Get initial response from AI
            messages = [
                {"role": "system", "content": get_system_prompt()},
                {"role": "user", "content": "新しいプロジェクトを始めたいのですが、チャーターを作成するのを手伝ってください。"}
            ]
            
            ai_response = ask_gpt(messages)
            
            # Add to conversation
            st.session_state.conversation = [
                {"role": "user", "content": "新しいプロジェクトを始めたいのですが、チャーターを作成するのを手伝ってください。", "timestamp": datetime.now().isoformat()},
                {"role": "assistant", "content": ai_response, "timestamp": datetime.now().isoformat()}
            ]
            st.rerun()
    
    except Exception as e:
        st.error(f"❌ AI との接続に失敗しました: {str(e)}")
        st.stop()

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
        
        try:
            with st.spinner("🤖 Kai が考えています..."):
                # Prepare messages for OpenAI (exclude timestamps)
                openai_messages = [{"role": "system", "content": get_system_prompt()}]
                for msg in st.session_state.conversation:
                    openai_messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
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
                    st.session_state.charter_data = charter_data
                    st.session_state.conversation_complete = True
                
                st.rerun()
        
        except Exception as e:
            st.error(f"❌ AI応答エラー: {str(e)}")

# Show charter completion and save options
if st.session_state.conversation_complete and st.session_state.charter_data:
    st.markdown("---")
    st.success("🎉 チャーター作成完了！")
    
    charter_data = st.session_state.charter_data
    
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
        
        constraints = charter_data.get('constraints', {})
        if constraints:
            st.write("**制約条件:**")
            if constraints.get('budget'):
                st.write(f"- 予算: {constraints['budget']}")
            if constraints.get('deadline'):
                st.write(f"- 期限: {constraints['deadline']}")
    
    # Save section
    col1, col2 = st.columns([2, 1])
    
    with col1:
        charter_filename = st.text_input(
            "チャーターファイル名:",
            value=generate_charter_filename(),
            help="チャーターのファイル名を入力してください (data/charters/に保存されます)"
        )
    
    with col2:
        if st.button("💾 チャーター保存", type="primary", use_container_width=True):
            save_charter(charter_data, charter_filename, st.session_state.conversation)

# Reset button
st.markdown("---")
col1, col2 = st.columns([1, 1])

with col1:
    if st.button("🔄 会話を最初からやり直し", help="会話をクリアして新しいチャーターを開始"):
        keys_to_reset = [
            "conversation",
            "charter_data",
            "conversation_complete"
        ]
        
        for key in keys_to_reset:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

with col2:
    if st.session_state.conversation and not st.session_state.conversation_complete:
        if st.button("💾 会話を保存", help="現在の会話ログを保存"):
            filename = f"conversation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.yaml"
            conversation_file = save_conversation(st.session_state.conversation, filename)
            if conversation_file:
                st.success(f"会話ログを保存しました: {conversation_file}")

# Progress indicator
if st.session_state.conversation and not st.session_state.conversation_complete:
    # Estimate progress based on conversation length and typical charter requirements
    conversation_length = len([msg for msg in st.session_state.conversation if msg["role"] == "user"])
    estimated_progress = min(conversation_length / 8, 0.9)  # Assume ~8 exchanges needed
    
    st.progress(estimated_progress, text=f"進捗推定: {int(estimated_progress * 100)}% (対話回数: {conversation_length})")