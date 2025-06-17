# --- core/notification_system.py ---
"""
NotificationSystem - 統合通知管理システム
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import threading
import time
from queue import Queue, Empty

from .progress_monitor import ProgressAlert, AlertLevel
from .auto_update_engine import AutoUpdateResult
from .project_service import get_project

logger = logging.getLogger(__name__)

class NotificationChannel(Enum):
    """通知チャネル"""
    EMAIL = "email"
    SLACK = "slack"
    DISCORD = "discord"
    WEBHOOK = "webhook"
    UI = "ui"
    LOG = "log"

class NotificationPriority(Enum):
    """通知優先度"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"

@dataclass
class NotificationTemplate:
    """通知テンプレート"""
    id: str
    title_template: str
    body_template: str
    channels: List[NotificationChannel]
    priority: NotificationPriority
    conditions: Dict[str, Any]

@dataclass
class Notification:
    """通知オブジェクト"""
    id: str
    project_id: str
    title: str
    body: str
    priority: NotificationPriority
    channels: List[NotificationChannel]
    data: Dict[str, Any]
    created_at: str
    scheduled_for: Optional[str] = None
    sent_at: Optional[str] = None
    status: str = "pending"  # pending, sent, failed
    retry_count: int = 0

@dataclass
class NotificationRule:
    """通知ルール"""
    id: str
    name: str
    conditions: Dict[str, Any]
    template_id: str
    enabled: bool = True
    cooldown_minutes: int = 60  # 同種の通知のクールダウン時間

class NotificationSystem:
    """統合通知管理システム"""
    
    def __init__(self, projects_dir: Path | None = None):
        self.projects_dir = projects_dir
        self.notification_queue = Queue()
        self.sent_notifications = []
        self.handlers = {}
        self.is_running = False
        self.worker_thread = None
        
        # デフォルトテンプレート
        self.templates = {
            "task_overdue": NotificationTemplate(
                id="task_overdue",
                title_template="⚠️ タスク遅延アラート - {project_name}",
                body_template="プロジェクト「{project_name}」で{overdue_count}個のタスクが期限を過ぎています。\n\n詳細:\n{task_details}",
                channels=[NotificationChannel.UI, NotificationChannel.LOG],
                priority=NotificationPriority.HIGH,
                conditions={"alert_level": "warning"}
            ),
            "critical_blocker": NotificationTemplate(
                id="critical_blocker",
                title_template="🚨 緊急: 長期ブロッカー - {project_name}",
                body_template="プロジェクト「{project_name}」で{duration_days}日間継続しているブロッカーがあります。\n\n課題: {blocker_description}\n\n至急対応が必要です。",
                channels=[NotificationChannel.UI, NotificationChannel.LOG],
                priority=NotificationPriority.URGENT,
                conditions={"alert_level": "critical", "metric": "blocker_duration"}
            ),
            "phase_advancement": NotificationTemplate(
                id="phase_advancement",
                title_template="🎉 フェーズ進行 - {project_name}",
                body_template="プロジェクト「{project_name}」が{new_phase}フェーズに進行しました。\n\n現在の完了率: {completion_percentage}%",
                channels=[NotificationChannel.UI, NotificationChannel.LOG],
                priority=NotificationPriority.NORMAL,
                conditions={"event_type": "phase_advancement"}
            ),
            "auto_update_applied": NotificationTemplate(
                id="auto_update_applied",
                title_template="🤖 自動更新適用 - {project_name}",
                body_template="プロジェクト「{project_name}」で{update_count}件の自動更新が適用されました。\n\n更新内容:\n{update_details}",
                channels=[NotificationChannel.UI, NotificationChannel.LOG],
                priority=NotificationPriority.LOW,
                conditions={"event_type": "auto_update"}
            ),
            "project_health_critical": NotificationTemplate(
                id="project_health_critical",
                title_template="🆘 プロジェクト状態危険 - {project_name}",
                body_template="プロジェクト「{project_name}」の健康状態が危険レベルになりました。\n\nリスクスコア: {risk_score}\nアラート数: {alert_count}\n\n緊急の対応が必要です。",
                channels=[NotificationChannel.UI, NotificationChannel.LOG],
                priority=NotificationPriority.URGENT,
                conditions={"health_status": "critical"}
            )
        }
        
        # デフォルト通知ルール
        self.rules = [
            NotificationRule(
                id="task_overdue_rule",
                name="タスク遅延通知",
                conditions={"metric": "task_overdue", "min_overdue_count": 1},
                template_id="task_overdue",
                cooldown_minutes=120
            ),
            NotificationRule(
                id="critical_blocker_rule", 
                name="緊急ブロッカー通知",
                conditions={"metric": "blocker_duration", "alert_level": "critical"},
                template_id="critical_blocker",
                cooldown_minutes=60
            ),
            NotificationRule(
                id="phase_advancement_rule",
                name="フェーズ進行通知",
                conditions={"event_type": "phase_advancement"},
                template_id="phase_advancement",
                cooldown_minutes=5
            ),
            NotificationRule(
                id="auto_update_rule",
                name="自動更新通知",
                conditions={"event_type": "auto_update", "min_update_count": 1},
                template_id="auto_update_applied",
                cooldown_minutes=30
            ),
            NotificationRule(
                id="project_health_critical_rule",
                name="プロジェクト健康状態危険通知",
                conditions={"health_status": "critical"},
                template_id="project_health_critical",
                cooldown_minutes=240
            )
        ]
        
        # デフォルトハンドラーを登録
        self.register_handler(NotificationChannel.LOG, self._log_handler)
        self.register_handler(NotificationChannel.UI, self._ui_handler)
    
    def start(self):
        """通知システムを開始"""
        if not self.is_running:
            self.is_running = True
            self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
            self.worker_thread.start()
            logger.info("Notification system started")
    
    def stop(self):
        """通知システムを停止"""
        self.is_running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=5)
        logger.info("Notification system stopped")
    
    def register_handler(self, channel: NotificationChannel, handler: Callable):
        """通知ハンドラーを登録"""
        self.handlers[channel] = handler
        logger.info("Registered handler for channel: %s", channel.value)
    
    def process_progress_alerts(self, project_id: str, alerts: List[ProgressAlert]):
        """進捗アラートを処理して通知を生成"""
        
        for alert in alerts:
            self._process_alert(project_id, alert)
    
    def process_auto_update_result(self, project_id: str, result: AutoUpdateResult):
        """自動更新結果を処理して通知を生成"""
        
        if result.updates_applied:
            self._create_notification_from_template(
                project_id=project_id,
                template_id="auto_update_applied",
                data={
                    "event_type": "auto_update",
                    "update_count": len(result.updates_applied),
                    "update_details": "\n".join([f"- {u.reasoning}" for u in result.updates_applied])
                }
            )
        
        if result.phase_advanced:
            # フェーズ進行通知は lifecycle_manager で処理されるため、ここでは処理しない
            pass
    
    def process_phase_advancement(self, project_id: str, old_phase: str, new_phase: str, completion_percentage: float):
        """フェーズ進行を処理して通知を生成"""
        
        self._create_notification_from_template(
            project_id=project_id,
            template_id="phase_advancement",
            data={
                "event_type": "phase_advancement",
                "old_phase": old_phase,
                "new_phase": new_phase,
                "completion_percentage": completion_percentage
            }
        )
    
    def process_project_health_change(self, project_id: str, old_health: str, new_health: str, risk_score: float, alert_count: int):
        """プロジェクト健康状態変化を処理"""
        
        if new_health == "critical" and old_health != "critical":
            self._create_notification_from_template(
                project_id=project_id,
                template_id="project_health_critical",
                data={
                    "health_status": new_health,
                    "risk_score": f"{risk_score:.2f}",
                    "alert_count": alert_count
                }
            )
    
    def _process_alert(self, project_id: str, alert: ProgressAlert):
        """個別アラートを処理"""
        
        # アラートタイプに応じた通知生成
        if alert.metric.value == "task_overdue":
            self._create_notification_from_template(
                project_id=project_id,
                template_id="task_overdue",
                data={
                    "metric": alert.metric.value,
                    "alert_level": alert.level.value,
                    "overdue_count": len(alert.data.get("overdue_tasks", [])),
                    "task_details": self._format_overdue_tasks(alert.data.get("overdue_tasks", []))
                }
            )
        
        elif alert.metric.value == "blocker_duration" and alert.level == AlertLevel.CRITICAL:
            blockers = alert.data.get("long_duration_blockers", [])
            if blockers:
                longest_blocker = max(blockers, key=lambda x: x.get("duration_days", 0))
                self._create_notification_from_template(
                    project_id=project_id,
                    template_id="critical_blocker",
                    data={
                        "metric": alert.metric.value,
                        "alert_level": alert.level.value,
                        "duration_days": longest_blocker.get("duration_days", 0),
                        "blocker_description": longest_blocker.get("issue", {}).get("description", "不明")
                    }
                )
    
    def _create_notification_from_template(self, project_id: str, template_id: str, data: Dict[str, Any]):
        """テンプレートから通知を作成"""
        
        # ルールチェック
        applicable_rules = [r for r in self.rules if r.template_id == template_id and r.enabled]
        if not applicable_rules:
            return
        
        rule = applicable_rules[0]
        
        # 条件チェック
        if not self._check_rule_conditions(rule, data):
            return
        
        # クールダウンチェック
        if not self._check_cooldown(project_id, template_id, rule.cooldown_minutes):
            return
        
        # テンプレート取得
        template = self.templates.get(template_id)
        if not template:
            logger.warning("Template not found: %s", template_id)
            return
        
        # プロジェクト情報取得
        project_data = get_project(project_id, self.projects_dir)
        project_name = project_data.get("overview", project_id) if project_data else project_id
        
        # テンプレート変数
        template_vars = {
            "project_id": project_id,
            "project_name": project_name,
            **data
        }
        
        # 通知作成
        notification = Notification(
            id=f"{project_id}_{template_id}_{int(datetime.now().timestamp())}",
            project_id=project_id,
            title=template.title_template.format(**template_vars),
            body=template.body_template.format(**template_vars),
            priority=template.priority,
            channels=template.channels,
            data=data,
            created_at=datetime.utcnow().isoformat()
        )
        
        # 通知をキューに追加
        self.notification_queue.put(notification)
        logger.info("Notification queued: %s for project %s", template_id, project_id)
    
    def _check_rule_conditions(self, rule: NotificationRule, data: Dict[str, Any]) -> bool:
        """ルール条件をチェック"""
        
        for key, expected_value in rule.conditions.items():
            if key.startswith("min_"):
                actual_key = key[4:]  # "min_" を除去
                actual_value = data.get(actual_key, 0)
                if isinstance(actual_value, (int, float)) and actual_value < expected_value:
                    return False
            elif key.startswith("max_"):
                actual_key = key[4:]  # "max_" を除去
                actual_value = data.get(actual_key, 0)
                if isinstance(actual_value, (int, float)) and actual_value > expected_value:
                    return False
            else:
                if data.get(key) != expected_value:
                    return False
        
        return True
    
    def _check_cooldown(self, project_id: str, template_id: str, cooldown_minutes: int) -> bool:
        """クールダウン期間をチェック"""
        
        if cooldown_minutes <= 0:
            return True
        
        cutoff_time = datetime.utcnow() - timedelta(minutes=cooldown_minutes)
        
        # 最近送信された同種の通知をチェック
        for notification in self.sent_notifications:
            if (notification.project_id == project_id and 
                template_id in notification.id and
                notification.sent_at):
                
                try:
                    sent_time = datetime.fromisoformat(notification.sent_at.replace('Z', '+00:00'))
                    if sent_time > cutoff_time:
                        logger.debug("Notification blocked by cooldown: %s", template_id)
                        return False
                except ValueError:
                    continue
        
        return True
    
    def _format_overdue_tasks(self, overdue_tasks: List[Dict[str, Any]]) -> str:
        """遅延タスクをフォーマット"""
        
        if not overdue_tasks:
            return "詳細なし"
        
        lines = []
        for item in overdue_tasks[:5]:  # 最大5件表示
            task = item.get("task", {})
            days_overdue = item.get("days_overdue", 0)
            task_desc = task.get("description", "不明なタスク")
            lines.append(f"- {task_desc} ({days_overdue}日遅延)")
        
        if len(overdue_tasks) > 5:
            lines.append(f"... 他{len(overdue_tasks) - 5}件")
        
        return "\n".join(lines)
    
    def _worker_loop(self):
        """通知処理ワーカーループ"""
        
        while self.is_running:
            try:
                # キューから通知を取得（タイムアウト付き）
                notification = self.notification_queue.get(timeout=1.0)
                
                # 通知を送信
                self._send_notification(notification)
                
                # 完了をマーク
                self.notification_queue.task_done()
                
            except Empty:
                continue
            except Exception as e:
                logger.error("Error in notification worker loop: %s", str(e))
                time.sleep(1)
    
    def _send_notification(self, notification: Notification):
        """通知を送信"""
        
        success = True
        
        for channel in notification.channels:
            handler = self.handlers.get(channel)
            if handler:
                try:
                    handler(notification)
                    logger.debug("Notification sent via %s: %s", channel.value, notification.id)
                except Exception as e:
                    logger.error("Error sending notification via %s: %s", channel.value, str(e))
                    success = False
            else:
                logger.warning("No handler registered for channel: %s", channel.value)
                success = False
        
        # 送信状態を更新
        notification.status = "sent" if success else "failed"
        notification.sent_at = datetime.utcnow().isoformat()
        
        # 送信履歴に追加
        self.sent_notifications.append(notification)
        
        # 履歴の古い項目を削除（メモリ節約）
        if len(self.sent_notifications) > 1000:
            self.sent_notifications = self.sent_notifications[-500:]
    
    def _log_handler(self, notification: Notification):
        """ログ通知ハンドラー"""
        
        log_level = {
            NotificationPriority.LOW: logging.INFO,
            NotificationPriority.NORMAL: logging.INFO,
            NotificationPriority.HIGH: logging.WARNING,
            NotificationPriority.URGENT: logging.ERROR
        }.get(notification.priority, logging.INFO)
        
        logger.log(log_level, "NOTIFICATION [%s]: %s - %s", 
                  notification.priority.value.upper(), 
                  notification.title, 
                  notification.body)
    
    def _ui_handler(self, notification: Notification):
        """UI通知ハンドラー（Streamlit用）"""
        
        # Streamlitのセッション状態に通知を保存
        # 実際のStreamlitアプリケーションで利用される
        ui_notification = {
            "id": notification.id,
            "title": notification.title,
            "body": notification.body,
            "priority": notification.priority.value,
            "created_at": notification.created_at,
            "project_id": notification.project_id
        }
        
        # ファイルベースの簡易UI通知システム
        ui_notifications_file = Path("data/ui_notifications.json")
        ui_notifications_file.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            if ui_notifications_file.exists():
                with open(ui_notifications_file, 'r', encoding='utf-8') as f:
                    ui_notifications = json.load(f)
            else:
                ui_notifications = []
            
            ui_notifications.append(ui_notification)
            
            # 最新100件のみ保持
            if len(ui_notifications) > 100:
                ui_notifications = ui_notifications[-100:]
            
            with open(ui_notifications_file, 'w', encoding='utf-8') as f:
                json.dump(ui_notifications, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.error("Error saving UI notification: %s", str(e))
    
    def get_notifications_for_project(self, project_id: str, limit: int = 50) -> List[Notification]:
        """プロジェクトの通知履歴を取得"""
        
        project_notifications = [
            n for n in self.sent_notifications 
            if n.project_id == project_id
        ]
        
        # 新しい順にソート
        project_notifications.sort(key=lambda x: x.created_at, reverse=True)
        
        return project_notifications[:limit]
    
    def get_recent_notifications(self, hours: int = 24, limit: int = 100) -> List[Notification]:
        """最近の通知を取得"""
        
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        recent_notifications = [
            n for n in self.sent_notifications
            if datetime.fromisoformat(n.created_at.replace('Z', '+00:00')) > cutoff_time
        ]
        
        # 新しい順にソート
        recent_notifications.sort(key=lambda x: x.created_at, reverse=True)
        
        return recent_notifications[:limit]
    
    def clear_old_notifications(self, days: int = 30):
        """古い通知を削除"""
        
        cutoff_time = datetime.utcnow() - timedelta(days=days)
        
        self.sent_notifications = [
            n for n in self.sent_notifications
            if datetime.fromisoformat(n.created_at.replace('Z', '+00:00')) > cutoff_time
        ]
        
        logger.info("Cleared notifications older than %d days", days)