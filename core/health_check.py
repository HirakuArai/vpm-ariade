# --- core/health_check.py ---
"""
Health Check System - システム健康状態監視
"""

import json
import logging
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import psutil
import yaml

logger = logging.getLogger(__name__)

@dataclass
class HealthStatus:
    """健康状態"""
    component: str
    status: str  # "healthy", "degraded", "unhealthy"
    message: str
    details: Dict[str, Any]
    checked_at: str

@dataclass
class SystemHealth:
    """システム全体の健康状態"""
    overall_status: str
    components: List[HealthStatus]
    metrics: Dict[str, Any]
    generated_at: str

class HealthChecker:
    """システム健康状態チェッカー"""
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or Path("config/production.yml")
        self.config = self._load_config()
        
        # 健康状態チェック設定
        self.thresholds = {
            "cpu_percent": 80.0,
            "memory_percent": 85.0,
            "disk_percent": 90.0,
            "response_time_ms": 5000,
            "error_rate_percent": 5.0
        }
        
        # メトリクス履歴
        self.metrics_history = []
        self.max_history_size = 100
    
    def _load_config(self) -> Dict[str, Any]:
        """設定ファイルを読み込み"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Config loading failed: {str(e)}")
        
        return {}
    
    def check_system_health(self) -> SystemHealth:
        """システム全体の健康状態をチェック"""
        
        components = []
        overall_status = "healthy"
        
        # 各コンポーネントをチェック
        components.append(self._check_system_resources())
        components.append(self._check_file_system())
        components.append(self._check_openai_connection())
        components.append(self._check_data_integrity())
        components.append(self._check_automation_systems())
        
        # 全体ステータスを決定
        for component in components:
            if component.status == "unhealthy":
                overall_status = "unhealthy"
                break
            elif component.status == "degraded" and overall_status == "healthy":
                overall_status = "degraded"
        
        # システムメトリクスを計算
        metrics = self._calculate_system_metrics()
        
        health = SystemHealth(
            overall_status=overall_status,
            components=components,
            metrics=metrics,
            generated_at=datetime.utcnow().isoformat()
        )
        
        # 履歴に追加
        self._add_to_history(health)
        
        return health
    
    def _check_system_resources(self) -> HealthStatus:
        """システムリソースをチェック"""
        
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # メモリ使用率
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # ディスク使用率
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            
            details = {
                "cpu_percent": cpu_percent,
                "memory_percent": memory_percent,
                "disk_percent": disk_percent,
                "memory_available_gb": memory.available / (1024**3),
                "disk_free_gb": disk.free / (1024**3)
            }
            
            # ステータス判定
            status = "healthy"
            messages = []
            
            if cpu_percent > self.thresholds["cpu_percent"]:
                status = "degraded" if cpu_percent < 95 else "unhealthy"
                messages.append(f"CPU使用率が高い: {cpu_percent:.1f}%")
            
            if memory_percent > self.thresholds["memory_percent"]:
                status = "degraded" if memory_percent < 95 else "unhealthy"
                messages.append(f"メモリ使用率が高い: {memory_percent:.1f}%")
            
            if disk_percent > self.thresholds["disk_percent"]:
                status = "unhealthy"
                messages.append(f"ディスク使用率が高い: {disk_percent:.1f}%")
            
            message = "; ".join(messages) if messages else "システムリソースは正常です"
            
            return HealthStatus(
                component="system_resources",
                status=status,
                message=message,
                details=details,
                checked_at=datetime.utcnow().isoformat()
            )
            
        except Exception as e:
            return HealthStatus(
                component="system_resources",
                status="unhealthy",
                message=f"リソースチェックエラー: {str(e)}",
                details={"error": str(e)},
                checked_at=datetime.utcnow().isoformat()
            )
    
    def _check_file_system(self) -> HealthStatus:
        """ファイルシステムをチェック"""
        
        try:
            # 重要なディレクトリの存在確認
            required_dirs = [
                Path("data"),
                Path("data/projects"),
                Path("data/schedules"),
                Path("logs"),
                Path("config")
            ]
            
            missing_dirs = []
            for dir_path in required_dirs:
                if not dir_path.exists():
                    missing_dirs.append(str(dir_path))
                    try:
                        dir_path.mkdir(parents=True, exist_ok=True)
                    except Exception:
                        pass
            
            # ファイル権限チェック
            writable_dirs = [Path("data"), Path("logs")]
            permission_issues = []
            
            for dir_path in writable_dirs:
                if dir_path.exists() and not os.access(dir_path, os.W_OK):
                    permission_issues.append(str(dir_path))
            
            details = {
                "missing_directories": missing_dirs,
                "permission_issues": permission_issues,
                "data_directory_size_mb": self._get_directory_size(Path("data")) / (1024**2)
            }
            
            # ステータス判定
            if permission_issues:
                status = "unhealthy"
                message = f"ファイル権限エラー: {', '.join(permission_issues)}"
            elif missing_dirs:
                status = "degraded"
                message = f"ディレクトリが見つからず作成しました: {', '.join(missing_dirs)}"
            else:
                status = "healthy"
                message = "ファイルシステムは正常です"
            
            return HealthStatus(
                component="file_system",
                status=status,
                message=message,
                details=details,
                checked_at=datetime.utcnow().isoformat()
            )
            
        except Exception as e:
            return HealthStatus(
                component="file_system",
                status="unhealthy",
                message=f"ファイルシステムチェックエラー: {str(e)}",
                details={"error": str(e)},
                checked_at=datetime.utcnow().isoformat()
            )
    
    def _check_openai_connection(self) -> HealthStatus:
        """OpenAI接続をチェック"""
        
        try:
            import openai
            
            # API Key の存在確認
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                return HealthStatus(
                    component="openai_connection",
                    status="unhealthy",
                    message="OpenAI API キーが設定されていません",
                    details={"api_key_configured": False},
                    checked_at=datetime.utcnow().isoformat()
                )
            
            # 簡単な接続テスト（実際のAPIは呼ばない）
            openai.api_key = api_key
            
            details = {
                "api_key_configured": True,
                "api_key_length": len(api_key),
                "last_check": datetime.utcnow().isoformat()
            }
            
            return HealthStatus(
                component="openai_connection",
                status="healthy",
                message="OpenAI設定は正常です",
                details=details,
                checked_at=datetime.utcnow().isoformat()
            )
            
        except Exception as e:
            return HealthStatus(
                component="openai_connection",
                status="degraded",
                message=f"OpenAI設定チェックエラー: {str(e)}",
                details={"error": str(e)},
                checked_at=datetime.utcnow().isoformat()
            )
    
    def _check_data_integrity(self) -> HealthStatus:
        """データ整合性をチェック"""
        
        try:
            # プロジェクトファイルの整合性チェック
            projects_dir = Path("data/projects")
            if not projects_dir.exists():
                return HealthStatus(
                    component="data_integrity",
                    status="unhealthy",
                    message="プロジェクトディレクトリが存在しません",
                    details={"projects_directory_exists": False},
                    checked_at=datetime.utcnow().isoformat()
                )
            
            # JSONファイルの妥当性チェック
            corrupted_files = []
            total_files = 0
            
            for json_file in projects_dir.glob("*.json"):
                total_files += 1
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        json.load(f)
                except (json.JSONDecodeError, Exception):
                    corrupted_files.append(str(json_file.name))
            
            details = {
                "total_project_files": total_files,
                "corrupted_files": corrupted_files,
                "corruption_rate": len(corrupted_files) / max(total_files, 1)
            }
            
            # ステータス判定
            if len(corrupted_files) > 0:
                if len(corrupted_files) / max(total_files, 1) > 0.1:  # 10%以上破損
                    status = "unhealthy"
                    message = f"多数のファイルが破損しています: {len(corrupted_files)}/{total_files}"
                else:
                    status = "degraded"
                    message = f"一部のファイルが破損しています: {', '.join(corrupted_files)}"
            else:
                status = "healthy"
                message = f"データ整合性は正常です ({total_files}ファイル)"
            
            return HealthStatus(
                component="data_integrity",
                status=status,
                message=message,
                details=details,
                checked_at=datetime.utcnow().isoformat()
            )
            
        except Exception as e:
            return HealthStatus(
                component="data_integrity",
                status="unhealthy",
                message=f"データ整合性チェックエラー: {str(e)}",
                details={"error": str(e)},
                checked_at=datetime.utcnow().isoformat()
            )
    
    def _check_automation_systems(self) -> HealthStatus:
        """自動化システムをチェック"""
        
        try:
            # 自動化コンポーネントのインポートテスト
            components_status = {}
            
            try:
                from core.auto_update_engine import AutoUpdateEngine
                components_status["auto_update_engine"] = "available"
            except Exception as e:
                components_status["auto_update_engine"] = f"error: {str(e)}"
            
            try:
                from core.progress_monitor import ProgressMonitor
                components_status["progress_monitor"] = "available"
            except Exception as e:
                components_status["progress_monitor"] = f"error: {str(e)}"
            
            try:
                from core.notification_system import NotificationSystem
                components_status["notification_system"] = "available"
            except Exception as e:
                components_status["notification_system"] = f"error: {str(e)}"
            
            try:
                from core.schedule_manager import ScheduleManager
                components_status["schedule_manager"] = "available"
            except Exception as e:
                components_status["schedule_manager"] = f"error: {str(e)}"
            
            # ステータス判定
            available_count = sum(1 for status in components_status.values() if status == "available")
            total_count = len(components_status)
            
            details = {
                "components": components_status,
                "availability_rate": available_count / total_count
            }
            
            if available_count == total_count:
                status = "healthy"
                message = "全ての自動化システムが利用可能です"
            elif available_count >= total_count * 0.75:
                status = "degraded"
                message = f"一部の自動化システムに問題があります ({available_count}/{total_count})"
            else:
                status = "unhealthy"
                message = f"多くの自動化システムが利用できません ({available_count}/{total_count})"
            
            return HealthStatus(
                component="automation_systems",
                status=status,
                message=message,
                details=details,
                checked_at=datetime.utcnow().isoformat()
            )
            
        except Exception as e:
            return HealthStatus(
                component="automation_systems",
                status="unhealthy",
                message=f"自動化システムチェックエラー: {str(e)}",
                details={"error": str(e)},
                checked_at=datetime.utcnow().isoformat()
            )
    
    def _calculate_system_metrics(self) -> Dict[str, Any]:
        """システムメトリクスを計算"""
        
        try:
            # システム稼働時間
            boot_time = psutil.boot_time()
            uptime_seconds = time.time() - boot_time
            
            # プロセス情報
            current_process = psutil.Process()
            process_memory = current_process.memory_info()
            
            return {
                "uptime_hours": uptime_seconds / 3600,
                "process_memory_mb": process_memory.rss / (1024**2),
                "process_cpu_percent": current_process.cpu_percent(),
                "total_threads": current_process.num_threads(),
                "system_load": os.getloadavg()[0] if hasattr(os, 'getloadavg') else None
            }
            
        except Exception as e:
            logger.error(f"Metrics calculation failed: {str(e)}")
            return {"error": str(e)}
    
    def _get_directory_size(self, directory: Path) -> int:
        """ディレクトリサイズを取得"""
        
        total_size = 0
        try:
            for dirpath, dirnames, filenames in os.walk(directory):
                for filename in filenames:
                    filepath = Path(dirpath) / filename
                    try:
                        total_size += filepath.stat().st_size
                    except (OSError, FileNotFoundError):
                        pass
        except Exception:
            pass
        
        return total_size
    
    def _add_to_history(self, health: SystemHealth):
        """健康状態を履歴に追加"""
        
        self.metrics_history.append({
            "timestamp": health.generated_at,
            "overall_status": health.overall_status,
            "metrics": health.metrics
        })
        
        # 履歴サイズを制限
        if len(self.metrics_history) > self.max_history_size:
            self.metrics_history = self.metrics_history[-self.max_history_size:]
    
    def get_health_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """指定時間内の健康状態履歴を取得"""
        
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        return [
            entry for entry in self.metrics_history
            if datetime.fromisoformat(entry["timestamp"].replace('Z', '+00:00')) > cutoff_time
        ]
    
    def export_health_report(self, filepath: Path):
        """健康状態レポートをファイルに出力"""
        
        try:
            health = self.check_system_health()
            
            report = {
                "report_generated_at": datetime.utcnow().isoformat(),
                "system_health": {
                    "overall_status": health.overall_status,
                    "components": [
                        {
                            "component": comp.component,
                            "status": comp.status,
                            "message": comp.message,
                            "checked_at": comp.checked_at
                        }
                        for comp in health.components
                    ]
                },
                "metrics": health.metrics,
                "history_24h": self.get_health_history(24)
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Health report exported to {filepath}")
            
        except Exception as e:
            logger.error(f"Failed to export health report: {str(e)}")
            raise