#!/usr/bin/env python3
"""スクリーンショット取得スクリプト"""

import asyncio
import subprocess
import time
import signal
import os
from playwright.async_api import async_playwright

async def take_screenshot():
    """Streamlitアプリのスクリーンショットを取得"""
    
    # Streamlitプロセスを起動
    print("🚀 Streamlitを起動中...")
    streamlit_process = subprocess.Popen([
        "streamlit", "run", "app.py", 
        "--server.port", "8501",
        "--server.headless", "true",
        "--server.runOnSave", "false",
        "--browser.gatherUsageStats", "false"
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    # サーバーの起動を待つ
    print("⏳ サーバー起動を待機中...")
    time.sleep(10)
    
    try:
        async with async_playwright() as p:
            print("🌐 ブラウザを起動中...")
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            # 解像度を1440x900に設定
            await page.set_viewport_size({"width": 1440, "height": 900})
            
            print("📱 ページにアクセス中...")
            await page.goto("http://localhost:8501", wait_until="networkidle")
            
            # 少し待ってからスクリーンショット
            await asyncio.sleep(3)
            
            print("📸 スクリーンショット撮影中...")
            await page.screenshot(path="screenshot.png", full_page=True)
            
            print("✅ スクリーンショット保存完了: screenshot.png")
            
            await browser.close()
            
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
    finally:
        # Streamlitプロセスを終了
        print("🛑 Streamlitプロセスを終了中...")
        streamlit_process.terminate()
        try:
            streamlit_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            streamlit_process.kill()
        print("✅ 完了")

if __name__ == "__main__":
    asyncio.run(take_screenshot())