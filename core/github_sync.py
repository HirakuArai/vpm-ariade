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


def push_memory_to_github(commit_message: Optional[str] = None, retry_count: int = 3) -> bool:
    """
    Memory repoファイルをGitHubに自動Push（堅牢化版・リトライ対応）
    
    Args:
        commit_message: カスタムコミットメッセージ
        retry_count: リトライ回数
        
    Returns:
        bool: Push成功フラグ
    """
    repo_root = Path(__file__).resolve().parent.parent
    
    # Git認証設定を確実に実行（Streamlit Cloud対応）
    if not setup_git_credentials():
        logger.error("Git credentials setup failed")
        return False
    
    # デフォルトコミットメッセージ
    if not commit_message:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        commit_message = f"chore: memory sync {ts}"
    
    for attempt in range(retry_count):
        try:
            logger.info(f"GitHub同期試行 {attempt + 1}/{retry_count}")
            
            # 1. git add memory_repo
            add_result = subprocess.run(
                ["git", "add", "memory_repo"],
                cwd=repo_root,
                check=False,
                capture_output=True,
                text=True
            )
            
            if add_result.returncode != 0:
                logger.warning(f"Git add failed: {add_result.stderr}")
                continue
            
            # 2. git commit -m "chore: memory sync YYYY-MM-DD HH:MM"
            commit_result = subprocess.run(
                ["git", "commit", "-m", commit_message],
                cwd=repo_root,
                check=False,
                capture_output=True,
                text=True
            )
            
            # デバッグ情報出力
            logger.info(f"Git commit return code: {commit_result.returncode}")
            logger.info(f"Git commit stdout: {commit_result.stdout}")
            logger.info(f"Git commit stderr: {commit_result.stderr}")
            
            # コミットが空の場合は正常終了
            if commit_result.returncode != 0:
                if "nothing to commit" in commit_result.stdout or "nothing to commit" in commit_result.stderr:
                    logger.info("No memory changes to commit")
                    return True
                else:
                    logger.warning(f"Git commit failed: stdout='{commit_result.stdout}' stderr='{commit_result.stderr}'")
                    continue
            
            # 3. git push origin main（リベースしてからプッシュ）
            push_success = False
            try:
                # まず通常push試行
                push_result = subprocess.run(
                    ["git", "push", "origin", "main"],
                    cwd=repo_root,
                    env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if push_result.returncode == 0:
                    logger.info("Memory files successfully pushed to GitHub")
                    return True
                elif "rejected" in push_result.stderr and "non-fast-forward" in push_result.stderr:
                    # 競合時のリベース処理
                    logger.info("Push rejected, attempting rebase...")
                    
                    # git pull --rebase origin main
                    rebase_result = subprocess.run(
                        ["git", "pull", "--rebase", "origin", "main"],
                        cwd=repo_root,
                        env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
                        capture_output=True,
                        text=True,
                        timeout=20
                    )
                    
                    if rebase_result.returncode == 0:
                        # リベース成功後に再push
                        retry_push_result = subprocess.run(
                            ["git", "push", "origin", "main"],
                            cwd=repo_root,
                            env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
                            capture_output=True,
                            text=True,
                            timeout=30
                        )
                        
                        if retry_push_result.returncode == 0:
                            logger.info("Memory files successfully pushed after rebase")
                            return True
                        else:
                            logger.warning(f"Push failed after rebase: {retry_push_result.stderr}")
                            continue
                    else:
                        logger.warning(f"Rebase failed: {rebase_result.stderr}")
                        continue
                elif "403" in push_result.stderr or "401" in push_result.stderr:
                    logger.error(f"Git push authentication failed: {push_result.stderr}")
                    logger.error("Check GITHUB_PAT token and permissions")
                    return False  # 認証エラーはリトライしない
                else:
                    logger.warning(f"Git push failed: {push_result.stderr}")
                    continue  # リトライ
                    
            except subprocess.TimeoutExpired:
                logger.warning(f"Git push timed out (attempt {attempt + 1})")
                continue
                
        except subprocess.TimeoutExpired:
            logger.warning(f"Git operation timed out (attempt {attempt + 1})")
            continue
        except subprocess.CalledProcessError as e:
            logger.warning(f"Git command error (attempt {attempt + 1}): {e}")
            if "403" in str(e) or "401" in str(e):
                logger.error("Authentication error - check GITHUB_PAT token")
                return False  # 認証エラーはリトライしない
            continue
        except Exception as e:
            logger.warning(f"Unexpected error (attempt {attempt + 1}): {e}")
            continue
    
    logger.error(f"GitHub sync failed after {retry_count} attempts")
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
    Git認証の設定（Streamlit Cloud対応強化版）
    GitHub Personal Access Token を使用
    """
    try:
        github_token = os.getenv("GITHUB_PAT") or os.getenv("GITHUB_TOKEN")
        
        if not github_token:
            logger.warning("GITHUB_PAT environment variable not set")
            return False
        
        repo_root = Path(__file__).resolve().parent.parent
        
        # Git credentialの設定（必須設定を確実に実行）
        commands = [
            # ユーザー識別情報（必須）
            ["git", "config", "--local", "user.email", "memory-bot@vpm-ariade.local"],
            ["git", "config", "--local", "user.name", "VPM Ariade Memory Bot"],
            # 認証設定
            ["git", "config", "--local", "credential.helper", "store"],
            # リモート設定確認・修正（HTTPS + Token）
            ["git", "config", "--local", "remote.origin.url", f"https://{github_token}@github.com/HirakuArai/vpm-ariade.git"]
        ]
        
        for cmd in commands:
            result = subprocess.run(cmd, cwd=repo_root, capture_output=True, text=True)
            if result.returncode != 0:
                logger.warning(f"Git config command failed: {' '.join(cmd)} - {result.stderr}")
                # 必須でない設定は続行
                if "user.email" in cmd or "user.name" in cmd:
                    logger.error(f"Critical git config failed: {' '.join(cmd)}")
                    return False
        
        # 設定確認
        check_commands = [
            ["git", "config", "--local", "user.email"],
            ["git", "config", "--local", "user.name"]
        ]
        
        for cmd in check_commands:
            result = subprocess.run(cmd, cwd=repo_root, capture_output=True, text=True)
            if result.returncode == 0:
                logger.info(f"Git config verified: {' '.join(cmd)} = {result.stdout.strip()}")
            else:
                logger.error(f"Git config verification failed: {' '.join(cmd)}")
                return False
        
        logger.info("Git credentials configured successfully")
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