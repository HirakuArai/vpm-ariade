# --- core/schedule_manager.py ---
"""
ScheduleManager - 統合スケジュール管理システム
"""

import json
import logging
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import calendar

from .models import ProjectPhase, DEFAULT_UNDEF
from .project_service import get_project, update_project_field, list_projects
from .lifecycle_manager import ProjectLifecycleManager

logger = logging.getLogger(__name__)

class TaskPriority(Enum):
    """タスク優先度"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"

class ResourceType(Enum):
    """リソースタイプ"""
    HUMAN = "human"
    EQUIPMENT = "equipment"
    BUDGET = "budget"
    TIME = "time"

@dataclass
class ScheduleEvent:
    """スケジュールイベント"""
    id: str
    project_id: str
    title: str
    description: str
    start_date: str
    end_date: str
    event_type: str  # "task", "milestone", "meeting", "deadline"
    priority: TaskPriority
    assigned_to: List[str]
    resources_required: Dict[str, Any]
    dependencies: List[str]
    completion_percentage: float = 0.0
    status: str = "planned"  # planned, in_progress, completed, cancelled

@dataclass
class ResourceAllocation:
    """リソース配分"""
    resource_id: str
    resource_type: ResourceType
    allocated_amount: float
    available_amount: float
    allocation_date: str
    project_id: str
    task_id: Optional[str] = None

@dataclass
class ScheduleConflict:
    """スケジュール競合"""
    id: str
    conflict_type: str  # "resource", "deadline", "dependency"
    affected_projects: List[str]
    affected_tasks: List[str]
    severity: str  # "low", "medium", "high"
    description: str
    suggestions: List[str]
    detected_at: str

@dataclass
class ScheduleRecommendation:
    """スケジュール推奨事項"""
    id: str
    project_id: str
    recommendation_type: str
    title: str
    description: str
    impact: str
    priority: int
    suggested_actions: List[str]
    generated_at: str

class ScheduleManager:
    """統合スケジュール管理システム"""
    
    def __init__(self, projects_dir: Path | None = None):
        self.projects_dir = projects_dir
        self.lifecycle_manager = ProjectLifecycleManager(projects_dir)
        
        # スケジュール設定
        self.schedule_config = {
            "work_days_per_week": 5,
            "work_hours_per_day": 8,
            "buffer_percentage": 0.2,  # スケジュールバッファ
            "critical_path_threshold": 0.8,  # クリティカルパス閾値
            "resource_utilization_max": 0.9,  # 最大リソース利用率
            "reminder_days_before_deadline": [7, 3, 1]  # リマインダー日数
        }
        
        # リソース管理
        self.resources = {
            "human_resources": {},
            "equipment": {},
            "budget_pools": {}
        }
        
        # データファイルパス
        self.schedule_data_dir = Path("data/schedules")
        self.schedule_data_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_project_schedule(self, project_id: str, start_date: Optional[str] = None) -> Dict[str, Any]:
        """プロジェクトスケジュールを生成"""
        
        try:
            project_data = get_project(project_id, self.projects_dir)
            if not project_data:
                raise ValueError(f"Project {project_id} not found")
            
            if not start_date:
                start_date = datetime.now().strftime("%Y-%m-%d")
            
            # タスクを取得・分析
            tasks = project_data.get("tasks", [])
            if not isinstance(tasks, list):
                tasks = []
            
            # スケジュールイベントに変換
            events = self._convert_tasks_to_events(project_id, tasks, start_date)
            
            # 依存関係を解析
            events = self._analyze_dependencies(events)
            
            # クリティカルパスを計算
            critical_path = self._calculate_critical_path(events)
            
            # リソース配分を最適化
            resource_allocation = self._optimize_resource_allocation(project_id, events)
            
            # マイルストーンを生成
            milestones = self._generate_milestones(project_id, events)
            
            # 完了予定日を計算
            estimated_completion = self._calculate_completion_date(events)
            
            # JSON serializable な形式でeventsを変換
            serializable_events = []
            for event in events:
                event_dict = asdict(event)
                # Enum を文字列に変換
                event_dict["priority"] = event.priority.value
                serializable_events.append(event_dict)
            
            schedule = {
                "project_id": project_id,
                "generated_at": datetime.utcnow().isoformat(),
                "start_date": start_date,
                "estimated_completion": estimated_completion,
                "events": serializable_events,
                "critical_path": critical_path,
                "milestones": milestones,
                "resource_allocation": resource_allocation,
                "schedule_metrics": self._calculate_schedule_metrics(events)
            }
            
            # スケジュールを保存
            self._save_schedule(project_id, schedule)
            
            return schedule
            
        except Exception as e:
            logger.error("Error generating schedule for project %s: %s", project_id, str(e))
            raise
    
    def check_schedule_conflicts(self, project_ids: Optional[List[str]] = None) -> List[ScheduleConflict]:
        """スケジュール競合をチェック"""
        
        conflicts = []
        
        try:
            if not project_ids:
                # 全アクティブプロジェクトをチェック
                projects = list_projects(self.projects_dir)
                project_ids = [p["identifier"] for p in projects if p.get("status") == "ACTIVE"]
            
            # 各プロジェクトのスケジュールを取得
            all_schedules = {}
            for project_id in project_ids:
                schedule = self._load_schedule(project_id)
                if schedule:
                    all_schedules[project_id] = schedule
            
            # リソース競合をチェック
            conflicts.extend(self._check_resource_conflicts(all_schedules))
            
            # 期限競合をチェック
            conflicts.extend(self._check_deadline_conflicts(all_schedules))
            
            # 依存関係競合をチェック
            conflicts.extend(self._check_dependency_conflicts(all_schedules))
            
        except Exception as e:
            logger.error("Error checking schedule conflicts: %s", str(e))
        
        return conflicts
    
    def generate_schedule_recommendations(self, project_id: str) -> List[ScheduleRecommendation]:
        """スケジュール推奨事項を生成"""
        
        recommendations = []
        
        try:
            project_data = get_project(project_id, self.projects_dir)
            schedule = self._load_schedule(project_id)
            
            if not project_data or not schedule:
                return recommendations
            
            # タスク優先度の推奨
            recommendations.extend(self._recommend_task_priorities(project_id, project_data, schedule))
            
            # リソース配分の推奨
            recommendations.extend(self._recommend_resource_allocation(project_id, schedule))
            
            # スケジュール最適化の推奨
            recommendations.extend(self._recommend_schedule_optimizations(project_id, schedule))
            
            # リスク軽減の推奨
            recommendations.extend(self._recommend_risk_mitigations(project_id, project_data, schedule))
            
        except Exception as e:
            logger.error("Error generating recommendations for project %s: %s", project_id, str(e))
        
        return recommendations
    
    def get_upcoming_deadlines(self, days_ahead: int = 7) -> List[Dict[str, Any]]:
        """今後の期限を取得"""
        
        deadlines = []
        cutoff_date = (datetime.now() + timedelta(days=days_ahead)).date()
        
        try:
            projects = list_projects(self.projects_dir)
            
            for project in projects:
                if project.get("status") != "ACTIVE":
                    continue
                
                project_id = project.get("identifier")
                schedule = self._load_schedule(project_id)
                
                if not schedule:
                    continue
                
                for event_data in schedule.get("events", []):
                    end_date_str = event_data.get("end_date")
                    if not end_date_str:
                        continue
                    
                    try:
                        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
                        if end_date <= cutoff_date:
                            deadlines.append({
                                "project_id": project_id,
                                "project_name": project.get("overview", project_id),
                                "event_title": event_data.get("title"),
                                "deadline": end_date_str,
                                "days_remaining": (end_date - datetime.now().date()).days,
                                "priority": event_data.get("priority"),
                                "completion_percentage": event_data.get("completion_percentage", 0)
                            })
                    except ValueError:
                        continue
            
            # 期限順にソート
            deadlines.sort(key=lambda x: x["deadline"])
            
        except Exception as e:
            logger.error("Error getting upcoming deadlines: %s", str(e))
        
        return deadlines
    
    def get_resource_utilization(self) -> Dict[str, Any]:
        """リソース利用状況を取得"""
        
        utilization = {
            "human_resources": {},
            "equipment": {},
            "budget": {},
            "overall_utilization": 0.0,
            "bottlenecks": []
        }
        
        try:
            projects = list_projects(self.projects_dir)
            active_projects = [p for p in projects if p.get("status") == "ACTIVE"]
            
            # 各プロジェクトのリソース使用量を集計
            total_allocations = {}
            
            for project in active_projects:
                project_id = project.get("identifier")
                schedule = self._load_schedule(project_id)
                
                if schedule and "resource_allocation" in schedule:
                    for allocation in schedule["resource_allocation"]:
                        resource_id = allocation.get("resource_id")
                        resource_type = allocation.get("resource_type")
                        allocated = allocation.get("allocated_amount", 0)
                        
                        if resource_id not in total_allocations:
                            total_allocations[resource_id] = {
                                "type": resource_type,
                                "allocated": 0,
                                "available": allocation.get("available_amount", 100)
                            }
                        
                        total_allocations[resource_id]["allocated"] += allocated
            
            # 利用率を計算
            for resource_id, data in total_allocations.items():
                utilization_rate = data["allocated"] / max(data["available"], 1)
                
                resource_type = data["type"]
                if resource_type not in utilization:
                    utilization[resource_type] = {}
                
                utilization[resource_type][resource_id] = {
                    "utilization_rate": utilization_rate,
                    "allocated": data["allocated"],
                    "available": data["available"]
                }
                
                # ボトルネックを特定
                if utilization_rate > self.schedule_config["resource_utilization_max"]:
                    utilization["bottlenecks"].append({
                        "resource_id": resource_id,
                        "resource_type": resource_type,
                        "utilization_rate": utilization_rate
                    })
            
            # 全体利用率を計算
            if total_allocations:
                overall_rate = sum(
                    data["allocated"] / max(data["available"], 1) 
                    for data in total_allocations.values()
                ) / len(total_allocations)
                utilization["overall_utilization"] = overall_rate
            
        except Exception as e:
            logger.error("Error calculating resource utilization: %s", str(e))
        
        return utilization
    
    def _convert_tasks_to_events(self, project_id: str, tasks: List[Dict[str, Any]], start_date: str) -> List[ScheduleEvent]:
        """タスクをスケジュールイベントに変換"""
        
        events = []
        current_date = datetime.strptime(start_date, "%Y-%m-%d")
        
        for i, task in enumerate(tasks):
            if not isinstance(task, dict):
                continue
            
            task_id = task.get("id", i + 1)
            description = task.get("description", f"Task {task_id}")
            due_date_str = task.get("due_date")
            
            # 期限が設定されている場合は使用、なければ推定
            if due_date_str:
                try:
                    end_date = datetime.strptime(due_date_str, "%Y-%m-%d")
                except ValueError:
                    end_date = current_date + timedelta(days=7)  # デフォルト1週間
            else:
                end_date = current_date + timedelta(days=7)
            
            # 開始日を推定（終了日の5日前）
            start_date_calc = end_date - timedelta(days=5)
            
            # 優先度を決定
            priority = self._determine_task_priority(task)
            
            event = ScheduleEvent(
                id=f"{project_id}_task_{task_id}",
                project_id=project_id,
                title=description,
                description=description,
                start_date=start_date_calc.strftime("%Y-%m-%d"),
                end_date=end_date.strftime("%Y-%m-%d"),
                event_type="task",
                priority=priority,
                assigned_to=[task.get("owner", "未割当")],
                resources_required={"time": 1.0},
                dependencies=[],
                completion_percentage=self._get_task_completion(task),
                status=self._get_task_status(task)
            )
            
            events.append(event)
            current_date = end_date + timedelta(days=1)
        
        return events
    
    def _determine_task_priority(self, task: Dict[str, Any]) -> TaskPriority:
        """タスクの優先度を決定"""
        
        # 期限ベースの優先度判定
        due_date_str = task.get("due_date")
        if due_date_str:
            try:
                due_date = datetime.strptime(due_date_str, "%Y-%m-%d").date()
                days_until_due = (due_date - datetime.now().date()).days
                
                if days_until_due <= 1:
                    return TaskPriority.URGENT
                elif days_until_due <= 3:
                    return TaskPriority.HIGH
                elif days_until_due <= 7:
                    return TaskPriority.NORMAL
                else:
                    return TaskPriority.LOW
            except ValueError:
                pass
        
        # デフォルトは NORMAL
        return TaskPriority.NORMAL
    
    def _get_task_completion(self, task: Dict[str, Any]) -> float:
        """タスクの完了率を取得"""
        
        status = task.get("status", "")
        if status in ["completed", "完了", "COMPLETED"]:
            return 100.0
        elif status in ["in_progress", "進行中", "IN_PROGRESS"]:
            return 50.0
        else:
            return 0.0
    
    def _get_task_status(self, task: Dict[str, Any]) -> str:
        """タスクのステータスを取得"""
        
        status = task.get("status", "")
        if status in ["completed", "完了", "COMPLETED"]:
            return "completed"
        elif status in ["in_progress", "進行中", "IN_PROGRESS"]:
            return "in_progress"
        else:
            return "planned"
    
    def _analyze_dependencies(self, events: List[ScheduleEvent]) -> List[ScheduleEvent]:
        """依存関係を解析"""
        
        # 簡易的な依存関係解析（実際の実装ではより詳細な分析が必要）
        for i, event in enumerate(events[1:], 1):
            # 前のタスクに依存すると仮定
            event.dependencies = [events[i-1].id]
        
        return events
    
    def _calculate_critical_path(self, events: List[ScheduleEvent]) -> List[str]:
        """クリティカルパスを計算"""
        
        # 簡易的なクリティカルパス計算
        critical_path = []
        
        # 最も期限がタイトなタスクの連鎖を特定
        urgent_events = [e for e in events if e.priority in [TaskPriority.URGENT, TaskPriority.HIGH]]
        
        if urgent_events:
            # 日付順にソートしてクリティカルパスとする
            urgent_events.sort(key=lambda x: x.end_date)
            critical_path = [e.id for e in urgent_events]
        else:
            # 緊急タスクがない場合は依存関係順
            critical_path = [e.id for e in events]
        
        return critical_path
    
    def _optimize_resource_allocation(self, project_id: str, events: List[ScheduleEvent]) -> List[Dict[str, Any]]:
        """リソース配分を最適化"""
        
        allocations = []
        
        for event in events:
            # 基本的なリソース配分
            allocation = {
                "resource_id": f"human_resource_1",
                "resource_type": ResourceType.HUMAN.value,
                "allocated_amount": event.resources_required.get("time", 1.0),
                "available_amount": 8.0,  # 1日8時間
                "allocation_date": event.start_date,
                "project_id": project_id,
                "task_id": event.id
            }
            allocations.append(allocation)
        
        return allocations
    
    def _generate_milestones(self, project_id: str, events: List[ScheduleEvent]) -> List[Dict[str, Any]]:
        """マイルストーンを生成"""
        
        milestones = []
        
        # イベントを4分割してマイルストーンを作成
        if events:
            total_events = len(events)
            milestone_intervals = [total_events // 4, total_events // 2, (total_events * 3) // 4, total_events - 1]
            
            for i, interval in enumerate(milestone_intervals):
                if interval < len(events):
                    event = events[interval]
                    milestone = {
                        "id": f"{project_id}_milestone_{i+1}",
                        "title": f"マイルストーン {i+1}",
                        "date": event.end_date,
                        "description": f"プロジェクトの{25*(i+1)}%完了時点",
                        "target_completion": 25 * (i + 1)
                    }
                    milestones.append(milestone)
        
        return milestones
    
    def _calculate_completion_date(self, events: List[ScheduleEvent]) -> Optional[str]:
        """完了予定日を計算"""
        
        if not events:
            return None
        
        # 最後のイベントの終了日を完了予定日とする
        latest_end_date = max(events, key=lambda x: x.end_date).end_date
        
        # バッファを追加
        completion_date = datetime.strptime(latest_end_date, "%Y-%m-%d")
        buffer_days = int((completion_date - datetime.now()).days * self.schedule_config["buffer_percentage"])
        completion_date += timedelta(days=buffer_days)
        
        return completion_date.strftime("%Y-%m-%d")
    
    def _calculate_schedule_metrics(self, events: List[ScheduleEvent]) -> Dict[str, Any]:
        """スケジュールメトリクスを計算"""
        
        if not events:
            return {}
        
        total_events = len(events)
        completed_events = len([e for e in events if e.status == "completed"])
        in_progress_events = len([e for e in events if e.status == "in_progress"])
        
        total_duration = 0
        if events:
            start_dates = [datetime.strptime(e.start_date, "%Y-%m-%d") for e in events]
            end_dates = [datetime.strptime(e.end_date, "%Y-%m-%d") for e in events]
            total_duration = (max(end_dates) - min(start_dates)).days
        
        return {
            "total_tasks": total_events,
            "completed_tasks": completed_events,
            "in_progress_tasks": in_progress_events,
            "completion_rate": completed_events / max(total_events, 1),
            "total_duration_days": total_duration,
            "average_task_duration": total_duration / max(total_events, 1),
            "urgent_tasks": len([e for e in events if e.priority == TaskPriority.URGENT]),
            "high_priority_tasks": len([e for e in events if e.priority == TaskPriority.HIGH])
        }
    
    def _save_schedule(self, project_id: str, schedule: Dict[str, Any]):
        """スケジュールを保存"""
        
        schedule_file = self.schedule_data_dir / f"{project_id}_schedule.json"
        
        try:
            with open(schedule_file, 'w', encoding='utf-8') as f:
                json.dump(schedule, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error("Error saving schedule for project %s: %s", project_id, str(e))
    
    def _load_schedule(self, project_id: str) -> Optional[Dict[str, Any]]:
        """スケジュールを読み込み"""
        
        schedule_file = self.schedule_data_dir / f"{project_id}_schedule.json"
        
        if not schedule_file.exists():
            return None
        
        try:
            with open(schedule_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error("Error loading schedule for project %s: %s", project_id, str(e))
            return None
    
    def _check_resource_conflicts(self, all_schedules: Dict[str, Dict[str, Any]]) -> List[ScheduleConflict]:
        """リソース競合をチェック"""
        
        conflicts = []
        resource_usage = {}
        
        # 各日のリソース使用量を集計
        for project_id, schedule in all_schedules.items():
            for allocation in schedule.get("resource_allocation", []):
                resource_id = allocation.get("resource_id")
                date = allocation.get("allocation_date")
                amount = allocation.get("allocated_amount", 0)
                
                if date not in resource_usage:
                    resource_usage[date] = {}
                if resource_id not in resource_usage[date]:
                    resource_usage[date][resource_id] = {"total": 0, "projects": []}
                
                resource_usage[date][resource_id]["total"] += amount
                resource_usage[date][resource_id]["projects"].append(project_id)
        
        # 競合を検出
        for date, resources in resource_usage.items():
            for resource_id, usage in resources.items():
                if usage["total"] > 8.0:  # 1日8時間を超える場合
                    conflict = ScheduleConflict(
                        id=f"resource_conflict_{resource_id}_{date}",
                        conflict_type="resource",
                        affected_projects=usage["projects"],
                        affected_tasks=[],
                        severity="high" if usage["total"] > 12.0 else "medium",
                        description=f"リソース {resource_id} が {date} に過剰配分されています ({usage['total']:.1f}時間)",
                        suggestions=[
                            "タスクの実行時期を調整する",
                            "追加リソースを確保する",
                            "タスクの優先度を見直す"
                        ],
                        detected_at=datetime.utcnow().isoformat()
                    )
                    conflicts.append(conflict)
        
        return conflicts
    
    def _check_deadline_conflicts(self, all_schedules: Dict[str, Dict[str, Any]]) -> List[ScheduleConflict]:
        """期限競合をチェック"""
        
        conflicts = []
        
        # 同じ日に複数の重要な期限がある場合を検出
        deadline_dates = {}
        
        for project_id, schedule in all_schedules.items():
            for event_data in schedule.get("events", []):
                if event_data.get("priority") in ["urgent", "high"]:
                    end_date = event_data.get("end_date")
                    if end_date:
                        if end_date not in deadline_dates:
                            deadline_dates[end_date] = []
                        deadline_dates[end_date].append({
                            "project_id": project_id,
                            "event": event_data
                        })
        
        for date, items in deadline_dates.items():
            if len(items) > 2:  # 3つ以上の重要な期限が同じ日
                conflict = ScheduleConflict(
                    id=f"deadline_conflict_{date}",
                    conflict_type="deadline",
                    affected_projects=[item["project_id"] for item in items],
                    affected_tasks=[item["event"]["id"] for item in items],
                    severity="high",
                    description=f"{date} に {len(items)}個の重要な期限が集中しています",
                    suggestions=[
                        "期限を分散させる",
                        "優先度を再評価する",
                        "リソースを集中投入する"
                    ],
                    detected_at=datetime.utcnow().isoformat()
                )
                conflicts.append(conflict)
        
        return conflicts
    
    def _check_dependency_conflicts(self, all_schedules: Dict[str, Dict[str, Any]]) -> List[ScheduleConflict]:
        """依存関係競合をチェック"""
        
        # 簡易実装：実際にはより複雑な依存関係解析が必要
        return []
    
    def _recommend_task_priorities(self, project_id: str, project_data: Dict[str, Any], 
                                 schedule: Dict[str, Any]) -> List[ScheduleRecommendation]:
        """タスク優先度の推奨"""
        
        recommendations = []
        
        # 期限が近いのに優先度が低いタスクを特定
        events = schedule.get("events", [])
        today = datetime.now().date()
        
        for event_data in events:
            end_date_str = event_data.get("end_date")
            priority = event_data.get("priority", "normal")
            
            if end_date_str:
                try:
                    end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
                    days_until_due = (end_date - today).days
                    
                    if days_until_due <= 3 and priority in ["low", "normal"]:
                        recommendation = ScheduleRecommendation(
                            id=f"{project_id}_priority_rec_{int(datetime.now().timestamp())}",
                            project_id=project_id,
                            recommendation_type="task_priority",
                            title=f"タスク「{event_data.get('title')}」の優先度を上げることを推奨",
                            description=f"期限まで{days_until_due}日しかないのに優先度が{priority}です",
                            impact="期限遅れのリスクを軽減",
                            priority=80,
                            suggested_actions=[
                                "タスクの優先度を HIGH または URGENT に変更",
                                "リソース配分を見直し",
                                "他のタスクとの調整"
                            ],
                            generated_at=datetime.utcnow().isoformat()
                        )
                        recommendations.append(recommendation)
                        
                except ValueError:
                    continue
        
        return recommendations
    
    def _recommend_resource_allocation(self, project_id: str, schedule: Dict[str, Any]) -> List[ScheduleRecommendation]:
        """リソース配分の推奨"""
        
        recommendations = []
        
        # リソース利用率が高い日を特定
        resource_utilization = {}
        for allocation in schedule.get("resource_allocation", []):
            date = allocation.get("allocation_date")
            amount = allocation.get("allocated_amount", 0)
            
            if date not in resource_utilization:
                resource_utilization[date] = 0
            resource_utilization[date] += amount
        
        for date, total_hours in resource_utilization.items():
            if total_hours > 8:  # 8時間を超える場合
                recommendation = ScheduleRecommendation(
                    id=f"{project_id}_resource_rec_{date}",
                    project_id=project_id,
                    recommendation_type="resource_allocation",
                    title=f"{date} のリソース過剰配分を調整することを推奨",
                    description=f"{total_hours:.1f}時間の作業が予定されており、実行可能性に問題があります",
                    impact="作業効率の向上と品質確保",
                    priority=70,
                    suggested_actions=[
                        "タスクを他の日に分散",
                        "追加リソースの確保",
                        "タスクの簡素化や分割"
                    ],
                    generated_at=datetime.utcnow().isoformat()
                )
                recommendations.append(recommendation)
        
        return recommendations
    
    def _recommend_schedule_optimizations(self, project_id: str, schedule: Dict[str, Any]) -> List[ScheduleRecommendation]:
        """スケジュール最適化の推奨"""
        
        recommendations = []
        
        metrics = schedule.get("schedule_metrics", {})
        completion_rate = metrics.get("completion_rate", 0)
        
        if completion_rate < 0.3:
            recommendation = ScheduleRecommendation(
                id=f"{project_id}_optimization_completion",
                project_id=project_id,
                recommendation_type="schedule_optimization",
                title="タスク完了率が低いため、スケジュール見直しを推奨",
                description=f"現在の完了率は{completion_rate:.1%}で、計画に対して遅れています",
                impact="プロジェクト成功率の向上",
                priority=90,
                suggested_actions=[
                    "未完了タスクの詳細分析",
                    "ブロッカーの特定と解決",
                    "リソース追加の検討",
                    "スコープの調整"
                ],
                generated_at=datetime.utcnow().isoformat()
            )
            recommendations.append(recommendation)
        
        return recommendations
    
    def _recommend_risk_mitigations(self, project_id: str, project_data: Dict[str, Any], 
                                  schedule: Dict[str, Any]) -> List[ScheduleRecommendation]:
        """リスク軽減の推奨"""
        
        recommendations = []
        
        # ブロッキング課題がある場合
        blocking_issues = project_data.get("blocking_issues", [])
        if isinstance(blocking_issues, list) and blocking_issues:
            active_blockers = [issue for issue in blocking_issues 
                             if isinstance(issue, dict) and issue.get("status") == "active"]
            
            if active_blockers:
                recommendation = ScheduleRecommendation(
                    id=f"{project_id}_risk_blockers",
                    project_id=project_id,
                    recommendation_type="risk_mitigation",
                    title=f"{len(active_blockers)}件のアクティブなブロッカーの解決を推奨",
                    description="未解決のブロッカーがプロジェクトの進行を阻害しています",
                    impact="プロジェクト遅延リスクの軽減",
                    priority=95,
                    suggested_actions=[
                        "各ブロッカーの解決策を明確化",
                        "担当者と期限を設定",
                        "エスカレーション計画の策定",
                        "代替案の検討"
                    ],
                    generated_at=datetime.utcnow().isoformat()
                )
                recommendations.append(recommendation)
        
        return recommendations