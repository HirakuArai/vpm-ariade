# --- core/conversation_engine.py ---
"""
PhaseAwareConversationEngine - フェーズ対応会話エンジン
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Any, Optional
from datetime import datetime

from .models import ProjectPhase, DEFAULT_UNDEF
from .project_service import get_project
from .lifecycle_manager import ProjectLifecycleManager

logger = logging.getLogger(__name__)

@dataclass
class ConversationResponse:
    """会話応答データクラス"""
    content: str
    phase: ProjectPhase
    suggested_actions: List[Dict[str, Any]]
    project_updates: List[Dict[str, Any]]
    next_actions: List[str]
    confidence: float = 0.8

class PhaseAwareConversationEngine:
    """フェーズ対応AI会話エンジン"""
    
    def __init__(self, project_id: str, projects_dir=None):
        self.project_id = project_id
        self.projects_dir = projects_dir
        self.project_data = get_project(project_id, projects_dir)
        
        if not self.project_data:
            raise ValueError(f"Project {project_id} not found")
        
        self.lifecycle_manager = ProjectLifecycleManager(projects_dir)
        self.current_phase = self.lifecycle_manager.get_current_phase(project_id)
    
    def generate_response(self, user_input: str) -> ConversationResponse:
        """フェーズに応じた会話応答を生成"""
        
        # フェーズ別の処理
        if self.current_phase == ProjectPhase.INCEPTION:
            return self._handle_inception_conversation(user_input)
        elif self.current_phase == ProjectPhase.DEFINITION:
            return self._handle_definition_conversation(user_input)
        elif self.current_phase == ProjectPhase.PLANNING:
            return self._handle_planning_conversation(user_input)
        elif self.current_phase == ProjectPhase.EXECUTION:
            return self._handle_execution_conversation(user_input)
        elif self.current_phase == ProjectPhase.MONITORING:
            return self._handle_monitoring_conversation(user_input)
        elif self.current_phase == ProjectPhase.CLOSURE:
            return self._handle_closure_conversation(user_input)
        else:
            return self._handle_generic_conversation(user_input)
    
    def get_system_prompt(self) -> str:
        """フェーズ特化型システムプロンプトを生成"""
        base_context = self._get_project_context()
        phase_context = self._get_phase_specific_context()
        
        return f"{base_context}\n\n{phase_context}\n\n必ず日本語で回答してください。"
    
    def _handle_inception_conversation(self, user_input: str) -> ConversationResponse:
        """構想段階の会話処理"""
        
        # 構想段階では目的・背景・基本要件の深掘りを行う
        suggested_actions = [
            {
                "type": "clarify_purpose",
                "description": "プロジェクトの目的を明確化",
                "priority": "high"
            },
            {
                "type": "identify_stakeholders", 
                "description": "ステークホルダーの特定",
                "priority": "medium"
            },
            {
                "type": "define_constraints",
                "description": "制約条件の整理",
                "priority": "medium"
            }
        ]
        
        # 構想段階の応答内容を生成
        content = self._generate_inception_response(user_input)
        
        # プロジェクト更新提案（キーワード抽出ベース）
        project_updates = self._extract_project_updates_inception(user_input)
        
        next_actions = [
            "プロジェクトの目的をより具体的に教えてください",
            "想定している成果物や目標について聞かせてください",
            "制約条件（予算、期限、リソース）はありますか？"
        ]
        
        return ConversationResponse(
            content=content,
            phase=self.current_phase,
            suggested_actions=suggested_actions,
            project_updates=project_updates,
            next_actions=next_actions
        )
    
    def _handle_definition_conversation(self, user_input: str) -> ConversationResponse:
        """定義段階の会話処理"""
        
        suggested_actions = [
            {
                "type": "create_charter",
                "description": "プロジェクトチャーターの作成",
                "priority": "high"
            },
            {
                "type": "define_scope",
                "description": "プロジェクトスコープの定義",
                "priority": "high"
            },
            {
                "type": "risk_identification",
                "description": "初期リスクの特定",
                "priority": "medium"
            }
        ]
        
        content = self._generate_definition_response(user_input)
        project_updates = self._extract_project_updates_definition(user_input)
        
        next_actions = [
            "機能要件について詳しく教えてください",
            "技術的な制約や要件はありますか？",
            "プロジェクトチャーターの作成を進めましょうか？"
        ]
        
        return ConversationResponse(
            content=content,
            phase=self.current_phase,
            suggested_actions=suggested_actions,
            project_updates=project_updates,
            next_actions=next_actions
        )
    
    def _handle_planning_conversation(self, user_input: str) -> ConversationResponse:
        """計画段階の会話処理"""
        
        suggested_actions = [
            {
                "type": "create_wbs",
                "description": "作業分解構造の作成",
                "priority": "high"
            },
            {
                "type": "schedule_planning",
                "description": "スケジュール計画",
                "priority": "high"
            },
            {
                "type": "resource_planning",
                "description": "リソース計画",
                "priority": "medium"
            }
        ]
        
        content = self._generate_planning_response(user_input)
        project_updates = self._extract_project_updates_planning(user_input)
        
        next_actions = [
            "タスクの詳細と依存関係を整理しましょう",
            "各タスクの工数見積もりをしてください",
            "リソースの割り当てを決めましょう"
        ]
        
        return ConversationResponse(
            content=content,
            phase=self.current_phase,
            suggested_actions=suggested_actions,
            project_updates=project_updates,
            next_actions=next_actions
        )
    
    def _handle_execution_conversation(self, user_input: str) -> ConversationResponse:
        """実行段階の会話処理"""
        
        # 現在のタスク状況を取得
        current_tasks = self.project_data.get("tasks", [])
        active_tasks = [t for t in current_tasks if isinstance(t, dict) and t.get("status") not in ["完了", "COMPLETED"]]
        
        suggested_actions = [
            {
                "type": "track_progress",
                "description": "進捗の追跡と更新",
                "priority": "high"
            },
            {
                "type": "resolve_issues",
                "description": "課題・ブロッカーの解決",
                "priority": "high"
            },
            {
                "type": "update_timeline",
                "description": "スケジュールの調整",
                "priority": "medium"
            }
        ]
        
        content = self._generate_execution_response(user_input, active_tasks)
        project_updates = self._extract_project_updates_execution(user_input)
        
        next_actions = [
            "現在の作業状況を教えてください",
            "何か課題やブロッカーはありませんか？",
            "次に優先すべきタスクは何ですか？"
        ]
        
        return ConversationResponse(
            content=content,
            phase=self.current_phase,
            suggested_actions=suggested_actions,
            project_updates=project_updates,
            next_actions=next_actions
        )
    
    def _handle_monitoring_conversation(self, user_input: str) -> ConversationResponse:
        """監視段階の会話処理"""
        
        suggested_actions = [
            {
                "type": "quality_review",
                "description": "品質レビューの実施",
                "priority": "high"
            },
            {
                "type": "stakeholder_communication",
                "description": "ステークホルダーとのコミュニケーション",
                "priority": "medium"
            }
        ]
        
        content = self._generate_monitoring_response(user_input)
        project_updates = []
        
        next_actions = [
            "成果物の品質はいかがですか？",
            "ステークホルダーからのフィードバックはありますか？"
        ]
        
        return ConversationResponse(
            content=content,
            phase=self.current_phase,
            suggested_actions=suggested_actions,
            project_updates=project_updates,
            next_actions=next_actions
        )
    
    def _handle_closure_conversation(self, user_input: str) -> ConversationResponse:
        """完了段階の会話処理"""
        
        suggested_actions = [
            {
                "type": "final_review",
                "description": "最終レビューの実施",
                "priority": "high"
            },
            {
                "type": "documentation",
                "description": "最終ドキュメント作成",
                "priority": "medium"
            }
        ]
        
        content = self._generate_closure_response(user_input)
        project_updates = []
        
        next_actions = [
            "プロジェクトのアーカイブ準備をしましょう",
            "学んだことや改善点をまとめましょう"
        ]
        
        return ConversationResponse(
            content=content,
            phase=self.current_phase,
            suggested_actions=suggested_actions,
            project_updates=project_updates,
            next_actions=next_actions
        )
    
    def _handle_generic_conversation(self, user_input: str) -> ConversationResponse:
        """汎用会話処理（フォールバック）"""
        
        content = f"プロジェクト '{self.project_data.get('overview', 'Unknown')}' について、どのようなサポートが必要でしょうか？"
        
        return ConversationResponse(
            content=content,
            phase=self.current_phase,
            suggested_actions=[],
            project_updates=[],
            next_actions=["プロジェクトの現状を教えてください"]
        )
    
    def _get_project_context(self) -> str:
        """プロジェクトコンテキストの生成"""
        overview = self.project_data.get("overview", "概要未設定")
        status = self.project_data.get("status", "DRAFT")
        completion = self.project_data.get("completion_percentage", 0)
        
        # Safe conversion for completion percentage
        if isinstance(completion, str):
            try:
                completion = float(completion)
            except (ValueError, TypeError):
                completion = 0.0
        elif not isinstance(completion, (int, float)):
            completion = 0.0
        
        return f"""あなたはプロジェクトマネージャーのAIアシスタントです。

現在のプロジェクト情報：
- プロジェクト名: {self.project_id}
- 概要: {overview}
- ステータス: {status}
- 現在フェーズ: {self.current_phase.value}
- 完了率: {completion:.1f}%"""
    
    def _get_phase_specific_context(self) -> str:
        """フェーズ特化型コンテキストの生成"""
        phase_contexts = {
            ProjectPhase.INCEPTION: """現在は構想段階です。プロジェクトの目的、背景、基本要件を明確化することが重要です。
以下の観点で質問や提案を行ってください：
1. プロジェクトの目的と価値
2. ステークホルダーの特定
3. 基本的な制約条件
4. 成功の定義""",
            
            ProjectPhase.DEFINITION: """現在は定義段階です。プロジェクトの詳細仕様と要件を固めることが重要です。
以下の観点で支援してください：
1. 機能要件と非機能要件の整理
2. プロジェクトスコープの明確化
3. 技術的制約の確認
4. リスクの初期評価""",
            
            ProjectPhase.PLANNING: """現在は計画段階です。具体的な実行計画を策定することが重要です。
以下の観点で支援してください：
1. 作業分解構造（WBS）の作成
2. スケジュールとマイルストーンの設定
3. リソース計画
4. リスク対応計画""",
            
            ProjectPhase.EXECUTION: """現在は実行段階です。計画された作業を実行し、進捗を管理することが重要です。
以下の観点で支援してください：
1. 進捗の追跡と報告
2. 課題とブロッカーの解決
3. 品質管理
4. ステークホルダーとのコミュニケーション""",
            
            ProjectPhase.MONITORING: """現在は監視段階です。成果物の品質確認と最終調整を行うことが重要です。
以下の観点で支援してください：
1. 成果物の品質レビュー
2. ステークホルダーからのフィードバック収集
3. 最終調整の実施
4. 完了準備""",
            
            ProjectPhase.CLOSURE: """現在は完了段階です。プロジェクトの正式な終了処理を行うことが重要です。
以下の観点で支援してください：
1. 最終成果物の確認
2. プロジェクト完了報告書の作成
3. 学習事項のまとめ
4. リソースの解放とアーカイブ"""
        }
        
        return phase_contexts.get(self.current_phase, "プロジェクトの進行をサポートします。")
    
    # 簡易的な応答生成メソッド（実際の実装ではOpenAI APIを使用）
    def _generate_inception_response(self, user_input: str) -> str:
        """構想段階の応答生成"""
        return f"「{user_input}」について理解しました。このプロジェクトの目的をより具体的に教えていただけますか？また、誰がこのプロジェクトから恩恵を受けるのでしょうか？"
    
    def _generate_definition_response(self, user_input: str) -> str:
        """定義段階の応答生成"""
        return f"「{user_input}」について、技術的な詳細を整理していきましょう。この機能を実現するために必要な要件や制約はありますか？"
    
    def _generate_planning_response(self, user_input: str) -> str:
        """計画段階の応答生成"""
        return f"「{user_input}」について、具体的な作業計画を立てていきましょう。このタスクの工数見積もりと依存関係を教えてください。"
    
    def _generate_execution_response(self, user_input: str, active_tasks: List[Dict]) -> str:
        """実行段階の応答生成"""
        task_count = len(active_tasks)
        return f"「{user_input}」について承知しました。現在{task_count}個のアクティブなタスクがあります。進捗状況や課題について詳しく教えてください。"
    
    def _generate_monitoring_response(self, user_input: str) -> str:
        """監視段階の応答生成"""
        return f"「{user_input}」について、品質面での確認を行いましょう。成果物は期待される品質水準に達していますか？"
    
    def _generate_closure_response(self, user_input: str) -> str:
        """完了段階の応答生成"""
        return f"プロジェクト完了に向けて「{user_input}」を整理していきましょう。最終確認事項はありますか？"
    
    # 簡易的なプロジェクト更新抽出（実際の実装ではより高度なNLP処理）
    def _extract_project_updates_inception(self, user_input: str) -> List[Dict[str, Any]]:
        """構想段階のプロジェクト更新抽出"""
        updates = []
        
        # キーワードベースの簡易抽出
        if "目的" in user_input or "目標" in user_input:
            updates.append({
                "field": "purpose",
                "value": user_input,
                "confidence": 0.7
            })
        
        return updates
    
    def _extract_project_updates_definition(self, user_input: str) -> List[Dict[str, Any]]:
        """定義段階のプロジェクト更新抽出"""
        updates = []
        
        # 機能や要件に関する情報を抽出
        if "機能" in user_input or "要件" in user_input:
            updates.append({
                "field": "requirements",
                "value": user_input,
                "confidence": 0.8
            })
        
        return updates
    
    def _extract_project_updates_planning(self, user_input: str) -> List[Dict[str, Any]]:
        """計画段階のプロジェクト更新抽出"""
        updates = []
        
        # タスクやスケジュールに関する情報を抽出
        if "タスク" in user_input:
            updates.append({
                "field": "tasks",
                "value": user_input,
                "confidence": 0.9
            })
        
        return updates
    
    def _extract_project_updates_execution(self, user_input: str) -> List[Dict[str, Any]]:
        """実行段階のプロジェクト更新抽出"""
        updates = []
        
        # 進捗や課題に関する情報を抽出
        if "完了" in user_input or "終了" in user_input:
            updates.append({
                "field": "task_completion",
                "value": user_input,
                "confidence": 0.9
            })
        
        if "課題" in user_input or "問題" in user_input or "エラー" in user_input or "障害" in user_input:
            updates.append({
                "field": "blocking_issues",
                "value": user_input,
                "confidence": 0.8
            })
        
        return updates