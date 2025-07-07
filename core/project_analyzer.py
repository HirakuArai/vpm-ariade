# --- core/project_analyzer.py ---
"""
Project Content Analyzer - AIによるプロジェクト内容分析
プロジェクト概要から必要情報を推論し、動的スキーマを生成
"""

import json
import logging
import openai
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from .dynamic_schema import DynamicProjectSchema, FieldPriority, FieldStatus

logger = logging.getLogger(__name__)

class ProjectComplexity(Enum):
    """プロジェクトの複雑度"""
    SIMPLE = "simple"      # 個人的な活動、短期間
    MEDIUM = "medium"      # チーム活動、中期間
    COMPLEX = "complex"    # 組織的活動、長期間

@dataclass
class ProjectAnalysis:
    """プロジェクト分析結果"""
    project_type: str
    complexity: ProjectComplexity
    key_stakeholders: List[str]
    critical_success_factors: List[str]
    potential_risks: List[str]
    required_fields: Dict[str, Dict]
    recommended_fields: Dict[str, Dict]
    confidence: float

class ProjectContentAnalyzer:
    """プロジェクト内容の分析"""
    
    def __init__(self, api_key: str = None):
        """
        初期化
        
        Args:
            api_key: OpenAI API key (Noneの場合は環境変数から取得)
        """
        if api_key:
            openai.api_key = api_key
        self.model = "gpt-4.1"  # 分析精度を重視
    
    def analyze_project_description(self, description: str, 
                                  additional_context: str = None) -> ProjectAnalysis:
        """
        プロジェクト概要から必要情報を推論
        
        Args:
            description: プロジェクトの概要
            additional_context: 追加のコンテキスト情報
            
        Returns:
            ProjectAnalysis: 分析結果
        """
        try:
            # システムプロンプトの構築
            system_prompt = self._build_analysis_prompt()
            
            # ユーザープロンプトの構築
            user_prompt = f"""
プロジェクト概要: {description}

{f"追加情報: {additional_context}" if additional_context else ""}

上記のプロジェクトについて、成功に必要な情報カテゴリを分析してください。
"""
            
            # OpenAI API呼び出し（ログ記録ラッパー使用）
            from core.v2.openai_config import create_chat_completion
            response = create_chat_completion(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,  # 一貫性重視
                max_tokens=8000
            )
            
            # レスポンスを解析
            analysis_text = response.choices[0].message.content.strip()
            return self._parse_analysis_response(analysis_text, description)
            
        except Exception as e:
            logger.error(f"Project analysis failed: {e}")
            # フォールバック: 基本的な分析結果を返す
            return self._create_fallback_analysis(description)
    
    def _build_analysis_prompt(self) -> str:
        """分析用システムプロンプトを構築"""
        return """あなたはプロジェクト管理の専門家です。プロジェクトの概要を分析し、成功に必要な情報カテゴリを特定してください。

# 分析の観点

## プロジェクト種別の判定
- 個人活動、チーム活動、組織活動
- 創作、学習、業務、イベント、開発、研究など

## 複雑度の評価
- simple: 個人的、短期間（数日〜数週間）、明確な目標
- medium: チーム関与、中期間（数週間〜数ヶ月）、複数の要素
- complex: 組織的、長期間（数ヶ月〜年単位）、多くのステークホルダー

## 必要情報の特定
各プロジェクト種別で一般的に必要となる情報を特定:
- **必須(required)**: プロジェクト成功に絶対必要
- **推奨(recommended)**: あった方が良い
- **オプション(optional)**: 状況によって必要

# 出力形式
以下のJSON形式で回答してください:

```json
{
  "project_type": "プロジェクト種別",
  "complexity": "simple|medium|complex",
  "key_stakeholders": ["ステークホルダー1", "ステークホルダー2"],
  "critical_success_factors": ["成功要因1", "成功要因2"],
  "potential_risks": ["リスク1", "リスク2"],
  "required_fields": {
    "field_name": {
      "description": "フィールドの説明",
      "questions": ["質問1", "質問2"],
      "ask_after": null
    }
  },
  "recommended_fields": {
    "field_name": {
      "description": "フィールドの説明", 
      "questions": ["質問1"],
      "ask_after": "prerequisite_field"
    }
  },
  "confidence": 0.85
}
```

# 例

**入力**: "会社の新入社員研修プログラムを企画します"

**出力**:
```json
{
  "project_type": "education_program",
  "complexity": "medium",
  "key_stakeholders": ["新入社員", "人事担当", "各部署メンター", "経営陣"],
  "critical_success_factors": ["明確な学習目標", "実践的な内容", "適切な評価方法"],
  "potential_risks": ["参加者のモチベーション低下", "内容の陳腐化", "実施コスト超過"],
  "required_fields": {
    "participants": {
      "description": "研修参加者の情報",
      "questions": ["新入社員は何名ですか？", "バックグラウンドは？"],
      "ask_after": null
    },
    "timeline": {
      "description": "研修スケジュール",
      "questions": ["研修期間はいつからいつまでですか？", "1日何時間の予定ですか？"],
      "ask_after": "participants"
    },
    "learning_objectives": {
      "description": "学習目標",
      "questions": ["どのようなスキルを身につけてもらいたいですか？"],
      "ask_after": null
    }
  },
  "recommended_fields": {
    "budget": {
      "description": "研修予算",
      "questions": ["予算の上限はありますか？"],
      "ask_after": "timeline"
    },
    "evaluation_method": {
      "description": "評価方法",
      "questions": ["どのように効果を測定しますか？"],
      "ask_after": "learning_objectives"
    }
  },
  "confidence": 0.9
}
```"""
    
    def _parse_analysis_response(self, response_text: str, original_description: str) -> ProjectAnalysis:
        """AI応答をパースしてProjectAnalysisオブジェクトに変換"""
        try:
            # JSONブロックを抽出
            import re
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', response_text, re.DOTALL)
            if json_match:
                json_text = json_match.group(1)
            else:
                # JSON形式でない場合、全体をJSONとして解析を試みる
                json_text = response_text
            
            # JSONをパース
            data = json.loads(json_text)
            
            # ProjectAnalysisオブジェクトを構築
            return ProjectAnalysis(
                project_type=data.get("project_type", "unknown"),
                complexity=ProjectComplexity(data.get("complexity", "medium")),
                key_stakeholders=data.get("key_stakeholders", []),
                critical_success_factors=data.get("critical_success_factors", []),
                potential_risks=data.get("potential_risks", []),
                required_fields=data.get("required_fields", {}),
                recommended_fields=data.get("recommended_fields", {}),
                confidence=data.get("confidence", 0.5)
            )
            
        except Exception as e:
            logger.error(f"Failed to parse analysis response: {e}")
            logger.debug(f"Response text: {response_text}")
            return self._create_fallback_analysis(original_description)
    
    def _create_fallback_analysis(self, description: str) -> ProjectAnalysis:
        """分析失敗時のフォールバック"""
        # 基本的なキーワード分析
        description_lower = description.lower()
        
        # プロジェクト種別の簡易判定
        if any(keyword in description_lower for keyword in ["登山", "旅行", "イベント", "パーティー"]):
            project_type = "event_activity"
            basic_fields = {
                "participants": {
                    "description": "参加者情報",
                    "questions": ["参加者は何名ですか？"],
                    "ask_after": None
                },
                "timeline": {
                    "description": "実施時期",
                    "questions": ["いつ実施しますか？"],
                    "ask_after": "participants"
                },
                "budget": {
                    "description": "予算",
                    "questions": ["予算はどの程度ですか？"],
                    "ask_after": "timeline"
                }
            }
        elif any(keyword in description_lower for keyword in ["開発", "システム", "アプリ", "ソフト"]):
            project_type = "software_development"
            basic_fields = {
                "requirements": {
                    "description": "要件",
                    "questions": ["どのような機能が必要ですか？"],
                    "ask_after": None
                },
                "technology": {
                    "description": "技術スタック",
                    "questions": ["使用する技術はありますか？"],
                    "ask_after": "requirements"
                },
                "timeline": {
                    "description": "開発期間",
                    "questions": ["いつまでに完成予定ですか？"],
                    "ask_after": "requirements"
                }
            }
        else:
            project_type = "general"
            basic_fields = {
                "objectives": {
                    "description": "目標",
                    "questions": ["具体的な目標は何ですか？"],
                    "ask_after": None
                },
                "timeline": {
                    "description": "期間",
                    "questions": ["いつまでに完了予定ですか？"],
                    "ask_after": "objectives"
                }
            }
        
        return ProjectAnalysis(
            project_type=project_type,
            complexity=ProjectComplexity.MEDIUM,
            key_stakeholders=["プロジェクトオーナー"],
            critical_success_factors=["明確な目標設定", "適切な計画"],
            potential_risks=["スケジュール遅延", "要件変更"],
            required_fields=basic_fields,
            recommended_fields={},
            confidence=0.3
        )
    
    def apply_analysis_to_schema(self, project_id: str, analysis: ProjectAnalysis, 
                               projects_dir=None) -> bool:
        """
        分析結果を動的スキーマに適用
        
        Args:
            project_id: プロジェクトID
            analysis: 分析結果
            projects_dir: プロジェクトディレクトリ
            
        Returns:
            bool: 適用成功可否
        """
        try:
            # プロジェクトファイルが存在しない場合は作成
            if projects_dir is None:
                projects_dir = Path("data/projects")
            
            project_file = projects_dir / f"{project_id}.json"
            if not project_file.exists():
                # 基本的なプロジェクトファイルを作成
                projects_dir.mkdir(parents=True, exist_ok=True)
                basic_project = {
                    "identifier": project_id,
                    "overview": "AI分析により生成されたプロジェクト",
                    "created_at": datetime.now().isoformat(),
                    "created_by": "ai_analyzer",
                    "status": "DRAFT",
                    "schema_version": "1.0",
                    "updated_at": datetime.now().isoformat(),
                    "change_log": [],
                    "uuid": f"ai-{project_id}",
                    "tasks": [],
                    "phase": "INCEPTION",
                    "completion_percentage": 0.0,
                    "next_actions": [],
                    "blocking_issues": [],
                    "phase_requirements": {},
                    "phase_history": []
                }
                
                with open(project_file, 'w', encoding='utf-8') as f:
                    json.dump(basic_project, f, ensure_ascii=False, indent=2)
            
            # 既存のスキーマを取得
            schema = DynamicProjectSchema(project_id, projects_dir)
            
            # 必須フィールドを追加
            for field_name, field_info in analysis.required_fields.items():
                if field_name not in schema.fields:
                    schema.add_field(
                        name=field_name,
                        priority=FieldPriority.REQUIRED,
                        questions=field_info.get("questions", []),
                        ask_after=field_info.get("ask_after")
                    )
            
            # 推奨フィールドを追加
            for field_name, field_info in analysis.recommended_fields.items():
                if field_name not in schema.fields:
                    schema.add_field(
                        name=field_name,
                        priority=FieldPriority.RECOMMENDED,
                        questions=field_info.get("questions", []),
                        ask_after=field_info.get("ask_after")
                    )
            
            # スキーマを保存
            success = schema.save_to_project_file()
            
            if success:
                logger.info(f"Applied analysis to schema for project {project_id}")
                logger.info(f"Added {len(analysis.required_fields)} required fields")
                logger.info(f"Added {len(analysis.recommended_fields)} recommended fields")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to apply analysis to schema: {e}")
            return False
    
    def analyze_and_initialize_project(self, project_id: str, description: str,
                                     additional_context: str = None,
                                     projects_dir=None) -> Tuple[ProjectAnalysis, bool]:
        """
        プロジェクト分析とスキーマ初期化を一括実行
        
        Args:
            project_id: プロジェクトID
            description: プロジェクト概要
            additional_context: 追加コンテキスト
            projects_dir: プロジェクトディレクトリ
            
        Returns:
            Tuple[ProjectAnalysis, bool]: (分析結果, スキーマ適用成功可否)
        """
        # 1. プロジェクト分析
        analysis = self.analyze_project_description(description, additional_context)
        
        # 2. スキーマに適用
        schema_success = self.apply_analysis_to_schema(project_id, analysis, projects_dir)
        
        return analysis, schema_success


# ユーティリティ関数
def analyze_project_and_create_schema(project_id: str, description: str,
                                    api_key: str = None,
                                    projects_dir=None) -> Tuple[ProjectAnalysis, bool]:
    """
    プロジェクト分析とスキーマ作成のヘルパー関数
    
    Args:
        project_id: プロジェクトID
        description: プロジェクト概要
        api_key: OpenAI API key
        projects_dir: プロジェクトディレクトリ
        
    Returns:
        Tuple[ProjectAnalysis, bool]: (分析結果, 成功可否)
    """
    analyzer = ProjectContentAnalyzer(api_key)
    return analyzer.analyze_and_initialize_project(
        project_id, description, projects_dir=projects_dir
    )