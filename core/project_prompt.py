"""
project_prompt.py - Generate project-specific context for system prompts
"""

import json
from pathlib import Path
from typing import Optional
from .models import DEFAULT_UNDEF


def get_project_prompt(project_id: str) -> str:
    """
    Generate project-specific context prompt including overview, status, and top 3 incomplete tasks.
    
    Args:
        project_id: The project identifier
        
    Returns:
        Markdown-formatted project context string
    """
    projects_dir = Path("data/projects")
    project_file = projects_dir / f"{project_id}.json"
    
    if not project_file.exists():
        return f"❌ プロジェクト {project_id} が見つかりません。"
    
    try:
        with open(project_file, 'r', encoding='utf-8') as f:
            project_data = json.load(f)
        
        # Extract basic project info
        overview = project_data.get("overview", "概要が設定されていません")
        status = project_data.get("status", "DRAFT")
        identifier = project_data.get("identifier", project_id)
        
        # Build the context prompt
        context_lines = [
            "# 📋 現在のプロジェクトコンテキスト",
            "",
            f"**プロジェクト ID**: {identifier}",
            f"**概要**: {overview}",
            f"**ステータス**: {status}",
        ]
        
        # Add task information if available
        tasks = project_data.get("tasks", [])
        if tasks:
            # Filter incomplete tasks (not completed)
            incomplete_tasks = [
                task for task in tasks 
                if task.get("status", DEFAULT_UNDEF) not in ["完了", "COMPLETED", "完了済み"]
            ]
            
            context_lines.extend([
                "",
                "## 🔲 未完了タスク (上位3件)",
                ""
            ])
            
            if incomplete_tasks:
                # Show top 3 incomplete tasks
                for i, task in enumerate(incomplete_tasks[:3], 1):
                    task_id = task.get("id", "不明")
                    description = task.get("description", "説明なし")
                    due_date = task.get("due_date", "期日未設定")
                    owner = task.get("owner", DEFAULT_UNDEF)
                    
                    # Format owner display
                    owner_display = f" (担当: {owner})" if owner != DEFAULT_UNDEF else ""
                    
                    context_lines.append(f"{i}. **[{task_id}]** {description} (期日: {due_date}){owner_display}")
                
                if len(incomplete_tasks) > 3:
                    context_lines.append(f"... 他 {len(incomplete_tasks) - 3} 件の未完了タスク")
            else:
                context_lines.append("すべてのタスクが完了しています。")
        else:
            context_lines.extend([
                "",
                "## 🔲 タスク",
                "",
                "まだタスクが作成されていません。"
            ])
        
        # Add additional context if available
        repository_url = project_data.get("repository_url")
        if repository_url:
            context_lines.extend([
                "",
                f"**リポジトリ**: {repository_url}"
            ])
        
        due_date = project_data.get("due_date")
        if due_date:
            context_lines.extend([
                f"**プロジェクト期日**: {due_date}"
            ])
        
        budget = project_data.get("budget")
        if budget and budget != DEFAULT_UNDEF:
            context_lines.extend([
                f"**予算**: {budget}"
            ])
        
        context_lines.extend([
            "",
            "---",
            "",
            "このプロジェクトコンテキストを念頭に置いて、ユーザーの質問や要求に応答してください。",
            "タスクの追加、更新、プロジェクト情報の変更など、プロジェクト管理に関する支援を提供してください。"
        ])
        
        return "\n".join(context_lines)
        
    except Exception as e:
        return f"❌ プロジェクト {project_id} の読み込み中にエラーが発生しました: {str(e)}"


def get_available_project_ids() -> list[str]:
    """
    Get list of available project IDs from the projects directory.
    
    Returns:
        List of project identifiers
    """
    projects_dir = Path("data/projects")
    
    if not projects_dir.exists():
        return []
    
    project_files = list(projects_dir.glob("*.json"))
    project_ids = [file.stem for file in project_files]
    
    # Sort by modification time (most recent first)
    project_files_with_time = [(file, file.stat().st_mtime) for file in project_files]
    project_files_with_time.sort(key=lambda x: x[1], reverse=True)
    
    return [file[0].stem for file in project_files_with_time]


def get_project_summary(project_id: str) -> Optional[str]:
    """
    Get a brief summary of a project for display in selector.
    
    Args:
        project_id: The project identifier
        
    Returns:
        Brief project summary or None if project not found
    """
    projects_dir = Path("data/projects")
    project_file = projects_dir / f"{project_id}.json"
    
    if not project_file.exists():
        return None
    
    try:
        with open(project_file, 'r', encoding='utf-8') as f:
            project_data = json.load(f)
        
        overview = project_data.get("overview", "概要なし")
        status = project_data.get("status", "DRAFT")
        
        # Truncate overview if too long
        if len(overview) > 50:
            overview = overview[:47] + "..."
        
        return f"{project_id} ({status}) - {overview}"
        
    except Exception:
        return f"{project_id} (読み込みエラー)"