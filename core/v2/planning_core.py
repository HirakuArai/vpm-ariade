"""
Planning Core: Work Breakdown Structure (WBS) Generator for Kai VPM
Generates detailed task lists from persona analysis results with dependencies and realistic scheduling.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import re


def generate_wbs(persona_result: dict) -> List[Dict[str, Any]]:
    """
    Generate Work Breakdown Structure (WBS) from persona analysis results.
    
    Args:
        persona_result: Output from persona_core.analyze_charter()
        
    Returns:
        List[Dict]: List of tasks with name, description, depends_on, suggested_due_date
    """
    if not persona_result:
        return []
    
    high_priority_goals = persona_result.get('high_priority_goals', [])
    recommended_milestones = persona_result.get('recommended_milestones', [])
    project_name = persona_result.get('project_name', 'Project')
    
    # Create timeline reference from milestones
    milestone_dates = _extract_milestone_dates(recommended_milestones)
    
    # Generate base start date
    start_date = datetime.now() + timedelta(days=1)
    
    # Generate tasks for each priority goal
    all_tasks = []
    task_counter = 1
    
    # Add initial project setup tasks
    setup_tasks = _generate_setup_tasks(start_date, task_counter)
    all_tasks.extend(setup_tasks)
    task_counter += len(setup_tasks)
    
    # Process each high priority goal
    for goal in high_priority_goals:
        goal_tasks = _generate_tasks_for_goal(
            goal, start_date, milestone_dates, task_counter, all_tasks
        )
        all_tasks.extend(goal_tasks)
        task_counter += len(goal_tasks)
    
    # Add final integration and review tasks
    final_tasks = _generate_final_tasks(all_tasks, milestone_dates, task_counter)
    all_tasks.extend(final_tasks)
    
    return all_tasks


def _extract_milestone_dates(milestones: List[Dict[str, str]]) -> Dict[str, datetime]:
    """Extract and parse milestone dates"""
    milestone_dates = {}
    
    for milestone in milestones:
        title = milestone.get('title', '')
        due_str = milestone.get('due', '')
        
        if due_str:
            try:
                due_date = datetime.strptime(due_str, '%Y-%m-%d')
                milestone_dates[title] = due_date
            except ValueError:
                continue
    
    return milestone_dates


def _generate_setup_tasks(start_date: datetime, task_counter: int) -> List[Dict[str, Any]]:
    """Generate initial project setup tasks"""
    tasks = []
    
    setup_task_templates = [
        {
            "name": "プロジェクト環境セットアップ",
            "description": "開発環境、ツール、ワークスペースの準備を行う。",
            "days_offset": 1,
            "depends_on": []
        },
        {
            "name": "要件定義書作成",
            "description": "詳細な機能要件と非機能要件をドキュメント化する。",
            "days_offset": 3,
            "depends_on": ["プロジェクト環境セットアップ"]
        },
        {
            "name": "技術設計書作成",
            "description": "システムアーキテクチャと技術スタックを決定し文書化する。",
            "days_offset": 5,
            "depends_on": ["要件定義書作成"]
        }
    ]
    
    for template in setup_task_templates:
        task_date = start_date + timedelta(days=template['days_offset'])
        
        tasks.append({
            "name": template["name"],
            "description": template["description"],
            "depends_on": template["depends_on"],
            "suggested_due_date": task_date.strftime('%Y-%m-%d')
        })
    
    return tasks


def _generate_tasks_for_goal(
    goal: str, 
    start_date: datetime, 
    milestone_dates: Dict[str, datetime],
    task_counter: int,
    existing_tasks: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Generate specific tasks for a high priority goal"""
    
    # Extract goal type and content
    goal_clean = _clean_goal_text(goal)
    goal_type = _classify_goal_type(goal_clean)
    
    # Get base dependencies from existing tasks
    base_dependencies = ["技術設計書作成"]
    
    # Generate tasks based on goal type
    if goal_type == "development":
        return _generate_development_tasks(goal_clean, start_date, milestone_dates, base_dependencies)
    elif goal_type == "system":
        return _generate_system_tasks(goal_clean, start_date, milestone_dates, base_dependencies)
    elif goal_type == "integration":
        return _generate_integration_tasks(goal_clean, start_date, milestone_dates, base_dependencies)
    elif goal_type == "warning":
        return _generate_resolution_tasks(goal_clean, start_date, milestone_dates, [])
    else:
        return _generate_generic_tasks(goal_clean, start_date, milestone_dates, base_dependencies)


def _clean_goal_text(goal: str) -> str:
    """Remove priority prefixes from goal text"""
    # Remove priority markers like 【最優先】, 【重要】, etc.
    clean_text = re.sub(r'【[^】]+】', '', goal).strip()
    return clean_text


def _classify_goal_type(goal: str) -> str:
    """Classify the type of goal for appropriate task generation"""
    goal_lower = goal.lower()
    
    if any(keyword in goal_lower for keyword in ['警告', '明確化', '決定', '特定']):
        return "warning"
    elif any(keyword in goal_lower for keyword in ['開発', 'システム', '実装', '機能']):
        return "development"
    elif any(keyword in goal_lower for keyword in ['登録', 'ユーザー', 'ui', 'ux']):
        return "system"
    elif any(keyword in goal_lower for keyword in ['対応', '連携', '統合']):
        return "integration"
    else:
        return "generic"


def _generate_development_tasks(
    goal: str, 
    start_date: datetime, 
    milestone_dates: Dict[str, datetime],
    base_dependencies: List[str]
) -> List[Dict[str, Any]]:
    """Generate tasks for development-related goals"""
    tasks = []
    base_date = start_date + timedelta(days=7)  # Start after setup phase
    
    task_templates = [
        {
            "name": f"{goal} - プロトタイプ作成",
            "description": f"{goal}の基本機能プロトタイプを作成する。",
            "days_offset": 0,
            "depends_on": base_dependencies
        },
        {
            "name": f"{goal} - コア機能実装",
            "description": f"{goal}の主要機能を実装する。",
            "days_offset": 7,
            "depends_on": [f"{goal} - プロトタイプ作成"]
        },
        {
            "name": f"{goal} - テスト実装",
            "description": f"{goal}の単体テストと結合テストを作成する。",
            "days_offset": 12,
            "depends_on": [f"{goal} - コア機能実装"]
        },
        {
            "name": f"{goal} - 品質検証",
            "description": f"{goal}の品質チェックと性能テストを実施する。",
            "days_offset": 16,
            "depends_on": [f"{goal} - テスト実装"]
        }
    ]
    
    for template in task_templates:
        task_date = base_date + timedelta(days=template['days_offset'])
        
        tasks.append({
            "name": template["name"],
            "description": template["description"],
            "depends_on": template["depends_on"],
            "suggested_due_date": task_date.strftime('%Y-%m-%d')
        })
    
    return tasks


def _generate_system_tasks(
    goal: str, 
    start_date: datetime, 
    milestone_dates: Dict[str, datetime],
    base_dependencies: List[str]
) -> List[Dict[str, Any]]:
    """Generate tasks for system/user interface related goals"""
    tasks = []
    base_date = start_date + timedelta(days=5)
    
    task_templates = [
        {
            "name": f"{goal} - UI設計",
            "description": f"{goal}のユーザーインターフェース設計を行う。",
            "days_offset": 0,
            "depends_on": base_dependencies
        },
        {
            "name": f"{goal} - データモデル設計",
            "description": f"{goal}に必要なデータ構造と関係を設計する。",
            "days_offset": 3,
            "depends_on": base_dependencies
        },
        {
            "name": f"{goal} - フロントエンド実装",
            "description": f"{goal}のユーザーインターフェースを実装する。",
            "days_offset": 8,
            "depends_on": [f"{goal} - UI設計"]
        },
        {
            "name": f"{goal} - バックエンド実装",
            "description": f"{goal}のサーバーサイド機能を実装する。",
            "days_offset": 10,
            "depends_on": [f"{goal} - データモデル設計"]
        },
        {
            "name": f"{goal} - 統合テスト",
            "description": f"{goal}のフロントエンドとバックエンドを統合しテストする。",
            "days_offset": 15,
            "depends_on": [f"{goal} - フロントエンド実装", f"{goal} - バックエンド実装"]
        }
    ]
    
    for template in task_templates:
        task_date = base_date + timedelta(days=template['days_offset'])
        
        tasks.append({
            "name": template["name"],
            "description": template["description"],
            "depends_on": template["depends_on"],
            "suggested_due_date": task_date.strftime('%Y-%m-%d')
        })
    
    return tasks


def _generate_integration_tasks(
    goal: str, 
    start_date: datetime, 
    milestone_dates: Dict[str, datetime],
    base_dependencies: List[str]
) -> List[Dict[str, Any]]:
    """Generate tasks for integration-related goals"""
    tasks = []
    base_date = start_date + timedelta(days=14)  # Start after core components
    
    task_templates = [
        {
            "name": f"{goal} - 統合計画策定",
            "description": f"{goal}の統合手順と検証方法を計画する。",
            "days_offset": 0,
            "depends_on": base_dependencies
        },
        {
            "name": f"{goal} - 統合実装",
            "description": f"{goal}の統合機能を実装する。",
            "days_offset": 5,
            "depends_on": [f"{goal} - 統合計画策定"]
        },
        {
            "name": f"{goal} - 統合テスト",
            "description": f"{goal}の統合テストを実施し、動作確認を行う。",
            "days_offset": 10,
            "depends_on": [f"{goal} - 統合実装"]
        }
    ]
    
    for template in task_templates:
        task_date = base_date + timedelta(days=template['days_offset'])
        
        tasks.append({
            "name": template["name"],
            "description": template["description"],
            "depends_on": template["depends_on"],
            "suggested_due_date": task_date.strftime('%Y-%m-%d')
        })
    
    return tasks


def _generate_resolution_tasks(
    goal: str, 
    start_date: datetime, 
    milestone_dates: Dict[str, datetime],
    base_dependencies: List[str]
) -> List[Dict[str, Any]]:
    """Generate tasks for warning/resolution goals"""
    tasks = []
    base_date = start_date  # Start immediately for urgent items
    
    if "関係者" in goal:
        task_templates = [
            {
                "name": "ステークホルダー分析",
                "description": "プロジェクトに関わる全関係者を特定し、影響度と関心度を分析する。",
                "days_offset": 0,
                "depends_on": []
            },
            {
                "name": "関係者役割定義",
                "description": "各関係者の役割、責任、権限を明確に定義し合意を得る。",
                "days_offset": 2,
                "depends_on": ["ステークホルダー分析"]
            }
        ]
    elif "ツール" in goal:
        task_templates = [
            {
                "name": "技術調査・比較",
                "description": "利用可能なツールと技術を調査し、比較検討を行う。",
                "days_offset": 0,
                "depends_on": []
            },
            {
                "name": "ツール選定・決定",
                "description": "プロジェクト要件に最適なツールを選定し、決定する。",
                "days_offset": 3,
                "depends_on": ["技術調査・比較"]
            }
        ]
    else:
        task_templates = [
            {
                "name": f"{goal} - 現状分析",
                "description": f"{goal}に関する現状を詳細に分析する。",
                "days_offset": 0,
                "depends_on": []
            },
            {
                "name": f"{goal} - 解決策検討",
                "description": f"{goal}の解決策を検討し、最適な方法を決定する。",
                "days_offset": 2,
                "depends_on": [f"{goal} - 現状分析"]
            }
        ]
    
    for template in task_templates:
        task_date = base_date + timedelta(days=template['days_offset'])
        
        tasks.append({
            "name": template["name"],
            "description": template["description"],
            "depends_on": template["depends_on"],
            "suggested_due_date": task_date.strftime('%Y-%m-%d')
        })
    
    return tasks


def _generate_generic_tasks(
    goal: str, 
    start_date: datetime, 
    milestone_dates: Dict[str, datetime],
    base_dependencies: List[str]
) -> List[Dict[str, Any]]:
    """Generate generic tasks for unclassified goals"""
    tasks = []
    base_date = start_date + timedelta(days=7)
    
    task_templates = [
        {
            "name": f"{goal} - 計画策定",
            "description": f"{goal}の詳細計画を策定する。",
            "days_offset": 0,
            "depends_on": base_dependencies
        },
        {
            "name": f"{goal} - 実装・実行",
            "description": f"{goal}を実装・実行する。",
            "days_offset": 5,
            "depends_on": [f"{goal} - 計画策定"]
        },
        {
            "name": f"{goal} - 検証・完了",
            "description": f"{goal}の結果を検証し、完了確認を行う。",
            "days_offset": 10,
            "depends_on": [f"{goal} - 実装・実行"]
        }
    ]
    
    for template in task_templates:
        task_date = base_date + timedelta(days=template['days_offset'])
        
        tasks.append({
            "name": template["name"],
            "description": template["description"],
            "depends_on": template["depends_on"],
            "suggested_due_date": task_date.strftime('%Y-%m-%d')
        })
    
    return tasks


def _generate_final_tasks(
    existing_tasks: List[Dict[str, Any]], 
    milestone_dates: Dict[str, datetime],
    task_counter: int
) -> List[Dict[str, Any]]:
    """Generate final integration and review tasks"""
    tasks = []
    
    # Find the latest task date
    latest_date = datetime.now()
    for task in existing_tasks:
        try:
            task_date = datetime.strptime(task['suggested_due_date'], '%Y-%m-%d')
            if task_date > latest_date:
                latest_date = task_date
        except (ValueError, KeyError):
            continue
    
    # Generate final tasks
    final_date = latest_date + timedelta(days=3)
    
    final_task_templates = [
        {
            "name": "統合テスト実施",
            "description": "全コンポーネントの統合テストを実施し、システム全体の動作を確認する。",
            "days_offset": 0,
            "depends_on": []  # Will be populated with all development tasks
        },
        {
            "name": "ユーザー受入テスト",
            "description": "エンドユーザーによる受入テストを実施し、要件充足を確認する。",
            "days_offset": 3,
            "depends_on": ["統合テスト実施"]
        },
        {
            "name": "プロジェクト完了・振り返り",
            "description": "プロジェクトの成果を評価し、学習事項をまとめる。",
            "days_offset": 7,
            "depends_on": ["ユーザー受入テスト"]
        }
    ]
    
    # Add dependencies for integration test (all major tasks should be done)
    development_tasks = [
        task['name'] for task in existing_tasks 
        if any(keyword in task['name'] for keyword in ['実装', '検証', '完了', 'テスト'])
    ]
    
    for template in final_task_templates:
        task_date = final_date + timedelta(days=template['days_offset'])
        
        if template['name'] == "統合テスト実施":
            depends_on = development_tasks[-3:] if development_tasks else []  # Latest 3 dev tasks
        else:
            depends_on = template["depends_on"]
        
        tasks.append({
            "name": template["name"],
            "description": template["description"],
            "depends_on": depends_on,
            "suggested_due_date": task_date.strftime('%Y-%m-%d')
        })
    
    return tasks


if __name__ == "__main__":
    # Example usage
    sample_persona_result = {
        "project_name": "テストプロジェクト",
        "high_priority_goals": [
            "【重要】ユーザー登録システムの完成",
            "【重要】商品検索機能の実装",
            "【警告】関係者の明確化が必要"
        ],
        "recommended_milestones": [
            {"title": "プロトタイプ完成", "due": "2025-07-15"}
        ]
    }
    
    wbs = generate_wbs(sample_persona_result)
    for task in wbs:
        print(f"{task['name']}: {task['suggested_due_date']}")
        print(f"  {task['description']}")
        print(f"  依存: {task['depends_on']}")
        print()