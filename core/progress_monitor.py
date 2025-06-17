# --- core/progress_monitor.py ---
"""
ProgressMonitor - プロジェクト進捗監視とアラート生成
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from .models import ProjectPhase, DEFAULT_UNDEF
from .project_service import get_project, list_projects
from .lifecycle_manager import ProjectLifecycleManager

logger = logging.getLogger(__name__)

class AlertLevel(Enum):
    """アラートレベル"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"

class MonitoringMetric(Enum):
    """監視メトリック"""
    TASK_OVERDUE = "task_overdue"
    PHASE_DELAY = "phase_delay"
    COMPLETION_RATE = "completion_rate"
    BLOCKER_DURATION = "blocker_duration"
    MILESTONE_DELAY = "milestone_delay"
    ACTIVITY_STAGNATION = "activity_stagnation"

@dataclass
class ProgressAlert:
    """進捗アラート"""
    id: str
    project_id: str
    metric: MonitoringMetric
    level: AlertLevel
    title: str
    description: str
    impact: str
    recommendations: List[str]
    created_at: str
    data: Dict[str, Any]

@dataclass
class ProgressReport:
    """進捗レポート"""
    project_id: str
    generated_at: str
    overall_health: str  # "healthy", "at_risk", "critical"
    completion_percentage: float
    phase_progress: Dict[str, Any]
    task_summary: Dict[str, int]
    alerts: List[ProgressAlert]
    metrics: Dict[str, Any]
    predictions: Dict[str, Any]

class ProgressMonitor:
    """プロジェクト進捗監視システム"""
    
    def __init__(self, projects_dir: Path | None = None):
        self.projects_dir = projects_dir
        self.lifecycle_manager = ProjectLifecycleManager(projects_dir)
        
        # 監視設定
        self.monitoring_config = {
            "task_overdue_threshold_days": 1,  # タスク遅延アラート閾値
            "phase_delay_threshold_days": 7,   # フェーズ遅延アラート閾値
            "completion_rate_threshold": 0.2,  # 完了率低下アラート閾値
            "blocker_duration_threshold_days": 3,  # ブロッカー継続アラート閾値
            "activity_stagnation_threshold_days": 5,  # 活動停滞アラート閾値
            "health_thresholds": {
                "healthy": {"min_completion_rate": 0.8, "max_overdue_tasks": 1},
                "at_risk": {"min_completion_rate": 0.5, "max_overdue_tasks": 3},
                "critical": {"min_completion_rate": 0.3, "max_overdue_tasks": 5}
            }
        }
    
    def monitor_project(self, project_id: str) -> ProgressReport:
        """プロジェクトの進捗を監視してレポートを生成"""
        
        try:
            project_data = get_project(project_id, self.projects_dir)
            if not project_data:
                raise ValueError(f"Project {project_id} not found")
            
            # 各メトリックをチェック
            alerts = []
            alerts.extend(self._check_task_overdue(project_id, project_data))
            alerts.extend(self._check_phase_delay(project_id, project_data))
            alerts.extend(self._check_completion_rate(project_id, project_data))
            alerts.extend(self._check_blocker_duration(project_id, project_data))
            alerts.extend(self._check_activity_stagnation(project_id, project_data))
            
            # 進捗サマリーを生成
            task_summary = self._generate_task_summary(project_data)
            phase_progress = self.lifecycle_manager.get_phase_progress(project_id)
            metrics = self._calculate_metrics(project_data, alerts)
            predictions = self._generate_predictions(project_data, metrics)
            
            # 全体的な健康状態を判定
            overall_health = self._assess_overall_health(metrics, alerts)
            
            completion_percentage = phase_progress.get("completion_percentage", 0.0)
            
            return ProgressReport(
                project_id=project_id,
                generated_at=datetime.utcnow().isoformat(),
                overall_health=overall_health,
                completion_percentage=completion_percentage,
                phase_progress=phase_progress,
                task_summary=task_summary,
                alerts=alerts,
                metrics=metrics,
                predictions=predictions
            )
            
        except Exception as e:
            logger.error("Error monitoring project %s: %s", project_id, str(e))
            raise
    
    def monitor_all_projects(self) -> Dict[str, ProgressReport]:
        """全プロジェクトの進捗を監視"""
        reports = {}
        
        try:
            projects = list_projects(self.projects_dir)
            for project in projects:
                project_id = project.get("identifier")
                if project_id and project.get("status") == "ACTIVE":
                    try:
                        reports[project_id] = self.monitor_project(project_id)
                    except Exception as e:
                        logger.error("Error monitoring project %s: %s", project_id, str(e))
                        
        except Exception as e:
            logger.error("Error monitoring all projects: %s", str(e))
        
        return reports
    
    def _check_task_overdue(self, project_id: str, project_data: Dict[str, Any]) -> List[ProgressAlert]:
        """遅延タスクのチェック"""
        alerts = []
        tasks = project_data.get("tasks", [])
        
        if not isinstance(tasks, list):
            return alerts
        
        today = datetime.now().date()
        overdue_tasks = []
        
        for task in tasks:
            if not isinstance(task, dict):
                continue
                
            due_date_str = task.get("due_date")
            status = task.get("status", "")
            
            if due_date_str and status not in ["completed", "完了", "COMPLETED"]:
                try:
                    due_date = datetime.strptime(due_date_str, "%Y-%m-%d").date()
                    days_overdue = (today - due_date).days
                    
                    if days_overdue > self.monitoring_config["task_overdue_threshold_days"]:
                        overdue_tasks.append({
                            "task": task,
                            "days_overdue": days_overdue
                        })
                except ValueError:
                    continue
        
        if overdue_tasks:
            level = AlertLevel.CRITICAL if len(overdue_tasks) > 3 else AlertLevel.WARNING
            
            alerts.append(ProgressAlert(
                id=f"{project_id}_task_overdue_{int(datetime.now().timestamp())}",
                project_id=project_id,
                metric=MonitoringMetric.TASK_OVERDUE,
                level=level,
                title=f"遅延タスクが{len(overdue_tasks)}件あります",
                description=f"{len(overdue_tasks)}個のタスクが期限を過ぎています",
                impact="プロジェクト完了に遅れが生じる可能性があります",
                recommendations=[
                    "遅延タスクの優先度を見直す",
                    "リソース配分を調整する", 
                    "期限の再設定を検討する",
                    "ブロッカーがないか確認する"
                ],
                created_at=datetime.utcnow().isoformat(),
                data={"overdue_tasks": overdue_tasks}
            ))
        
        return alerts
    
    def _check_phase_delay(self, project_id: str, project_data: Dict[str, Any]) -> List[ProgressAlert]:
        """フェーズ遅延のチェック"""
        alerts = []
        
        try:
            phase_history = project_data.get("phase_history", [])
            if not isinstance(phase_history, list) or not phase_history:
                return alerts
            
            # 現在フェーズの開始時期を計算
            current_phase = self.lifecycle_manager.get_current_phase(project_id)
            current_phase_start = None
            
            for entry in reversed(phase_history):
                if isinstance(entry, dict) and entry.get("to_phase") == current_phase.value:
                    current_phase_start = entry.get("timestamp")
                    break
            
            if current_phase_start:
                start_date = datetime.fromisoformat(current_phase_start.replace('Z', '+00:00'))
                days_in_phase = (datetime.utcnow() - start_date).days
                
                if days_in_phase > self.monitoring_config["phase_delay_threshold_days"]:
                    alerts.append(ProgressAlert(
                        id=f"{project_id}_phase_delay_{int(datetime.now().timestamp())}",
                        project_id=project_id,
                        metric=MonitoringMetric.PHASE_DELAY,
                        level=AlertLevel.WARNING,
                        title=f"{current_phase.value}フェーズが長期化しています",
                        description=f"現在のフェーズに{days_in_phase}日間滞在しています",
                        impact="プロジェクト全体のスケジュールに影響する可能性があります",
                        recommendations=[
                            "フェーズ進行要件を確認する",
                            "ブロッカーを特定・解決する",
                            "スコープの見直しを検討する"
                        ],
                        created_at=datetime.utcnow().isoformat(),
                        data={"days_in_phase": days_in_phase, "current_phase": current_phase.value}
                    ))
                    
        except Exception as e:
            logger.error("Error checking phase delay for project %s: %s", project_id, str(e))
        
        return alerts
    
    def _check_completion_rate(self, project_id: str, project_data: Dict[str, Any]) -> List[ProgressAlert]:
        """完了率のチェック"""
        alerts = []
        
        try:
            tasks = project_data.get("tasks", [])
            if not isinstance(tasks, list) or not tasks:
                return alerts
            
            total_tasks = len(tasks)
            completed_tasks = sum(1 for task in tasks 
                                if isinstance(task, dict) and 
                                task.get("status") in ["completed", "完了", "COMPLETED"])
            
            completion_rate = completed_tasks / total_tasks if total_tasks > 0 else 0
            
            if completion_rate < self.monitoring_config["completion_rate_threshold"]:
                level = AlertLevel.CRITICAL if completion_rate < 0.1 else AlertLevel.WARNING
                
                alerts.append(ProgressAlert(
                    id=f"{project_id}_completion_rate_{int(datetime.now().timestamp())}",
                    project_id=project_id,
                    metric=MonitoringMetric.COMPLETION_RATE,
                    level=level,
                    title=f"タスク完了率が低い状態です ({completion_rate:.1%})",
                    description=f"{total_tasks}タスク中{completed_tasks}タスクのみ完了",
                    impact="プロジェクトの進捗が予定より遅れています",
                    recommendations=[
                        "未完了タスクの状況を確認する",
                        "優先度の高いタスクに集中する",
                        "チームの作業効率を向上させる",
                        "外部支援の検討"
                    ],
                    created_at=datetime.utcnow().isoformat(),
                    data={
                        "completion_rate": completion_rate,
                        "total_tasks": total_tasks,
                        "completed_tasks": completed_tasks
                    }
                ))
                
        except Exception as e:
            logger.error("Error checking completion rate for project %s: %s", project_id, str(e))
        
        return alerts
    
    def _check_blocker_duration(self, project_id: str, project_data: Dict[str, Any]) -> List[ProgressAlert]:
        """ブロッカー継続期間のチェック"""
        alerts = []
        
        try:
            blocking_issues = project_data.get("blocking_issues", [])
            if not isinstance(blocking_issues, list):
                return alerts
            
            long_duration_blockers = []
            threshold_date = datetime.utcnow() - timedelta(
                days=self.monitoring_config["blocker_duration_threshold_days"]
            )
            
            for issue in blocking_issues:
                if not isinstance(issue, dict):
                    continue
                    
                if issue.get("status") != "active":
                    continue
                    
                identified_at_str = issue.get("identified_at")
                if identified_at_str:
                    try:
                        identified_at = datetime.fromisoformat(identified_at_str.replace('Z', '+00:00'))
                        if identified_at < threshold_date:
                            duration_days = (datetime.utcnow() - identified_at).days
                            long_duration_blockers.append({
                                "issue": issue,
                                "duration_days": duration_days
                            })
                    except ValueError:
                        continue
            
            if long_duration_blockers:
                alerts.append(ProgressAlert(
                    id=f"{project_id}_blocker_duration_{int(datetime.now().timestamp())}",
                    project_id=project_id,
                    metric=MonitoringMetric.BLOCKER_DURATION,
                    level=AlertLevel.CRITICAL,
                    title=f"長期間継続しているブロッカーが{len(long_duration_blockers)}件あります",
                    description="解決されていないブロッカーがプロジェクトを阻害しています",
                    impact="プロジェクトの進行が大幅に遅延する可能性があります",
                    recommendations=[
                        "ブロッカーの根本原因を分析する",
                        "エスカレーションを検討する",
                        "代替手段を模索する",
                        "外部リソースの活用を検討する"
                    ],
                    created_at=datetime.utcnow().isoformat(),
                    data={"long_duration_blockers": long_duration_blockers}
                ))
                
        except Exception as e:
            logger.error("Error checking blocker duration for project %s: %s", project_id, str(e))
        
        return alerts
    
    def _check_activity_stagnation(self, project_id: str, project_data: Dict[str, Any]) -> List[ProgressAlert]:
        """活動停滞のチェック"""
        alerts = []
        
        try:
            updated_at_str = project_data.get("updated_at")
            if not updated_at_str:
                return alerts
            
            updated_at = datetime.fromisoformat(updated_at_str.replace('Z', '+00:00'))
            days_since_update = (datetime.utcnow() - updated_at).days
            
            if days_since_update > self.monitoring_config["activity_stagnation_threshold_days"]:
                level = AlertLevel.CRITICAL if days_since_update > 10 else AlertLevel.WARNING
                
                alerts.append(ProgressAlert(
                    id=f"{project_id}_activity_stagnation_{int(datetime.now().timestamp())}",
                    project_id=project_id,
                    metric=MonitoringMetric.ACTIVITY_STAGNATION,
                    level=level,
                    title=f"プロジェクト活動が{days_since_update}日間停滞しています",
                    description="最近のプロジェクト更新が確認されていません",
                    impact="プロジェクトが放置状態になっている可能性があります",
                    recommendations=[
                        "プロジェクトの現状を確認する",
                        "チームメンバーとの連絡を取る",
                        "定期的な進捗報告を設定する",
                        "プロジェクトの優先度を見直す"
                    ],
                    created_at=datetime.utcnow().isoformat(),
                    data={"days_since_update": days_since_update, "last_updated": updated_at_str}
                ))
                
        except Exception as e:
            logger.error("Error checking activity stagnation for project %s: %s", project_id, str(e))
        
        return alerts
    
    def _generate_task_summary(self, project_data: Dict[str, Any]) -> Dict[str, int]:
        """タスクサマリーを生成"""
        tasks = project_data.get("tasks", [])
        if not isinstance(tasks, list):
            return {"total": 0, "completed": 0, "pending": 0, "overdue": 0}
        
        summary = {"total": 0, "completed": 0, "pending": 0, "overdue": 0}
        today = datetime.now().date()
        
        for task in tasks:
            if not isinstance(task, dict):
                continue
                
            summary["total"] += 1
            status = task.get("status", "")
            
            if status in ["completed", "完了", "COMPLETED"]:
                summary["completed"] += 1
            else:
                summary["pending"] += 1
                
                # 遅延チェック
                due_date_str = task.get("due_date")
                if due_date_str:
                    try:
                        due_date = datetime.strptime(due_date_str, "%Y-%m-%d").date()
                        if today > due_date:
                            summary["overdue"] += 1
                    except ValueError:
                        pass
        
        return summary
    
    def _calculate_metrics(self, project_data: Dict[str, Any], alerts: List[ProgressAlert]) -> Dict[str, Any]:
        """メトリクスを計算"""
        task_summary = self._generate_task_summary(project_data)
        
        metrics = {
            "task_completion_rate": task_summary["completed"] / max(task_summary["total"], 1),
            "task_overdue_rate": task_summary["overdue"] / max(task_summary["total"], 1),
            "alert_count_by_level": {
                "critical": len([a for a in alerts if a.level == AlertLevel.CRITICAL]),
                "warning": len([a for a in alerts if a.level == AlertLevel.WARNING]),
                "info": len([a for a in alerts if a.level == AlertLevel.INFO])
            },
            "total_alerts": len(alerts),
            "risk_score": self._calculate_risk_score(task_summary, alerts)
        }
        
        return metrics
    
    def _calculate_risk_score(self, task_summary: Dict[str, int], alerts: List[ProgressAlert]) -> float:
        """リスクスコア計算 (0.0-1.0)"""
        score = 0.0
        
        # タスク遅延によるリスク
        if task_summary["total"] > 0:
            overdue_rate = task_summary["overdue"] / task_summary["total"]
            score += overdue_rate * 0.4
        
        # アラートによるリスク
        critical_alerts = len([a for a in alerts if a.level == AlertLevel.CRITICAL])
        warning_alerts = len([a for a in alerts if a.level == AlertLevel.WARNING])
        
        score += min(critical_alerts * 0.3, 0.3)
        score += min(warning_alerts * 0.1, 0.3)
        
        return min(score, 1.0)
    
    def _generate_predictions(self, project_data: Dict[str, Any], metrics: Dict[str, Any]) -> Dict[str, Any]:
        """完了予測を生成"""
        predictions = {}
        
        try:
            task_summary = self._generate_task_summary(project_data)
            completion_rate = metrics.get("task_completion_rate", 0)
            
            if completion_rate > 0 and task_summary["total"] > 0:
                remaining_tasks = task_summary["total"] - task_summary["completed"]
                
                # 簡易的な完了予測（過去の進捗から推定）
                updated_at_str = project_data.get("updated_at")
                created_at_str = project_data.get("created_at")
                
                if updated_at_str and created_at_str:
                    updated_at = datetime.fromisoformat(updated_at_str.replace('Z', '+00:00'))
                    created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                    
                    elapsed_days = (updated_at - created_at).days
                    
                    if elapsed_days > 0:
                        avg_tasks_per_day = task_summary["completed"] / elapsed_days
                        if avg_tasks_per_day > 0:
                            estimated_days_remaining = remaining_tasks / avg_tasks_per_day
                            estimated_completion_date = datetime.now() + timedelta(days=estimated_days_remaining)
                            
                            predictions = {
                                "estimated_completion_date": estimated_completion_date.isoformat(),
                                "estimated_days_remaining": int(estimated_days_remaining),
                                "confidence": "low" if remaining_tasks > task_summary["completed"] else "medium"
                            }
                            
        except Exception as e:
            logger.error("Error generating predictions: %s", str(e))
        
        return predictions
    
    def _assess_overall_health(self, metrics: Dict[str, Any], alerts: List[ProgressAlert]) -> str:
        """全体的な健康状態を評価"""
        
        completion_rate = metrics.get("task_completion_rate", 0)
        overdue_rate = metrics.get("task_overdue_rate", 0)
        critical_alerts = metrics.get("alert_count_by_level", {}).get("critical", 0)
        risk_score = metrics.get("risk_score", 0)
        
        # 健康状態判定ロジック
        if risk_score > 0.7 or critical_alerts > 2:
            return "critical"
        elif risk_score > 0.4 or critical_alerts > 0 or overdue_rate > 0.2:
            return "at_risk"
        elif completion_rate > 0.7 and overdue_rate < 0.1:
            return "healthy"
        else:
            return "at_risk"
    
    def get_project_health_summary(self) -> Dict[str, Any]:
        """全プロジェクトの健康状態サマリーを取得"""
        
        reports = self.monitor_all_projects()
        
        summary = {
            "total_projects": len(reports),
            "health_distribution": {"healthy": 0, "at_risk": 0, "critical": 0},
            "total_alerts": 0,
            "critical_alerts": 0,
            "projects_needing_attention": []
        }
        
        for project_id, report in reports.items():
            summary["health_distribution"][report.overall_health] += 1
            summary["total_alerts"] += len(report.alerts)
            summary["critical_alerts"] += len([a for a in report.alerts if a.level == AlertLevel.CRITICAL])
            
            if report.overall_health in ["at_risk", "critical"]:
                summary["projects_needing_attention"].append({
                    "project_id": project_id,
                    "health": report.overall_health,
                    "alert_count": len(report.alerts)
                })
        
        return summary