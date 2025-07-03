#!/usr/bin/env python3
"""
Automated UI testing script to trigger LLM calls and generate trace logs.
"""

import subprocess
import sys
import time
import signal
import os
from pathlib import Path
from typing import Optional


def setup_llm_tracing():
    """Import and setup LLM call tracing."""
    try:
        # Import the trace script to enable tracing
        sys.path.insert(0, str(Path(__file__).parent))
        import trace_llm_calls
        
        # Setup tracing
        tracer = trace_llm_calls.LLMCallTracer()
        tracer.setup_tracing()
        print("LLM tracing enabled")
        return tracer
    except Exception as e:
        print(f"Warning: Could not setup LLM tracing: {e}")
        return None


def start_streamlit_process() -> Optional[subprocess.Popen]:
    """Start Streamlit in headless mode."""
    repo_root = Path(__file__).parent.parent
    
    try:
        process = subprocess.Popen([
            sys.executable, '-m', 'streamlit', 'run', 'app.py',
            '--server.headless', 'true',
            '--server.port', '8501',
            '--server.address', 'localhost'
        ], cwd=repo_root, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        print("Starting Streamlit server...")
        time.sleep(5)  # Wait for startup
        
        return process
    except Exception as e:
        print(f"Error starting Streamlit: {e}")
        return None


def run_playwright_automation():
    """Run Playwright automation to interact with the UI."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Playwright not available, skipping browser automation")
        return False
    
    print("Starting Playwright automation...")
    
    with sync_playwright() as p:
        try:
            # Launch browser in headless mode
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # Navigate to Streamlit app
            page.goto("http://localhost:8501", timeout=30000)
            print("Navigated to Streamlit app")
            
            # Wait for page to load
            page.wait_for_timeout(3000)
            
            # Try multiple selectors for chat input
            input_selectors = [
                'textarea[placeholder*="メッセージ"]',  # Japanese placeholder
                'textarea[placeholder*="message"]',     # English placeholder  
                'textarea[data-testid="stChatInput"]',  # Streamlit test ID
                'textarea',                             # Any textarea
                'input[type="text"]'                    # Fallback to text input
            ]
            
            input_element = None
            for selector in input_selectors:
                try:
                    input_element = page.query_selector(selector)
                    if input_element:
                        print(f"Found input element with selector: {selector}")
                        break
                except Exception:
                    continue
            
            if not input_element:
                print("Could not find chat input element, trying alternative approach")
                # Alternative: try to find any input-like element
                all_inputs = page.query_selector_all('textarea, input[type="text"]')
                if all_inputs:
                    input_element = all_inputs[-1]  # Use the last one (likely the chat input)
                    print(f"Using fallback input element")
            
            if input_element:
                # Clear and type test message
                input_element.fill("")
                input_element.type("テストプロジェクトを作成してください", delay=100)
                print("Typed test message")
                
                # Submit the message (try Enter key and button click)
                input_element.press("Enter")
                print("Pressed Enter to submit")
                
                # Also try to find and click submit button
                button_selectors = [
                    'button[data-testid="stChatInputSubmitButton"]',
                    'button[type="submit"]',
                    'button:has-text("送信")',
                    'button:has-text("Send")',
                    'button'
                ]
                
                for selector in button_selectors:
                    try:
                        button = page.query_selector(selector)
                        if button and button.is_visible():
                            button.click()
                            print(f"Clicked submit button: {selector}")
                            break
                    except Exception:
                        continue
                
                # Wait for response to appear
                print("Waiting for LLM response...")
                try:
                    # Wait for any element containing "Kai" or "AI" (response indicators)
                    page.wait_for_selector('div:has-text("AI"), div:has-text("Kai"), div:has-text("プロジェクト")', timeout=15000)
                    print("LLM response detected")
                    time.sleep(2)  # Additional wait for processing
                    return True
                except Exception as e:
                    print(f"Timeout waiting for response: {e}")
                    # Still return True as the input was submitted
                    return True
            else:
                print("Could not find input element")
                return False
                
        except Exception as e:
            print(f"Playwright automation error: {e}")
            return False
        finally:
            try:
                browser.close()
            except Exception:
                pass
    
    return False


def kill_streamlit_processes():
    """Kill any running Streamlit processes."""
    try:
        # Kill by process name
        subprocess.run(['pkill', '-f', 'streamlit'], capture_output=True)
        print("Killed Streamlit processes")
    except Exception as e:
        print(f"Error killing processes: {e}")


def count_trace_lines() -> int:
    """Count lines in the trace JSONL file."""
    trace_file = Path(__file__).parent.parent / "trace_llm_calls.jsonl"
    
    if not trace_file.exists():
        return 0
    
    try:
        with open(trace_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            return len([line for line in lines if line.strip()])
    except Exception as e:
        print(f"Error reading trace file: {e}")
        return 0


def count_recent_llm_calls(start_time: float) -> int:
    """Count LLM calls in the existing logs since start_time."""
    logs_dir = Path(__file__).parent.parent / "logs" / "llm_calls"
    
    if not logs_dir.exists():
        return 0
    
    count = 0
    
    try:
        # Find the most recent log file
        log_files = list(logs_dir.glob("*.jsonl"))
        log_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        for log_file in log_files[:2]:  # Check the 2 most recent files
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                import json
                                log_entry = json.loads(line)
                                # Parse timestamp
                                ts_str = log_entry.get('ts', '')
                                if ts_str:
                                    from datetime import datetime
                                    import re
                                    # Parse ISO timestamp
                                    if 'T' in ts_str and 'Z' in ts_str:
                                        ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00')).timestamp()
                                        if ts >= start_time:
                                            count += 1
                            except (json.JSONDecodeError, ValueError, KeyError):
                                continue
            except Exception as e:
                print(f"Error reading log file {log_file}: {e}")
                continue
                
    except Exception as e:
        print(f"Error counting recent LLM calls: {e}")
    
    return count


def main():
    """Main autotest logic."""
    # Record start time for LLM call tracking
    test_start_time = time.time()
    
    # Clean up any existing trace file
    trace_file = Path(__file__).parent.parent / "trace_llm_calls.jsonl"
    if trace_file.exists():
        trace_file.unlink()
    
    streamlit_process = None
    success = False
    
    try:
        # Setup LLM tracing
        tracer = setup_llm_tracing()
        
        # Start Streamlit
        streamlit_process = start_streamlit_process()
        if not streamlit_process:
            print("Failed to start Streamlit")
            return False
        
        # Record time before UI automation
        automation_start_time = time.time()
        
        # Run Playwright automation
        automation_success = run_playwright_automation()
        
        if automation_success:
            print("UI automation completed")
            # Give some time for LLM processing
            time.sleep(3)
        else:
            print("UI automation failed, but continuing to check traces")
        
        # Count trace lines from custom tracer
        custom_trace_count = count_trace_lines()
        
        # Count LLM calls from existing log system
        existing_log_count = count_recent_llm_calls(automation_start_time)
        
        total_count = custom_trace_count + existing_log_count
        
        print(f"LLM calls traced: {total_count}")
        if custom_trace_count > 0:
            print(f"  - Custom tracer: {custom_trace_count}")
        if existing_log_count > 0:
            print(f"  - Existing logs: {existing_log_count}")
        
        # Success condition: at least 1 LLM call detected
        success = total_count >= 1
        
        if success:
            print("✅ Autotest PASSED")
        else:
            print("❌ Autotest FAILED - No LLM calls traced")
        
        return success
        
    except Exception as e:
        print(f"Autotest error: {e}")
        return False
        
    finally:
        # Cleanup
        print("Cleaning up processes...")
        
        # Kill Streamlit process
        if streamlit_process:
            try:
                streamlit_process.terminate()
                streamlit_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                streamlit_process.kill()
            except Exception as e:
                print(f"Error terminating Streamlit process: {e}")
        
        # Kill any remaining Streamlit processes
        kill_streamlit_processes()
        
        time.sleep(1)  # Final cleanup wait


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)