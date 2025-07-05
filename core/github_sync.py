"""
GitHub Sync Module for Memory Layer Phase 2
メモリファイルの自動GitHub同期機能
"""

import subprocess
import os
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


def push_memory_to_github(commit_message: Optional[str] = None) -> bool:
    """
    Memory repoファイルをGitHubに自動Push
    
    Args:
        commit_message: カスタムコミットメッセージ
        
    Returns:
        bool: Push成功フラグ
    """
    try:
        repo_root = Path(__file__).resolve().parent.parent
        
        # デフォルトコミットメッセージ
        if not commit_message:
            ts = datetime.now().strftime("%Y-%m-%d %H:%M")
            commit_message = f"chore: memory sync {ts}"
        
        # Git操作の実行
        commands = [
            ["git", "add", "memory_repo/"],
            ["git", "commit", "-m", commit_message],
            ["git", "push", "origin", "main"]
        ]
        
        for cmd in commands:
            try:
                result = subprocess.run(
                    cmd,
                    cwd=repo_root,
                    capture_output=True,
                    text=True,
                    env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
                    timeout=30  # 30秒でタイムアウト
                )
                
                if result.returncode != 0:
                    # Commitが空の場合は正常（何も変更がない）
                    if "nothing to commit" in result.stdout or "nothing to commit" in result.stderr:
                        logger.info("No memory changes to commit")
                        return True
                    
                    # その他のエラー
                    logger.warning(f"Git command failed: {' '.join(cmd)}")
                    logger.warning(f"stdout: {result.stdout}")
                    logger.warning(f"stderr: {result.stderr}")
                    return False
                    
            except subprocess.TimeoutExpired:
                logger.error(f"Git command timed out: {' '.join(cmd)}")
                return False
            except subprocess.CalledProcessError as e:
                logger.error(f"Git command error: {e}")
                return False
        
        logger.info("Memory files successfully pushed to GitHub")
        return True
        
    except Exception as e:
        logger.error(f"Unexpected error during GitHub sync: {e}")
        return False


def check_git_auth() -> bool:
    """
    Git認証の確認
    
    Returns:
        bool: 認証成功フラグ
    """
    try:
        repo_root = Path(__file__).resolve().parent.parent
        
        # git status で基本的な接続確認
        result = subprocess.run(
            ["git", "status"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        return result.returncode == 0
        
    except Exception as e:
        logger.error(f"Git auth check failed: {e}")
        return False


def setup_git_credentials():
    """
    Git認証の設定
    GitHub Personal Access Token を使用
    """
    try:
        github_token = os.getenv("GITHUB_PAT") or os.getenv("GITHUB_TOKEN")
        
        if not github_token:
            logger.warning("GITHUB_PAT environment variable not set")
            return False
        
        repo_root = Path(__file__).resolve().parent.parent
        
        # Git credentialの設定
        commands = [
            ["git", "config", "--local", "credential.helper", "store"],
            ["git", "config", "--local", "user.email", "noreply@anthropic.com"],
            ["git", "config", "--local", "user.name", "Memory Layer Bot"]
        ]
        
        for cmd in commands:
            subprocess.run(cmd, cwd=repo_root, capture_output=True)
        
        logger.info("Git credentials configured")
        return True
        
    except Exception as e:
        logger.error(f"Git credential setup failed: {e}")
        return False


# セッション終了時のフック関数
def on_session_end_hook():
    """
    Streamlitセッション終了時に実行されるフック
    """
    try:
        logger.info("Session ending - attempting memory sync to GitHub")
        
        # Git認証確認
        if not check_git_auth():
            logger.warning("Git auth check failed - skipping sync")
            return
        
        # メモリファイルをPush
        success = push_memory_to_github("chore: memory sync on session end")
        
        if success:
            logger.info("Session end memory sync completed successfully")
        else:
            logger.warning("Session end memory sync failed")
            
    except Exception as e:
        logger.error(f"Session end hook error: {e}")


# Streamlit用のヘルパー関数
def sync_memory_with_feedback():
    """
    Streamlit UI用のメモリ同期関数（フィードバック付き）
    
    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        # Git認証確認
        if not check_git_auth():
            return False, "Git認証エラー: リポジトリにアクセスできません"
        
        # 同期実行
        success = push_memory_to_github()
        
        if success:
            return True, "✅ メモリファイルをGitHubに同期しました"
        else:
            return False, "❌ GitHub同期に失敗しました（詳細はログを確認）"
            
    except Exception as e:
        return False, f"❌ 同期エラー: {str(e)}"


if __name__ == "__main__":
    # テスト実行
    print("Testing GitHub sync functionality...")
    
    auth_ok = check_git_auth()
    print(f"Git auth check: {'OK' if auth_ok else 'FAILED'}")
    
    if auth_ok:
        success = push_memory_to_github("test: GitHub sync module test")
        print(f"Memory sync test: {'SUCCESS' if success else 'FAILED'}")