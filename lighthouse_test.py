#!/usr/bin/env python3
"""Lighthouse Accessibility スコア測定"""

import asyncio
import subprocess
import time
import json
from playwright.async_api import async_playwright

async def run_lighthouse_test():
    """Lighthouse Accessibility テストを実行"""
    
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
        # Lighthouse実行
        print("🔍 Lighthouse Accessibilityテスト実行中...")
        result = subprocess.run([
            "npx", "lighthouse", "http://localhost:8501",
            "--only-categories=accessibility",
            "--output=json",
            "--output-path=lighthouse-report.json",
            "--chrome-flags=--headless"
        ], capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            # レポート読み込み
            with open('lighthouse-report.json', 'r') as f:
                report = json.load(f)
            
            accessibility_score = report['categories']['accessibility']['score'] * 100
            print(f"✅ Lighthouse Accessibility スコア: {accessibility_score:.1f}/100")
            
            if accessibility_score >= 90:
                print("🎉 要求基準（90点以上）をクリアしました！")
                return True, accessibility_score
            else:
                print(f"⚠️ 要求基準（90点以上）に達していません。現在のスコア: {accessibility_score:.1f}")
                return False, accessibility_score
        else:
            print(f"❌ Lighthouseの実行に失敗しました: {result.stderr}")
            return False, 0
            
    except subprocess.TimeoutExpired:
        print("❌ Lighthouseがタイムアウトしました")
        return False, 0
    except FileNotFoundError:
        print("❌ Lighthouseがインストールされていません。npm install -g lighthouse でインストールしてください")
        return False, 0
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        return False, 0
    finally:
        # Streamlitプロセスを終了
        print("🛑 Streamlitプロセスを終了中...")
        streamlit_process.terminate()
        try:
            streamlit_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            streamlit_process.kill()

if __name__ == "__main__":
    success, score = asyncio.run(run_lighthouse_test())
    exit(0 if success else 1)