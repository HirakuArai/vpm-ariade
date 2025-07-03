#!/usr/bin/env python3
"""
Test script to isolate project details rendering issue
"""

import sys
import subprocess
import time
from pathlib import Path

def test_project_details():
    """Test project details page rendering"""
    print("🧪 Testing project details page...")
    
    try:
        from playwright.sync_api import sync_playwright
        
        # Start Streamlit
        process = subprocess.Popen([
            sys.executable, '-m', 'streamlit', 'run', 'app.py',
            '--server.port', '8502'
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        print("Starting Streamlit...")
        time.sleep(5)
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            page = browser.new_page()
            
            # Navigate to app
            page.goto("http://localhost:8502", timeout=30000)
            print("✅ Navigated to app")
            
            # Wait for load
            page.wait_for_timeout(3000)
            
            # Try to click on a project to view details
            # Look for project navigation in sidebar
            print("Looking for project navigation...")
            
            # Try to find project items in the sidebar
            project_elements = page.query_selector_all('div:has-text("八ヶ岳")')
            if project_elements:
                print("✅ Found project elements")
                # Click on the first project
                project_elements[0].click()
                print("✅ Clicked on project")
                
                # Wait for navigation
                time.sleep(2)
                
                # Look for project details content
                details_content = page.query_selector_all('h1, h2, h3')
                print(f"📊 Found {len(details_content)} heading elements")
                
                # Check if we can see the project details page content
                page_content = page.text_content('body')
                if '八ヶ岳登山計画' in page_content:
                    print("✅ Project details content found")
                else:
                    print("❌ No project details content visible")
                
                # Take a screenshot for debugging
                page.screenshot(path="project_details_test.png")
                print("📸 Screenshot saved as project_details_test.png")
                
            else:
                print("❌ No project elements found")
            
            # Keep browser open for manual inspection
            print("🔍 Browser staying open for 20 seconds...")
            time.sleep(20)
            
            browser.close()
            
    except ImportError:
        print("❌ Playwright not available")
    except Exception as e:
        print(f"❌ Test failed: {e}")
    finally:
        if process:
            process.terminate()
        subprocess.run(['pkill', '-f', 'streamlit'], capture_output=True)
        print("🧹 Cleaned up")

if __name__ == "__main__":
    test_project_details()