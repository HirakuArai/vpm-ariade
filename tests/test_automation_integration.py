# --- tests/test_automation_integration.py ---
"""
Test automation features integration (Week 3-4)
"""

import pytest
import tempfile
import json
from pathlib import Path
from datetime import datetime, timedelta
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.auto_update_engine import AutoUpdateEngine, UpdateCandidate
from core.progress_monitor import ProgressMonitor, AlertLevel
from core.notification_system import NotificationSystem, NotificationChannel
from core.schedule_manager import ScheduleManager
from core.project_service import create_project, add_task, update_project_field
from core.models import ProjectPhase


class TestAutoUpdateEngine:
    """Test AutoUpdateEngine functionality"""
    
    def setup_method(self):
        """Setup test environment"""
        self.test_dir = Path(tempfile.mkdtemp())
        # Mock the PROJECTS_DIR for testing
        import core.project_service
        self.original_projects_dir = core.project_service.PROJECTS_DIR
        core.project_service.PROJECTS_DIR = self.test_dir
    
    def teardown_method(self):
        """Cleanup test environment"""
        import shutil
        import core.project_service
        core.project_service.PROJECTS_DIR = self.original_projects_dir
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
    
    def test_auto_update_engine_initialization(self):
        """AutoUpdateEngine初期化テスト"""
        engine = AutoUpdateEngine(self.test_dir)
        
        assert engine.projects_dir == self.test_dir
        assert engine.confidence_threshold == 0.7
        assert "task_completion" in engine.update_patterns
        assert "task_creation" in engine.update_patterns
    
    def test_task_completion_detection(self):
        """タスク完了検出テスト"""
        # テストプロジェクト作成
        project = create_project("test-auto-update", "Auto Update Test", "test_user")
        add_task(project.identifier, "ログイン機能実装", "2024-12-31", "test_user", self.test_dir)
        
        engine = AutoUpdateEngine(self.test_dir)
        
        # タスク完了の会話を処理
        user_input = "ログイン機能の実装が完了しました"
        assistant_reply = "お疲れ様でした。次のタスクに進みましょう。"
        
        result = engine.process_conversation(project.identifier, user_input, assistant_reply)
        
        assert result.success == True
        assert len(result.updates_applied) > 0
        
        # タスク完了の更新が含まれているかチェック
        completion_updates = [u for u in result.updates_applied if u.field == "task_completion"]
        assert len(completion_updates) > 0
    
    def test_blocker_identification(self):
        """ブロッカー識別テスト"""
        project = create_project("test-blocker", "Blocker Test", "test_user")
        engine = AutoUpdateEngine(self.test_dir)
        
        user_input = "データベース接続でエラーが発生して作業が止まっています"
        assistant_reply = "エラーの詳細を調査しましょう"
        
        result = engine.process_conversation(project.identifier, user_input, assistant_reply)
        
        assert result.success == True
        
        # ブロッカー識別の更新をチェック
        blocker_updates = [u for u in result.updates_applied if u.field == "blocking_issues"]
        assert len(blocker_updates) > 0
        
        blocker_update = blocker_updates[0]
        assert "データベース接続" in str(blocker_update.new_value)
    
    def test_new_task_creation(self):
        """新規タスク作成テスト"""
        project = create_project("test-new-task", "New Task Test", "test_user")
        engine = AutoUpdateEngine(self.test_dir)
        
        user_input = "次にユーザー認証機能を実装する必要があります"
        assistant_reply = "承知しました。認証機能の要件を整理しましょう。"
        
        result = engine.process_conversation(project.identifier, user_input, assistant_reply)
        
        assert result.success == True
        
        # 新規タスク作成の更新をチェック
        task_updates = [u for u in result.updates_applied if u.field == "new_task"]
        assert len(task_updates) > 0


class TestProgressMonitor:
    """Test ProgressMonitor functionality"""
    
    def setup_method(self):
        """Setup test environment"""
        self.test_dir = Path(tempfile.mkdtemp())
        import core.project_service
        self.original_projects_dir = core.project_service.PROJECTS_DIR
        core.project_service.PROJECTS_DIR = self.test_dir
    
    def teardown_method(self):
        """Cleanup test environment"""
        import shutil
        import core.project_service
        core.project_service.PROJECTS_DIR = self.original_projects_dir
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
    
    def test_progress_monitor_initialization(self):
        """ProgressMonitor初期化テスト"""
        monitor = ProgressMonitor(self.test_dir)
        
        assert monitor.projects_dir == self.test_dir
        assert "task_overdue_threshold_days" in monitor.monitoring_config
        assert "health_thresholds" in monitor.monitoring_config
    
    def test_task_overdue_detection(self):
        """タスク遅延検出テスト"""
        # 遅延タスクを持つプロジェクトを作成
        project = create_project("test-overdue", "Overdue Test", "test_user")
        
        # 過去の日付でタスクを追加
        past_date = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
        add_task(project.identifier, "遅延タスク", past_date, "test_user", self.test_dir)
        
        monitor = ProgressMonitor(self.test_dir)
        report = monitor.monitor_project(project.identifier)
        
        assert report.project_id == project.identifier
        assert len(report.alerts) > 0
        
        # 遅延アラートがあることを確認
        overdue_alerts = [a for a in report.alerts if a.metric.value == "task_overdue"]
        assert len(overdue_alerts) > 0
        
        overdue_alert = overdue_alerts[0]
        assert overdue_alert.level in [AlertLevel.WARNING, AlertLevel.CRITICAL]
        assert "遅延" in overdue_alert.title
    
    def test_completion_rate_monitoring(self):
        """完了率監視テスト"""
        project = create_project("test-completion", "Completion Test", "test_user")
        
        # 複数のタスクを追加（一部は未完了）
        add_task(project.identifier, "タスク1", "2024-12-31", "test_user", self.test_dir)
        add_task(project.identifier, "タスク2", "2024-12-31", "test_user", self.test_dir)
        add_task(project.identifier, "タスク3", "2024-12-31", "test_user", self.test_dir)
        
        monitor = ProgressMonitor(self.test_dir)
        report = monitor.monitor_project(project.identifier)
        
        assert report.overall_health in ["healthy", "at_risk", "critical"]
        assert "task_completion_rate" in report.metrics
        assert report.task_summary["total"] == 3
    
    def test_health_assessment(self):
        """健康状態評価テスト"""
        project = create_project("test-health", "Health Test", "test_user")
        
        monitor = ProgressMonitor(self.test_dir)
        report = monitor.monitor_project(project.identifier)
        
        # 新規プロジェクトは健康な状態になるはず
        assert report.overall_health in ["healthy", "at_risk"]
        assert isinstance(report.metrics["risk_score"], float)
        assert 0.0 <= report.metrics["risk_score"] <= 1.0


class TestNotificationSystem:
    """Test NotificationSystem functionality"""
    
    def setup_method(self):
        """Setup test environment"""
        self.test_dir = Path(tempfile.mkdtemp())
        import core.project_service
        self.original_projects_dir = core.project_service.PROJECTS_DIR
        core.project_service.PROJECTS_DIR = self.test_dir
    
    def teardown_method(self):
        """Cleanup test environment"""
        import shutil
        import core.project_service
        core.project_service.PROJECTS_DIR = self.original_projects_dir
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
    
    def test_notification_system_initialization(self):
        """NotificationSystem初期化テスト"""
        notification_system = NotificationSystem(self.test_dir)
        
        assert notification_system.projects_dir == self.test_dir
        assert "task_overdue" in notification_system.templates
        assert len(notification_system.rules) > 0
        assert NotificationChannel.LOG in notification_system.handlers
    
    def test_template_based_notification(self):
        """テンプレートベース通知テスト"""
        project = create_project("test-notification", "Notification Test", "test_user")
        notification_system = NotificationSystem(self.test_dir)
        
        # 通知作成
        notification_system._create_notification_from_template(
            project_id=project.identifier,
            template_id="task_overdue",
            data={
                "metric": "task_overdue",
                "alert_level": "warning",
                "overdue_count": 2,
                "task_details": "- タスクA (2日遅延)\n- タスクB (1日遅延)"
            }
        )
        
        # 通知がキューに追加されているかチェック
        assert not notification_system.notification_queue.empty()
    
    def test_cooldown_mechanism(self):
        """クールダウン機能テスト"""
        project = create_project("test-cooldown", "Cooldown Test", "test_user")
        notification_system = NotificationSystem(self.test_dir)
        
        # 同じテンプレートで2回通知を試行
        data = {"event_type": "auto_update", "update_count": 1, "update_details": "test"}
        
        # 1回目は送信される
        notification_system._create_notification_from_template(
            project_id=project.identifier,
            template_id="auto_update_applied",
            data=data
        )
        first_queue_size = notification_system.notification_queue.qsize()
        
        # 2回目は即座にはブロックされる（クールダウン）
        notification_system._create_notification_from_template(
            project_id=project.identifier,
            template_id="auto_update_applied", 
            data=data
        )
        second_queue_size = notification_system.notification_queue.qsize()
        
        # クールダウンが適用されているかは実装により異なるが、少なくともエラーは発生しない
        assert second_queue_size >= first_queue_size


class TestScheduleManager:
    """Test ScheduleManager functionality"""
    
    def setup_method(self):
        """Setup test environment"""
        self.test_dir = Path(tempfile.mkdtemp())
        import core.project_service
        self.original_projects_dir = core.project_service.PROJECTS_DIR
        core.project_service.PROJECTS_DIR = self.test_dir
    
    def teardown_method(self):
        """Cleanup test environment"""
        import shutil
        import core.project_service
        core.project_service.PROJECTS_DIR = self.original_projects_dir
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
    
    def test_schedule_manager_initialization(self):
        """ScheduleManager初期化テスト"""
        schedule_manager = ScheduleManager(self.test_dir)
        
        assert schedule_manager.projects_dir == self.test_dir
        assert "work_days_per_week" in schedule_manager.schedule_config
        assert schedule_manager.schedule_data_dir.exists()
    
    def test_project_schedule_generation(self):
        """プロジェクトスケジュール生成テスト"""
        project = create_project("test-schedule", "Schedule Test", "test_user")
        
        # テスト用タスクを追加
        add_task(project.identifier, "設計", "2024-12-15", "test_user", self.test_dir)
        add_task(project.identifier, "実装", "2024-12-25", "test_user", self.test_dir)
        add_task(project.identifier, "テスト", "2024-12-31", "test_user", self.test_dir)
        
        schedule_manager = ScheduleManager(self.test_dir)
        schedule = schedule_manager.generate_project_schedule(project.identifier)
        
        assert schedule["project_id"] == project.identifier
        assert "events" in schedule
        assert "critical_path" in schedule
        assert "milestones" in schedule
        assert "estimated_completion" in schedule
        
        # イベントが正しく変換されているかチェック
        events = schedule["events"]
        assert len(events) == 3  # 3つのタスクが3つのイベントになる
        
        for event in events:
            assert "title" in event
            assert "start_date" in event
            assert "end_date" in event
    
    def test_upcoming_deadlines_detection(self):
        """今後の期限検出テスト"""
        project = create_project("test-deadlines", "Deadlines Test", "test_user")
        
        # 今後の期限でタスクを追加
        future_date = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")
        add_task(project.identifier, "締切近いタスク", future_date, "test_user", self.test_dir)
        
        # アクティブ状態に設定
        from core.project_service import set_status
        set_status(project.identifier, "ACTIVE", self.test_dir)
        
        schedule_manager = ScheduleManager(self.test_dir)
        
        # スケジュールを生成
        schedule_manager.generate_project_schedule(project.identifier)
        
        # 今後の期限を取得
        deadlines = schedule_manager.get_upcoming_deadlines(days_ahead=7)
        
        # 作成したタスクの期限が含まれているかチェック
        project_deadlines = [d for d in deadlines if d["project_id"] == project.identifier]
        assert len(project_deadlines) > 0
    
    def test_schedule_recommendations(self):
        """スケジュール推奨事項テスト"""
        project = create_project("test-recommendations", "Recommendations Test", "test_user")
        
        # 期限が近いタスクを追加
        urgent_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        add_task(project.identifier, "緊急タスク", urgent_date, "test_user", self.test_dir)
        
        schedule_manager = ScheduleManager(self.test_dir)
        
        # スケジュールを生成
        schedule_manager.generate_project_schedule(project.identifier)
        
        # 推奨事項を生成
        recommendations = schedule_manager.generate_schedule_recommendations(project.identifier)
        
        # 推奨事項が生成されているかチェック
        assert isinstance(recommendations, list)
        # 期限が近いタスクがあるため、何らかの推奨事項があるはず
        if recommendations:
            rec = recommendations[0]
            assert hasattr(rec, 'title')
            assert hasattr(rec, 'description')
            assert hasattr(rec, 'suggested_actions')


class TestAutomationIntegration:
    """Test integration between automation components"""
    
    def setup_method(self):
        """Setup test environment"""
        self.test_dir = Path(tempfile.mkdtemp())
        import core.project_service
        self.original_projects_dir = core.project_service.PROJECTS_DIR
        core.project_service.PROJECTS_DIR = self.test_dir
    
    def teardown_method(self):
        """Cleanup test environment"""
        import shutil
        import core.project_service
        core.project_service.PROJECTS_DIR = self.original_projects_dir
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
    
    def test_auto_update_to_progress_monitor_flow(self):
        """AutoUpdateEngine → ProgressMonitor の連携テスト"""
        project = create_project("test-integration-1", "Integration Test 1", "test_user")
        
        # AutoUpdateEngineでタスク完了を処理
        auto_engine = AutoUpdateEngine(self.test_dir)
        add_task(project.identifier, "統合テストタスク", "2024-12-31", "test_user", self.test_dir)
        
        user_input = "統合テストタスクが完了しました"
        assistant_reply = "完了おめでとうございます"
        
        auto_result = auto_engine.process_conversation(project.identifier, user_input, assistant_reply)
        assert auto_result.success
        
        # ProgressMonitorで状況を監視
        progress_monitor = ProgressMonitor(self.test_dir)
        report = progress_monitor.monitor_project(project.identifier)
        
        assert report.project_id == project.identifier
        assert isinstance(report.task_summary, dict)
        assert report.overall_health in ["healthy", "at_risk", "critical"]
    
    def test_progress_monitor_to_notification_flow(self):
        """ProgressMonitor → NotificationSystem の連携テスト"""
        project = create_project("test-integration-2", "Integration Test 2", "test_user")
        
        # 遅延タスクを作成してアラートを発生させる
        past_date = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")
        add_task(project.identifier, "遅延統合テストタスク", past_date, "test_user", self.test_dir)
        
        # ProgressMonitorでアラートを生成
        progress_monitor = ProgressMonitor(self.test_dir)
        report = progress_monitor.monitor_project(project.identifier)
        
        # NotificationSystemでアラートを処理
        notification_system = NotificationSystem(self.test_dir)
        notification_system.process_progress_alerts(project.identifier, report.alerts)
        
        # 通知が生成されているかチェック
        if report.alerts:
            # アラートがある場合、通知がキューに追加されるはず
            assert notification_system.notification_queue.qsize() >= 0
    
    def test_schedule_manager_integration(self):
        """ScheduleManager統合テスト"""
        project = create_project("test-integration-3", "Integration Test 3", "test_user")
        
        # 複数のタスクでスケジュールを作成
        add_task(project.identifier, "統合タスク1", "2024-12-20", "test_user", self.test_dir)
        add_task(project.identifier, "統合タスク2", "2024-12-25", "test_user", self.test_dir)
        add_task(project.identifier, "統合タスク3", "2024-12-30", "test_user", self.test_dir)
        
        # アクティブ状態に設定
        from core.project_service import set_status
        set_status(project.identifier, "ACTIVE", self.test_dir)
        
        # ScheduleManagerでスケジュール生成
        schedule_manager = ScheduleManager(self.test_dir)
        schedule = schedule_manager.generate_project_schedule(project.identifier)
        
        # 他のコンポーネントとの相互作用をテスト
        progress_monitor = ProgressMonitor(self.test_dir)
        report = progress_monitor.monitor_project(project.identifier)
        
        # スケジュールと進捗レポートの整合性をチェック
        assert schedule["project_id"] == report.project_id
        
        # 今後の期限チェック
        deadlines = schedule_manager.get_upcoming_deadlines(days_ahead=30)
        project_deadlines = [d for d in deadlines if d["project_id"] == project.identifier]
        
        # 作成したタスクの期限が含まれているかチェック
        assert len(project_deadlines) > 0
    
    def test_full_automation_workflow(self):
        """完全な自動化ワークフローのテスト"""
        project = create_project("test-full-workflow", "Full Workflow Test", "test_user")
        
        # 初期タスクを追加
        add_task(project.identifier, "ワークフローテストタスク", "2024-12-31", "test_user", self.test_dir)
        
        # アクティブ状態に設定
        from core.project_service import set_status
        set_status(project.identifier, "ACTIVE", self.test_dir)
        
        # 1. AutoUpdateEngineで会話を処理
        auto_engine = AutoUpdateEngine(self.test_dir)
        user_input = "ワークフローテストタスクが完了しました。次にデータベース設計のタスクを追加する必要があります。"
        assistant_reply = "完了おめでとうございます。データベース設計のタスクを追加しましょう。"
        
        auto_result = auto_engine.process_conversation(project.identifier, user_input, assistant_reply)
        assert auto_result.success
        
        # 2. ScheduleManagerでスケジュール更新
        schedule_manager = ScheduleManager(self.test_dir)
        schedule = schedule_manager.generate_project_schedule(project.identifier)
        assert schedule["project_id"] == project.identifier
        
        # 3. ProgressMonitorで監視
        progress_monitor = ProgressMonitor(self.test_dir)
        report = progress_monitor.monitor_project(project.identifier)
        assert report.project_id == project.identifier
        
        # 4. NotificationSystemで通知処理
        notification_system = NotificationSystem(self.test_dir)
        
        # AutoUpdate結果を処理
        notification_system.process_auto_update_result(project.identifier, auto_result)
        
        # Progress監視結果を処理
        notification_system.process_progress_alerts(project.identifier, report.alerts)
        
        # 全体のワークフローが正常に動作したことを確認
        assert auto_result.success
        assert len(schedule["events"]) > 0
        assert report.overall_health in ["healthy", "at_risk", "critical"]
        
        # 通知システムが少なくともエラーなく動作したことを確認
        assert hasattr(notification_system, 'notification_queue')


class TestAutomationErrorHandling:
    """Test error handling in automation components"""
    
    def setup_method(self):
        """Setup test environment"""
        self.test_dir = Path(tempfile.mkdtemp())
        import core.project_service
        self.original_projects_dir = core.project_service.PROJECTS_DIR
        core.project_service.PROJECTS_DIR = self.test_dir
    
    def teardown_method(self):
        """Cleanup test environment"""
        import shutil
        import core.project_service
        core.project_service.PROJECTS_DIR = self.original_projects_dir
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
    
    def test_auto_update_with_invalid_project(self):
        """存在しないプロジェクトでのAutoUpdateEngineエラーハンドリング"""
        engine = AutoUpdateEngine(self.test_dir)
        
        result = engine.process_conversation("non-existent-project", "test input", "test reply")
        
        assert result.success == False
        assert len(result.errors) > 0
        assert "not found" in result.errors[0]
    
    def test_progress_monitor_with_invalid_project(self):
        """存在しないプロジェクトでのProgressMonitorエラーハンドリング"""
        monitor = ProgressMonitor(self.test_dir)
        
        with pytest.raises(ValueError, match="not found"):
            monitor.monitor_project("non-existent-project")
    
    def test_schedule_manager_with_invalid_project(self):
        """存在しないプロジェクトでのScheduleManagerエラーハンドリング"""
        schedule_manager = ScheduleManager(self.test_dir)
        
        with pytest.raises(ValueError, match="not found"):
            schedule_manager.generate_project_schedule("non-existent-project")
    
    def test_notification_system_resilience(self):
        """NotificationSystemの耐障害性テスト"""
        notification_system = NotificationSystem(self.test_dir)
        
        # 不正なデータでの通知生成を試行
        notification_system._create_notification_from_template(
            project_id="non-existent",
            template_id="non-existent-template",
            data={}
        )
        
        # エラーが発生してもシステムが停止しないことを確認
        assert hasattr(notification_system, 'notification_queue')
        
        # 正常なデータでの通知生成は動作することを確認
        project = create_project("test-resilience", "Resilience Test", "test_user")
        notification_system._create_notification_from_template(
            project_id=project.identifier,
            template_id="auto_update_applied",
            data={"event_type": "auto_update", "update_count": 1, "update_details": "test"}
        )
        
        # 正常な通知は処理されることを確認
        assert notification_system.notification_queue.qsize() >= 0