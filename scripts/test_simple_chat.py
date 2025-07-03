#!/usr/bin/env python3
"""
Simple test to verify chat processing works
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_chat_processing():
    """Test the chat processing function directly"""
    print("🧪 Testing chat processing directly...")
    
    try:
        # Import required modules
        import streamlit as st
        from unittest.mock import MagicMock
        
        # Mock streamlit session state
        if not hasattr(st, 'session_state'):
            st.session_state = MagicMock()
            
        # Initialize session state
        st.session_state.history = []
        st.session_state.navigation_state = MagicMock()
        st.session_state.navigation_state.current_page = MagicMock()
        st.session_state.navigation_state.current_page.value = "home"
        st.session_state.navigation_state.selected_project_id = None
        
        # Set up API key
        os.environ['OPENAI_API_KEY'] = 'test-key'
        
        print("✅ Mocked Streamlit environment")
        
        # Import the chat handler
        from core.chat_handler_ai import process_chat_input_ai
        
        print("✅ Imported chat handler")
        
        # Test with a simple message
        try:
            process_chat_input_ai("こんにちは", None)
            print("✅ Chat processing completed without errors")
        except Exception as e:
            print(f"❌ Chat processing failed: {e}")
            import traceback
            traceback.print_exc()
            
        # Check session state
        print(f"📊 Session history length: {len(st.session_state.history)}")
        for i, msg in enumerate(st.session_state.history):
            print(f"  Message {i+1}: {msg.get('role', 'unknown')} - {msg.get('content', '')[:50]}...")
            
    except Exception as e:
        print(f"❌ Test setup failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_chat_processing()