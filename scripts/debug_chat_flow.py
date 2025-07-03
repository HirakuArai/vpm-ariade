#!/usr/bin/env python3
"""
Debug script to test chat flow locally
"""

import sys
import time
import subprocess
from pathlib import Path

def test_local_chat():
    """Test local chat functionality"""
    print("🧪 Testing local chat flow...")
    
    # Start Streamlit
    process = None
    try:
        process = subprocess.Popen([
            sys.executable, '-m', 'streamlit', 'run', 'app.py',
            '--server.port', '8504'
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        print("Starting Streamlit on port 8504...")
        time.sleep(5)
        
        # Test with playwright
        try:
            from playwright.sync_api import sync_playwright
            
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=False)  # Show browser for debugging
                page = browser.new_page()
                
                # Navigate to app
                page.goto("http://localhost:8504", timeout=30000)
                print("✅ Navigated to Streamlit app")
                
                # Wait for page load
                page.wait_for_timeout(3000)
                
                # Find chat input
                chat_input = page.query_selector('textarea[placeholder*="メッセージ"]')
                if not chat_input:
                    print("❌ Chat input not found")
                    return False
                
                print("✅ Found chat input")
                
                # Type test message
                chat_input.fill("こんにちは")
                chat_input.press("Enter")
                print("✅ Sent test message")
                
                # Wait for response
                time.sleep(5)
                
                # Check for chat messages
                chat_messages = page.query_selector_all('[data-testid="chat-message"]')
                if not chat_messages:
                    # Try alternative selectors
                    chat_messages = page.query_selector_all('div:has-text("user"), div:has-text("assistant")')
                
                print(f"📊 Found {len(chat_messages)} chat messages")
                
                # Check session history in debug section
                debug_expander = page.query_selector('details:has-text("デバッグ情報")')
                if debug_expander:
                    debug_expander.click()
                    time.sleep(1)
                    print("✅ Opened debug info")
                    
                    # Check history length
                    history_text = page.text_content('body')
                    if "履歴の長さ:" in history_text:
                        print("✅ Found history debug info")
                    else:
                        print("❌ No history debug info found")
                
                # Keep browser open for manual inspection
                print("🔍 Browser will stay open for 30 seconds for manual inspection...")
                time.sleep(30)
                
                browser.close()
                return True
                
        except ImportError:
            print("❌ Playwright not available")
            return False
        except Exception as e:
            print(f"❌ Browser test failed: {e}")
            return False
            
    except Exception as e:
        print(f"❌ Failed to start Streamlit: {e}")
        return False
        
    finally:
        if process:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
        subprocess.run(['pkill', '-f', 'streamlit'], capture_output=True)
        print("🧹 Cleaned up processes")

if __name__ == "__main__":
    success = test_local_chat()
    print(f"{'✅ Test completed' if success else '❌ Test failed'}")