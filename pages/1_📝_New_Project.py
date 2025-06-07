"""
📝 New Project - Charter Generation via Q&A Chat
"""

import streamlit as st

# Set page config first, before any other Streamlit commands
st.set_page_config(
    page_title="Kai VPM v2 - New Project",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded"
)

import yaml
from pathlib import Path
from datetime import datetime
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from libs.ui_layout import (
    get_charter_questions, generate_charter_filename, save_charter_data
)

# Main page content
st.title("📝 New Project Charter")
st.markdown("Create a new project charter through guided questions")

# Initialize chat state for this page
if "charter_chat_messages" not in st.session_state:
    st.session_state.charter_chat_messages = []
if "charter_answers" not in st.session_state:
    st.session_state.charter_answers = {}
if "current_question_index" not in st.session_state:
    st.session_state.current_question_index = 0
if "charter_complete" not in st.session_state:
    st.session_state.charter_complete = False

# Load questions
questions = get_charter_questions()
if not questions:
    st.error("❌ Failed to load charter questions")
    st.stop()

# Show progress
progress = st.session_state.current_question_index / len(questions)
st.progress(progress, text=f"Progress: {st.session_state.current_question_index}/{len(questions)} questions")


def process_answer(question: dict, user_input: str):
    """Process user answer based on question type"""
    question_id = question["id"]
    
    # Handle different answer types
    if question_id in ["outcomes", "scope.in", "scope.out", "constraints.tools", "success_metrics"]:
        # List type - split by lines/commas
        if "\n" in user_input:
            return [item.strip() for item in user_input.split("\n") if item.strip()]
        elif "," in user_input:
            return [item.strip() for item in user_input.split(",") if item.strip()]
        else:
            return [user_input.strip()] if user_input.strip() else []
    
    elif question_id == "stakeholders":
        # Parse stakeholder format (try to extract name and role)
        stakeholders = []
        lines = user_input.split("\n")
        for line in lines:
            line = line.strip()
            if not line:
                continue
            # Try to parse "Name (Role)" or "Name - Role" format
            if "(" in line and ")" in line:
                parts = line.split("(")
                name = parts[0].strip()
                role = parts[1].replace(")", "").strip()
                stakeholders.append({"name": name, "role": role})
            elif " - " in line:
                parts = line.split(" - ", 1)
                stakeholders.append({"name": parts[0].strip(), "role": parts[1].strip()})
            else:
                # Default to just name
                stakeholders.append({"name": line, "role": "未定義"})
        return stakeholders if stakeholders else [{"name": user_input, "role": "未定義"}]
    
    elif question_id == "milestones":
        # Parse milestone format
        milestones = []
        lines = user_input.split("\n")
        for line in lines:
            line = line.strip()
            if not line:
                continue
            # Try to parse "Date: Title" format
            if ":" in line:
                parts = line.split(":", 1)
                date_part = parts[0].strip()
                title_part = parts[1].strip()
                milestones.append({"date": date_part, "title": title_part})
            else:
                # Default format
                milestones.append({"date": "未定", "title": line})
        return milestones if milestones else [{"date": "未定", "title": user_input}]
    
    elif question_id == "risks":
        # Parse risk format
        risks = []
        lines = user_input.split("\n")
        for line in lines:
            line = line.strip()
            if not line:
                continue
            # Try to parse "Risk: Mitigation" format
            if ":" in line:
                parts = line.split(":", 1)
                risk_part = parts[0].strip()
                mitigation_part = parts[1].strip()
                risks.append({"risk": risk_part, "mitigation": mitigation_part})
            else:
                risks.append({"risk": line, "mitigation": "対策要検討"})
        return risks if risks else [{"risk": user_input, "mitigation": "対策要検討"}]
    
    else:
        # Simple string
        return user_input.strip()


def build_charter_data():
    """Build charter data structure from answers"""
    answers = st.session_state.charter_answers
    
    charter_data = {}
    
    # Simple string fields
    for field in ["name", "purpose"]:
        if field in answers:
            charter_data[field] = answers[field]
    
    # List fields
    for field in ["outcomes", "success_metrics"]:
        if field in answers:
            charter_data[field] = answers[field]
    
    # Nested scope
    if "scope.in" in answers or "scope.out" in answers:
        charter_data["scope"] = {}
        if "scope.in" in answers:
            charter_data["scope"]["in"] = answers["scope.in"]
        if "scope.out" in answers:
            charter_data["scope"]["out"] = answers["scope.out"]
    
    # Constraints
    constraints = {}
    for field in ["budget", "deadline"]:
        if f"constraints.{field}" in answers:
            constraints[field] = answers[f"constraints.{field}"]
    if "constraints.tools" in answers:
        constraints["tools"] = answers["constraints.tools"]
    if constraints:
        charter_data["constraints"] = constraints
    
    # Complex object fields
    for field in ["stakeholders", "milestones", "risks"]:
        if field in answers:
            charter_data[field] = answers[field]
    
    return charter_data


def save_charter(charter_data: dict, filename: str):
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
            # Update session state
            st.session_state.selected_charter_file = str(charter_path)
            st.session_state.charter_created = True
            
            st.success(f"✅ Charter saved successfully: {charter_path}")
            st.info("You can now proceed to the next step: ✏️ Preview Charter")
            
            # Auto-navigate to next page after a short delay
            st.balloons()
        else:
            st.error("❌ Failed to save charter")
    
    except Exception as e:
        st.error(f"❌ Error saving charter: {str(e)}")


# Chat interface for charter generation
if not st.session_state.charter_complete:
    # Show Q&A chat interface
    current_index = st.session_state.current_question_index
    
    # Display chat history
    for message in st.session_state.charter_chat_messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])
    
    # Check if we need to ask the next question
    if current_index < len(questions):
        question = questions[current_index]
        
        # Show current question if not already shown
        if not any(msg["content"].startswith(question["prompt"]) 
                  for msg in st.session_state.charter_chat_messages):
            # Add question to chat
            st.session_state.charter_chat_messages.append({
                "role": "assistant",
                "content": f"**{question['prompt']}**\n\n*Question {current_index + 1} of {len(questions)}*"
            })
            st.rerun()
    
    # User input
    if current_index < len(questions):
        question = questions[current_index]
        user_input = st.chat_input(f"回答を入力してください... (Question {current_index + 1}/{len(questions)})")
        
        if user_input:
            # Add user response to chat
            st.session_state.charter_chat_messages.append({
                "role": "user", 
                "content": user_input
            })
            
            # Process answer based on question type
            processed_answer = process_answer(question, user_input)
            st.session_state.charter_answers[question["id"]] = processed_answer
            
            # Move to next question
            st.session_state.current_question_index += 1
            
            # Check if we're done
            if st.session_state.current_question_index >= len(questions):
                st.session_state.charter_complete = True
                # Add completion message
                st.session_state.charter_chat_messages.append({
                    "role": "assistant",
                    "content": "🎉 **Charter完成！** 全ての質問にお答えいただきありがとうございます。\n\n下のボタンから保存できます。"
                })
            
            st.rerun()
    else:
        st.info("All questions completed! Please save your charter below.")

else:
    # Show charter summary and save option
    st.success("🎉 Charter作成完了！")
    
    # Build charter data structure
    charter_data = build_charter_data()
    
    # Show preview
    with st.expander("📋 Charter Preview", expanded=True):
        st.write("**Project Name:**", charter_data.get('name', 'N/A'))
        st.write("**Purpose:**", charter_data.get('purpose', 'N/A'))
        
        if charter_data.get('outcomes'):
            st.write("**Outcomes:**")
            for outcome in charter_data['outcomes']:
                st.write(f"- {outcome}")
        
        if charter_data.get('stakeholders'):
            st.write("**Stakeholders:**")
            for stakeholder in charter_data['stakeholders']:
                name = stakeholder.get('name', 'Unknown')
                role = stakeholder.get('role', 'Unknown') 
                st.write(f"- {name} ({role})")
    
    # Save section
    col1, col2 = st.columns([2, 1])
    
    with col1:
        charter_filename = st.text_input(
            "Charter filename:",
            value=generate_charter_filename(),
            help="Enter filename for the charter (will be saved in data/charters/)"
        )
    
    with col2:
        if st.button("💾 Save Charter", type="primary", use_container_width=True):
            save_charter(charter_data, charter_filename)
    
    # Reset button
    if st.button("🔄 Start Over", help="Clear all answers and start new charter"):
        keys_to_reset = [
            "charter_chat_messages",
            "charter_answers", 
            "current_question_index",
            "charter_complete"
        ]
        
        for key in keys_to_reset:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()