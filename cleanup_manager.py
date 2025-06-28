#!/usr/bin/env python3
"""
Resilient Cleanup Manager for VPM-Ariade

This script manages the staged cleanup process with automatic recovery capability.
It can be interrupted at any point and resumed from the exact same stage.

Usage:
    python cleanup_manager.py start     # Start new cleanup process
    python cleanup_manager.py resume    # Resume interrupted process
    python cleanup_manager.py status    # Show current status
    python cleanup_manager.py rollback  # Rollback to last safe state
    python cleanup_manager.py stage N   # Execute specific stage N
"""

import json
import os
import sys
import subprocess
import datetime
import uuid
import glob
from pathlib import Path
from typing import Dict, List, Optional


class CleanupManager:
    def __init__(self, state_file: str = "cleanup_state.json"):
        self.state_file = state_file
        self.state = self._load_state()
        self.project_root = Path.cwd()
    
    def _load_state(self) -> Dict:
        """Load cleanup state from JSON file"""
        try:
            with open(self.state_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"❌ State file {self.state_file} not found!")
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON in state file: {e}")
            sys.exit(1)
    
    def _save_state(self):
        """Save current state to JSON file"""
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2)
    
    def _run_command(self, command: str, check: bool = True) -> subprocess.CompletedProcess:
        """Run shell command and return result"""
        print(f"🔧 Running: {command}")
        try:
            result = subprocess.run(
                command, 
                shell=True, 
                capture_output=True, 
                text=True,
                check=check
            )
            if result.stdout:
                print(f"✅ Output: {result.stdout.strip()}")
            return result
        except subprocess.CalledProcessError as e:
            print(f"❌ Command failed: {e}")
            print(f"❌ Error output: {e.stderr}")
            if check:
                raise
            return e
    
    def _verify_stage(self, stage: Dict) -> bool:
        """Verify that a stage completed successfully"""
        print(f"🔍 Verifying stage {stage['id']}: {stage['name']}")
        
        for cmd in stage['verification_commands']:
            try:
                result = self._run_command(cmd, check=False)
                if result.returncode != 0:
                    print(f"❌ Verification failed: {cmd}")
                    return False
            except Exception as e:
                print(f"❌ Verification error: {e}")
                return False
        
        print(f"✅ Stage {stage['id']} verification passed")
        return True
    
    def _create_backup(self) -> bool:
        """Create complete backup before starting"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"vpm_backup_{timestamp}"
        
        print(f"📦 Creating backup: {backup_name}")
        
        # Create git tag for backup
        self._run_command(f"git tag backup_{timestamp}")
        
        # Create external backup
        backup_path = f"../{backup_name}"
        self._run_command(f"cp -r . {backup_path}")
        
        print(f"✅ Backup created at {backup_path}")
        return True
    
    def _create_archive_structure(self) -> bool:
        """Create archive directory structure"""
        archive_dirs = [
            "archive/tools",
            "archive/tests", 
            "archive/conversations",
            "archive/data-backups",
            "archive/scripts",
            "archive/docs-legacy",
            "archive/disabled-pages"
        ]
        
        for dir_path in archive_dirs:
            os.makedirs(dir_path, exist_ok=True)
            print(f"📁 Created: {dir_path}")
        
        return True
    
    def execute_stage(self, stage_id: int) -> bool:
        """Execute a specific cleanup stage"""
        stage = None
        for s in self.state['stages']:
            if s['id'] == stage_id:
                stage = s
                break
        
        if not stage:
            print(f"❌ Stage {stage_id} not found!")
            return False
        
        if stage['status'] == 'completed':
            print(f"✅ Stage {stage_id} already completed, skipping")
            return True
        
        print(f"🚀 Executing stage {stage_id}: {stage['name']}")
        print(f"📝 Description: {stage['description']}")
        
        try:
            # Execute stage-specific logic
            success = self._execute_stage_logic(stage)
            
            if success:
                # Verify the stage
                if self._verify_stage(stage):
                    stage['status'] = 'completed'
                    self.state['cleanup_session']['completed_stages'].append(stage_id)
                    self.state['cleanup_session']['current_stage'] = stage_id + 1
                    print(f"✅ Stage {stage_id} completed successfully")
                else:
                    stage['status'] = 'failed'
                    self.state['cleanup_session']['failed_stages'].append(stage_id)
                    print(f"❌ Stage {stage_id} verification failed")
                    return False
            else:
                stage['status'] = 'failed'
                self.state['cleanup_session']['failed_stages'].append(stage_id)
                print(f"❌ Stage {stage_id} execution failed")
                return False
        
        except Exception as e:
            print(f"❌ Stage {stage_id} failed with exception: {e}")
            stage['status'] = 'failed'
            self.state['cleanup_session']['failed_stages'].append(stage_id)
            return False
        
        finally:
            self._save_state()
        
        return True
    
    def _execute_stage_logic(self, stage: Dict) -> bool:
        """Execute the actual logic for each stage"""
        stage_id = stage['id']
        
        if stage_id == 1:  # pre_cleanup_backup
            return self._create_backup()
        
        elif stage_id == 2:  # create_archive_branch
            timestamp = datetime.datetime.now().strftime("%Y%m%d")
            branch_name = f"archive/cleanup-{timestamp}"
            self._run_command(f"git checkout -b {branch_name}")
            self._create_archive_structure()
            return True
        
        elif stage_id == 3:  # archive_external_tools
            if os.path.exists("tools/pycg"):
                self._run_command("git mv tools/pycg archive/tools/")
                self._run_command("git commit -m 'archive: move external pycg tool to archive'")
            return True
        
        elif stage_id == 4:  # archive_root_tests
            test_files = glob.glob("test_*.py")
            if test_files:
                for test_file in test_files:
                    self._run_command(f"git mv {test_file} archive/tests/")
                self._run_command("git commit -m 'archive: move root-level test files to archive'")
            return True
        
        elif stage_id == 5:  # archive_conversations
            if os.path.exists("conversations"):
                self._run_command("git mv conversations archive/")
                self._run_command("git commit -m 'archive: move conversation logs to archive'")
            return True
        
        elif stage_id == 6:  # archive_generated_data
            # Archive old capability backups
            backup_files = glob.glob("data/kai_capabilities_*.json")
            for backup_file in backup_files:
                if "backup" in backup_file or len(backup_file.split('_')) > 3:
                    self._run_command(f"git mv {backup_file} archive/data-backups/")
            
            # Archive output and snapshots
            for dir_name in ["output", "snapshots", "kai_generated"]:
                if os.path.exists(dir_name):
                    self._run_command(f"git mv {dir_name} archive/data-backups/")
            
            self._run_command("git commit -m 'archive: move generated data and backups to archive'")
            return True
        
        elif stage_id == 7:  # archive_utility_scripts
            if os.path.exists("scripts"):
                self._run_command("git mv scripts archive/")
                self._run_command("git commit -m 'archive: move utility scripts to archive'")
            return True
        
        elif stage_id == 8:  # archive_disabled_pages
            if os.path.exists("disabled_pages"):
                self._run_command("git mv disabled_pages archive/")
            
            # Archive alternative app files
            app_variants = glob.glob("app_*.py")
            for app_file in app_variants:
                self._run_command(f"git mv {app_file} archive/disabled-pages/")
            
            self._run_command("git commit -m 'archive: move disabled pages and app variants to archive'")
            return True
        
        elif stage_id == 9:  # consolidate_documentation
            # Archive redundant docs
            redundant_docs = [
                "docs/base_os_rules_*.md",
                "docs/project_definition_*.md", 
                "docs/conversation_*.md",
                "docs/ui_*.md",
                "SESSION_HISTORY.md",
                "QUICK_REFERENCE.md"
            ]
            
            moved_any = False
            for pattern in redundant_docs:
                files = glob.glob(pattern)
                for file in files:
                    if os.path.exists(file):
                        self._run_command(f"git mv {file} archive/docs-legacy/")
                        moved_any = True
            
            if moved_any:
                self._run_command("git commit -m 'archive: move redundant documentation to archive'")
            return True
        
        elif stage_id == 10:  # final_verification
            print("🔍 Running final system verification...")
            return True
        
        return False
    
    def start_cleanup(self) -> bool:
        """Start a new cleanup process"""
        if self.state['cleanup_session']['session_id']:
            print("❌ Cleanup session already in progress!")
            print("Use 'resume' to continue or 'rollback' to start over")
            return False
        
        # Initialize new session
        session_id = str(uuid.uuid4())[:8]
        self.state['cleanup_session'] = {
            'session_id': session_id,
            'started_at': datetime.datetime.now().isoformat(),
            'current_stage': 1,
            'completed_stages': [],
            'failed_stages': [],
            'backup_created': False,
            'archive_branch_created': False
        }
        
        # Reset all stages to pending
        for stage in self.state['stages']:
            stage['status'] = 'pending'
        
        self._save_state()
        print(f"🚀 Started cleanup session: {session_id}")
        
        return self.resume_cleanup()
    
    def resume_cleanup(self) -> bool:
        """Resume an interrupted cleanup process"""
        session = self.state['cleanup_session']
        
        if not session['session_id']:
            print("❌ No cleanup session to resume!")
            return False
        
        print(f"🔄 Resuming cleanup session: {session['session_id']}")
        print(f"📅 Started: {session['started_at']}")
        print(f"📊 Completed stages: {session['completed_stages']}")
        
        current_stage = session['current_stage']
        total_stages = len(self.state['stages'])
        
        if current_stage > total_stages:
            print("✅ All stages completed!")
            return True
        
        # Execute remaining stages
        for stage_id in range(current_stage, total_stages + 1):
            print(f"\n📋 Progress: {stage_id}/{total_stages}")
            
            if not self.execute_stage(stage_id):
                print(f"❌ Cleanup stopped at stage {stage_id}")
                return False
        
        print("\n🎉 Cleanup process completed successfully!")
        return True
    
    def show_status(self):
        """Show current cleanup status"""
        session = self.state['cleanup_session']
        
        print(f"📊 Cleanup Status")
        print(f"Session ID: {session['session_id'] or 'None'}")
        print(f"Started: {session['started_at'] or 'Not started'}")
        print(f"Current Stage: {session['current_stage']}")
        print(f"Completed: {session['completed_stages']}")
        print(f"Failed: {session['failed_stages']}")
        
        print(f"\n📋 Stages Overview:")
        for stage in self.state['stages']:
            status_icon = {
                'pending': '⏳',
                'completed': '✅', 
                'failed': '❌'
            }.get(stage['status'], '❓')
            
            print(f"  {status_icon} Stage {stage['id']}: {stage['name']} ({stage['status']})")
    
    def rollback(self) -> bool:
        """Rollback to the state before cleanup started"""
        session = self.state['cleanup_session']
        
        if not session['session_id']:
            print("❌ No active session to rollback!")
            return False
        
        print(f"🔄 Rolling back session: {session['session_id']}")
        
        # Find backup tag
        result = self._run_command("git tag --list 'backup_*'", check=False)
        if result.returncode == 0 and result.stdout.strip():
            latest_backup = result.stdout.strip().split('\n')[-1]
            print(f"📦 Restoring from backup: {latest_backup}")
            self._run_command(f"git reset --hard {latest_backup}")
        else:
            print("❌ No backup found for rollback!")
            return False
        
        # Clear session
        self.state['cleanup_session'] = {
            'session_id': None,
            'started_at': None,
            'current_stage': 0,
            'completed_stages': [],
            'failed_stages': [],
            'backup_created': False,
            'archive_branch_created': False
        }
        
        # Reset all stages
        for stage in self.state['stages']:
            stage['status'] = 'pending'
        
        self._save_state()
        print("✅ Rollback completed")
        return True


def main():
    if len(sys.argv) < 2:
        print("Usage: python cleanup_manager.py [start|resume|status|rollback|stage N]")
        sys.exit(1)
    
    manager = CleanupManager()
    command = sys.argv[1].lower()
    
    if command == 'start':
        manager.start_cleanup()
    elif command == 'resume':
        manager.resume_cleanup()
    elif command == 'status':
        manager.show_status()
    elif command == 'rollback':
        manager.rollback()
    elif command == 'stage' and len(sys.argv) > 2:
        try:
            stage_id = int(sys.argv[2])
            manager.execute_stage(stage_id)
        except ValueError:
            print("❌ Stage number must be an integer")
    else:
        print("❌ Unknown command!")
        print("Available commands: start, resume, status, rollback, stage N")


if __name__ == "__main__":
    main()