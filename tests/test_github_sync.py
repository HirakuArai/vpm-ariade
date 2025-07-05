"""
Unit tests for GitHub Sync
GitHub同期機能のテスト
"""

import unittest
import tempfile
import os
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

# Import the module under test
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.github_sync import (
    push_memory_to_github, check_git_auth, setup_git_credentials,
    sync_memory_with_feedback
)


class TestGitHubSync(unittest.TestCase):
    """GitHub Sync unit tests"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        """Clean up test environment"""
        import shutil
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    @patch('subprocess.run')
    def test_check_git_auth_success(self, mock_run):
        """Test successful git authentication check"""
        # Mock successful git status
        mock_run.return_value = MagicMock(returncode=0)
        
        result = check_git_auth()
        self.assertTrue(result)
        
        # Verify git status was called
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        self.assertEqual(args[0], "git")
        self.assertEqual(args[1], "status")
    
    @patch('subprocess.run')
    def test_check_git_auth_failure(self, mock_run):
        """Test failed git authentication check"""
        # Mock failed git status
        mock_run.return_value = MagicMock(returncode=1)
        
        result = check_git_auth()
        self.assertFalse(result)
    
    @patch('subprocess.run')
    def test_check_git_auth_exception(self, mock_run):
        """Test git auth check with exception"""
        # Mock exception
        mock_run.side_effect = Exception("Git not found")
        
        result = check_git_auth()
        self.assertFalse(result)
    
    @patch('subprocess.run')
    def test_push_memory_success(self, mock_run):
        """Test successful memory push"""
        # Mock successful git commands
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="",
            stderr=""
        )
        
        result = push_memory_to_github("test commit")
        self.assertTrue(result)
        
        # Should call git add, commit, and push
        self.assertEqual(mock_run.call_count, 3)
    
    @patch('subprocess.run')
    def test_push_memory_nothing_to_commit(self, mock_run):
        """Test push when nothing to commit"""
        # Mock git responses
        responses = [
            MagicMock(returncode=0, stdout="", stderr=""),  # git add
            MagicMock(returncode=0, stdout="nothing to commit", stderr=""),  # git commit
            MagicMock(returncode=0, stdout="", stderr="")   # git push
        ]
        mock_run.side_effect = responses
        
        result = push_memory_to_github()
        self.assertTrue(result)  # Should be True even with nothing to commit
    
    @patch('subprocess.run')
    def test_push_memory_commit_failure(self, mock_run):
        """Test push with commit failure"""
        # Mock git add success, commit failure
        responses = [
            MagicMock(returncode=0, stdout="", stderr=""),  # git add
            MagicMock(returncode=1, stdout="", stderr="commit failed"),  # git commit
        ]
        mock_run.side_effect = responses
        
        result = push_memory_to_github()
        self.assertFalse(result)
    
    @patch('subprocess.run')
    def test_push_memory_timeout(self, mock_run):
        """Test push with timeout"""
        # Mock timeout exception
        mock_run.side_effect = subprocess.TimeoutExpired("git", 30)
        
        result = push_memory_to_github()
        self.assertFalse(result)
    
    @patch.dict(os.environ, {'GITHUB_PAT': 'test_token'})
    @patch('subprocess.run')
    def test_setup_git_credentials(self, mock_run):
        """Test git credentials setup"""
        mock_run.return_value = MagicMock(returncode=0)
        
        result = setup_git_credentials()
        self.assertTrue(result)
        
        # Should call git config commands
        self.assertGreater(mock_run.call_count, 0)
    
    @patch.dict(os.environ, {}, clear=True)
    def test_setup_git_credentials_no_token(self):
        """Test git credentials setup without token"""
        result = setup_git_credentials()
        self.assertFalse(result)
    
    @patch('core.github_sync.check_git_auth')
    @patch('core.github_sync.push_memory_to_github')
    def test_sync_memory_with_feedback_success(self, mock_push, mock_auth):
        """Test memory sync with feedback - success case"""
        mock_auth.return_value = True
        mock_push.return_value = True
        
        success, message = sync_memory_with_feedback()
        
        self.assertTrue(success)
        self.assertIn("同期しました", message)
    
    @patch('core.github_sync.check_git_auth')
    def test_sync_memory_with_feedback_auth_failure(self, mock_auth):
        """Test memory sync with feedback - auth failure"""
        mock_auth.return_value = False
        
        success, message = sync_memory_with_feedback()
        
        self.assertFalse(success)
        self.assertIn("認証エラー", message)
    
    @patch('core.github_sync.check_git_auth')
    @patch('core.github_sync.push_memory_to_github')
    def test_sync_memory_with_feedback_push_failure(self, mock_push, mock_auth):
        """Test memory sync with feedback - push failure"""
        mock_auth.return_value = True
        mock_push.return_value = False
        
        success, message = sync_memory_with_feedback()
        
        self.assertFalse(success)
        self.assertIn("失敗", message)
    
    def test_custom_commit_message(self):
        """Test custom commit message formatting"""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            
            custom_message = "custom test commit"
            push_memory_to_github(custom_message)
            
            # Check that custom message was used in commit command
            commit_call = None
            for call in mock_run.call_args_list:
                if "commit" in call[0][0]:
                    commit_call = call
                    break
            
            self.assertIsNotNone(commit_call)
            commit_args = commit_call[0][0]
            self.assertIn(custom_message, commit_args)


class TestGitHubSyncIntegration(unittest.TestCase):
    """Integration tests for GitHub sync functionality"""
    
    @patch('core.github_sync.logger')
    def test_error_logging(self, mock_logger):
        """Test that errors are properly logged"""
        with patch('subprocess.run', side_effect=Exception("Test error")):
            result = push_memory_to_github()
            self.assertFalse(result)
            
            # Check that error was logged
            mock_logger.error.assert_called()


if __name__ == '__main__':
    unittest.main()