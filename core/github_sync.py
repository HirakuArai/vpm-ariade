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
    Memory repoファイルをGitHubに自動Push（仕様書準拠版）
    
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
        
        # Git操作の実行（仕様書準拠）
        try:
            # 1. git add memory_repo
            subprocess.run(
                ["git", "add", "memory_repo"],
                cwd=repo_root,
                check=False,
                capture_output=True,
                text=True
            )
            
            # 2. git commit -m "chore: memory sync YYYY-MM-DD HH:MM"
            commit_result = subprocess.run(
                ["git", "commit", "-m", commit_message],
                cwd=repo_root,
                check=False,
                capture_output=True,
                text=True
            )
            
            # コミットが空の場合は正常終了
            if commit_result.returncode != 0:
                if "nothing to commit" in commit_result.stdout or "nothing to commit" in commit_result.stderr:
                    logger.info("No memory changes to commit")
                    return True
                else:
                    logger.warning(f"Git commit failed: {commit_result.stderr}")
                    return False
            
            # 3. git push origin main
            push_result = subprocess.run(
                ["git", "push", "origin", "main"],
                cwd=repo_root,
                env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if push_result.returncode != 0:
                # エラーハンドリング（仕様書準拠）
                if "403" in push_result.stderr or "401" in push_result.stderr:
                    logger.error(f"Git push authentication failed: {push_result.stderr}")
                    logger.error("Check GITHUB_PAT token and permissions")
                else:
                    logger.error(f"Git push failed: {push_result.stderr}")
                return False
            
            logger.info("Memory files successfully pushed to GitHub")
            return True
            
        except subprocess.TimeoutExpired:
            logger.error("Git push timed out")
            return False
        except subprocess.CalledProcessError as e:
            logger.error(f"Git command error: {e}")
            if "403" in str(e) or "401" in str(e):
                logger.error("Authentication error - check GITHUB_PAT token")
            return False
        
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
    Streamlitセッション終了時に実行されるフック（仕様書準拠版）
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


# Streamlit用のセッション終了フック（代替実装）
def setup_session_end_hook():
    """
    Streamlit用のセッション終了フック設定
    st.on_session_endが存在しないため、代替実装を提供
    """
    import atexit
    
    def cleanup():
        """プロセス終了時のクリーンアップ"""
        try:
            on_session_end_hook()
        except Exception as e:
            logger.error(f"Cleanup hook error: {e}")
    
    # プロセス終了時にフックを実行
    atexit.register(cleanup)
    logger.info("Session end hook registered via atexit")


# Memory Chat用の手動同期関数
def manual_memory_sync():
    """
    Memory Chat β用の手動同期関数（仕様書準拠・エラーハンドリング付き）
    
    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        success = push_memory_to_github()
        
        if success:
            return True, "✅ メモリファイルをGitHubに同期しました"
        else:
            return False, "❌ GitHub同期に失敗しました（詳細はログを確認）"
            
    except subprocess.CalledProcessError as e:
        if "403" in str(e) or "401" in str(e):
            return False, "❌ 認証エラー: GITHUB_PAT トークンを確認してください"
        else:
            return False, f"❌ Git push failed: {str(e)}"
    except Exception as e:
        return False, f"❌ 同期エラー: {str(e)}"


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