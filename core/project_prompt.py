# --- core/project_prompt.py ---
"""
project_prompt.py - Generate project-specific context for system prompts
"""

import json
from pathlib import Path
from typing import Optional
from .models import DEFAULT_UNDEF

PROJECTS_DIR = Path("data/projects")

def get_project_prompt(project_id: str, projects_dir: Path | None = None) -> str:
    """
    Generate project-specific context prompt including overview, status, and top 3 incomplete tasks.
    
    Args:
        project_id: The project identifier
        projects_dir: Directory containing project files (defaults to PROJECTS_DIR)
        
    Returns:
        Markdown-formatted project context string
    """
    if projects_dir is None:
        projects_dir = PROJECTS_DIR
        
    project_file = projects_dir / f"{project_id}.json"
    
    if not project_file.exists():
        return f"❌ プロジェクト {project_id} が見つかりません。"
    
    try:
        with open(project_file, 'r', encoding='utf-8') as f:
            project_data = json.load(f)
        
        # Extract basic project info, filtering undefined fields
        overview = project_data.get("overview", "概要が設定されていません")
        status = project_data.get("status", "DRAFT")
        identifier = project_data.get("identifier", project_id)
        
        # Filter out undefined fields from display
        if overview == DEFAULT_UNDEF:
            overview = "概要が設定されていません"
        if status == DEFAULT_UNDEF:
            status = "DRAFT"
        
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
        
        # Add additional information section if any optional fields are present
        repository_url = project_data.get("repository_url")
        due_date = project_data.get("due_date")
        budget = project_data.get("budget")
        
        additional_info = []
        if repository_url not in [None, DEFAULT_UNDEF, ""]:
            additional_info.append(f"**リポジトリ**: {repository_url}")
        if due_date not in [None, DEFAULT_UNDEF, ""]:
            additional_info.append(f"**プロジェクト期日**: {due_date}")
        if budget not in [None, DEFAULT_UNDEF, ""]:
            additional_info.append(f"**予算**: {budget}")
        
        if additional_info:
            context_lines.extend([
                "",
                "### ℹ️ 追加情報",
                ""
            ])
            context_lines.extend(additional_info)
        
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


def get_available_project_ids(projects_dir: Path | None = None) -> list[str]:
    """
    Get list of available project IDs from the projects directory.
    
    Args:
        projects_dir: Directory containing project files (defaults to PROJECTS_DIR)
    
    Returns:
        List of project identifiers for projects with DRAFT or ACTIVE status, sorted by update time
    """
    projects_dir = projects_dir or PROJECTS_DIR
    if not projects_dir.exists():
        return []
    
    valid_projects = []
    for project_file in projects_dir.glob("*.json"):
        try:
            with open(project_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            status = data.get("status", "DRAFT")
            if status in {"DRAFT", "ACTIVE"}:
                ts = data.get("updated_at") or data.get("created_at") or ""
                valid_projects.append((project_file.stem, ts))
        except Exception:
            # Silently skip files that can't be read
            continue
    
    # Sort by timestamp descending
    valid_projects.sort(key=lambda x: x[1], reverse=True)
    return [project_id for project_id, _ in valid_projects]


def get_project_summary(project_id: str, projects_dir: Path | None = None) -> Optional[str]:
    """
    Get a brief summary of a project for display in selector.
    
    Args:
        project_id: The project identifier
        projects_dir: Directory containing project files (defaults to PROJECTS_DIR)
        
    Returns:
        Brief project summary or None if project not found
    """
    if projects_dir is None:
        projects_dir = PROJECTS_DIR
        
    project_file = projects_dir / f"{project_id}.json"
    
    if not project_file.exists():
        return None
    
    try:
        with open(project_file, 'r', encoding='utf-8') as f:
            project_data = json.load(f)
        
        overview = project_data.get("overview", "概要なし")
        status = project_data.get("status", "DRAFT")
        
        # Filter out undefined fields
        if overview == DEFAULT_UNDEF:
            overview = "概要なし"
        if status == DEFAULT_UNDEF:
            status = "DRAFT"
        
        # Truncate overview if too long
        if len(overview) > 50:
            overview = overview[:47] + "..."
        
        return f"{project_id} ({status}) - {overview}"
        
    except Exception:
        return f"{project_id} (読み込みエラー)"