"""
Persona Core: AI Project Manager for Kai VPM
Analyzes project charters and provides prioritization, risk assessment, and milestone recommendations.
"""

import yaml
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional


def analyze_charter(yaml_path: str) -> dict:
    """
    Analyze a project charter YAML file and return prioritized goals, risks, and milestone recommendations.
    
    Args:
        yaml_path: Path to the charter YAML file
        
    Returns:
        dict: Analysis results with prioritized goals, risks, milestones, and persona comments
    """
    # Load the charter
    charter = _load_charter(yaml_path)
    
    # Extract project name
    project_name = charter.get('name', 'Unnamed Project')
    
    # Analyze priorities
    high_priority_goals = _analyze_priorities(charter)
    
    # Extract and supplement risks
    potential_risks = _analyze_risks(charter)
    
    # Generate recommended milestones
    recommended_milestones = _generate_milestones(charter)
    
    # Generate persona comment
    persona_comment = _generate_persona_comment(charter, high_priority_goals, potential_risks)
    
    return {
        "project_name": project_name,
        "high_priority_goals": high_priority_goals,
        "potential_risks": potential_risks,
        "recommended_milestones": recommended_milestones,
        "persona_comment": persona_comment
    }


def _load_charter(yaml_path: str) -> Dict[str, Any]:
    """Load charter from YAML file"""
    charter_path = Path(yaml_path)
    if not charter_path.exists():
        raise FileNotFoundError(f"Charter file not found: {yaml_path}")
    
    with open(charter_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f) or {}


def _analyze_priorities(charter: Dict[str, Any]) -> List[str]:
    """
    Analyze and prioritize goals based on purpose, success_metrics, and outcomes.
    
    Priority logic:
    1. Items directly linked to purpose and success_metrics (highest)
    2. Items in scope.in but not explicitly in outcomes (medium)
    3. Items with undefined tools/stakeholders (lower with warning)
    """
    high_priority_goals = []
    
    purpose = charter.get('purpose', '').lower()
    success_metrics = charter.get('success_metrics', [])
    outcomes = charter.get('outcomes', [])
    scope_in = charter.get('scope', {}).get('in', [])
    
    # Convert to lowercase for matching
    success_keywords = ' '.join(success_metrics).lower() if success_metrics else ''
    
    # Priority 1: Outcomes that align with purpose and success metrics
    for outcome in outcomes:
        outcome_lower = outcome.lower()
        if any(keyword in outcome_lower for keyword in purpose.split() if len(keyword) > 2):
            high_priority_goals.append(f"【最優先】{outcome}")
        elif any(keyword in outcome_lower for keyword in success_keywords.split() if len(keyword) > 2):
            high_priority_goals.append(f"【最優先】{outcome}")
        else:
            high_priority_goals.append(f"【重要】{outcome}")
    
    # Priority 2: Scope items not covered in outcomes
    for scope_item in scope_in:
        if not any(scope_item.lower() in outcome.lower() for outcome in outcomes):
            high_priority_goals.append(f"【中優先】{scope_item}")
    
    # Check for undefined stakeholders/tools and adjust priorities
    stakeholders = charter.get('stakeholders', [])
    tools = charter.get('constraints', {}).get('tools', [])
    
    if not stakeholders:
        high_priority_goals.insert(0, "【警告】関係者の明確化が必要")
    
    if not tools:
        high_priority_goals.insert(-1 if stakeholders else 0, "【警告】使用ツールの決定が必要")
    
    return high_priority_goals[:10]  # Limit to top 10


def _analyze_risks(charter: Dict[str, Any]) -> List[Dict[str, str]]:
    """Extract existing risks and add supplementary risk analysis"""
    risks = []
    
    # Add existing risks from charter
    charter_risks = charter.get('risks', [])
    for risk_item in charter_risks:
        if isinstance(risk_item, dict):
            risks.append({
                "risk": risk_item.get('risk', ''),
                "impact": "中",  # Default impact level
                "suggested_mitigation": risk_item.get('mitigation', '')
            })
        elif isinstance(risk_item, str):
            risks.append({
                "risk": risk_item,
                "impact": "中",
                "suggested_mitigation": "対策要検討"
            })
    
    # Add supplementary risks based on charter analysis
    constraints = charter.get('constraints', {})
    stakeholders = charter.get('stakeholders', [])
    
    # Deadline risk
    deadline = constraints.get('deadline')
    milestones = charter.get('milestones', [])
    if deadline and deadline != 'n/a' and milestones:
        try:
            deadline_date = datetime.strptime(deadline, '%Y-%m-%d')
            if deadline_date < datetime.now() + timedelta(days=30):  # Less than 30 days
                risks.append({
                    "risk": "タイトなスケジュール",
                    "impact": "高",
                    "suggested_mitigation": "スコープの見直しまたはリソースの追加を検討"
                })
        except ValueError:
            pass
    
    # Stakeholder risk
    if not stakeholders:
        risks.append({
            "risk": "関係者が未定義",
            "impact": "高",
            "suggested_mitigation": "プロジェクト開始前に全関係者を特定し、役割を明確化"
        })
    
    # Budget risk
    budget = constraints.get('budget')
    if not budget or budget == 'n/a':
        risks.append({
            "risk": "予算制約が不明",
            "impact": "中",
            "suggested_mitigation": "概算予算の設定と承認プロセスの確立"
        })
    
    # Tool/Technology risk
    tools = constraints.get('tools', [])
    if not tools:
        risks.append({
            "risk": "技術・ツール選定が未完了",
            "impact": "中",
            "suggested_mitigation": "技術調査フェーズを設けて最適なツールを選定"
        })
    
    return risks


def _generate_milestones(charter: Dict[str, Any]) -> List[Dict[str, str]]:
    """Generate recommended milestones based on outcomes and constraints"""
    milestones = []
    
    # Start with existing milestones
    existing_milestones = charter.get('milestones', [])
    for milestone in existing_milestones:
        if isinstance(milestone, dict):
            milestones.append({
                "title": milestone.get('title', ''),
                "due": milestone.get('date', '')
            })
    
    # Generate additional milestones based on outcomes
    outcomes = charter.get('outcomes', [])
    constraints = charter.get('constraints', {})
    deadline = constraints.get('deadline')
    
    # Calculate milestone dates
    base_date = datetime.now()
    if deadline and deadline != 'n/a':
        try:
            end_date = datetime.strptime(deadline, '%Y-%m-%d')
            project_duration = (end_date - base_date).days
        except ValueError:
            project_duration = 90  # Default 3 months
    else:
        project_duration = 90  # Default 3 months
        end_date = base_date + timedelta(days=project_duration)
    
    # Generate standard project phases if not already covered
    existing_titles = [m['title'] for m in milestones]
    
    suggested_milestones = [
        ("プロジェクト計画完成", 0.15),
        ("初期プロトタイプ/MVP完成", 0.4),
        ("中間レビュー・検証完了", 0.65),
        ("最終成果物完成", 0.9),
        ("プロジェクト完了・振り返り", 1.0)
    ]
    
    for title, ratio in suggested_milestones:
        if not any(title in existing_title for existing_title in existing_titles):
            milestone_date = base_date + timedelta(days=int(project_duration * ratio))
            milestones.append({
                "title": title,
                "due": milestone_date.strftime('%Y-%m-%d')
            })
    
    # Add outcome-specific milestones
    for i, outcome in enumerate(outcomes[:3]):  # Limit to first 3 outcomes
        outcome_ratio = 0.3 + (i * 0.2)  # Distribute between 30% and 70%
        milestone_date = base_date + timedelta(days=int(project_duration * outcome_ratio))
        milestones.append({
            "title": f"成果物達成: {outcome}",
            "due": milestone_date.strftime('%Y-%m-%d')
        })
    
    # Sort by due date and return top 8
    milestones.sort(key=lambda x: x['due'] if x['due'] else '9999-12-31')
    return milestones[:8]


def _generate_persona_comment(charter: Dict[str, Any], priorities: List[str], risks: List[Dict[str, str]]) -> str:
    """Generate AI persona comment with overall assessment and advice"""
    project_name = charter.get('name', 'このプロジェクト')
    
    comments = [f"【{project_name}】の分析結果をお伝えします。"]
    
    # Assess project clarity
    purpose = charter.get('purpose', '')
    outcomes = charter.get('outcomes', [])
    stakeholders = charter.get('stakeholders', [])
    
    if purpose and outcomes:
        comments.append("プロジェクトの目的と成果物が明確に定義されており、良好なスタートです。")
    else:
        comments.append("プロジェクトの目的または成果物の定義が不十分です。明確化をお勧めします。")
    
    # Risk assessment
    high_risks = [r for r in risks if r.get('impact') == '高']
    if high_risks:
        comments.append(f"高リスク項目が{len(high_risks)}件検出されました。特に注意が必要です。")
    
    # Stakeholder assessment
    if not stakeholders:
        comments.append("関係者が未定義のため、プロジェクト開始前にステークホルダー分析を実施することを強く推奨します。")
    
    # Priority guidance
    urgent_priorities = [p for p in priorities if '【警告】' in p or '【最優先】' in p]
    if urgent_priorities:
        comments.append(f"最優先事項{len(urgent_priorities)}件から着手し、段階的に進めることをお勧めします。")
    
    # Timeline assessment
    constraints = charter.get('constraints', {})
    deadline = constraints.get('deadline')
    if deadline and deadline != 'n/a':
        try:
            deadline_date = datetime.strptime(deadline, '%Y-%m-%d')
            days_left = (deadline_date - datetime.now()).days
            if days_left < 30:
                comments.append("締切まで時間が限られているため、スコープの見直しを検討してください。")
            elif days_left > 365:
                comments.append("十分な期間があるため、品質向上と丁寧な検証に注力できます。")
        except ValueError:
            pass
    
    # Final advice
    comments.append("定期的な進捗確認と柔軟な計画調整により、プロジェクト成功確率を高めていきましょう。")
    
    return " ".join(comments)


def get_persona_prompt(charter_path: str) -> str:
    """
    Get persona system prompt with background information from charter
    
    Args:
        charter_path: Path to charter YAML file
        
    Returns:
        Enhanced system prompt with background information
    """
    base_prompt = """You are an expert AI project manager persona.
Analyze the provided project charter and give practical, actionable recommendations.
Focus on prioritization, risk mitigation, and realistic milestone planning."""
    
    try:
        charter = _load_charter(charter_path)
        background = charter.get('background')
        
        if background:
            enhanced_prompt = f"""{base_prompt}

<background>
{background}
</background>

Use this background information to provide more contextually relevant analysis and recommendations."""
            return enhanced_prompt
        
    except Exception:
        # If charter loading fails, return base prompt
        pass
    
    return base_prompt


if __name__ == "__main__":
    # Example usage
    import sys
    if len(sys.argv) > 1:
        result = analyze_charter(sys.argv[1])
        print(yaml.dump(result, default_flow_style=False, allow_unicode=True))
    else:
        print("Usage: python persona_core.py <charter_yaml_path>")