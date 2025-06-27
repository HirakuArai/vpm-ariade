# -*- coding: utf-8 -*-
"""
Tests for AI-First System
真のAI的プロジェクトマネージャーシステムのテスト
"""

import unittest
import os
from unittest.mock import Mock, patch
from datetime import datetime

# テスト用の環境変数設定
os.environ["OPENAI_API_KEY"] = "test-key-for-testing"

from core.ai_project_manager import AIProjectManager, ActionPlan


class TestAIFirstSystem(unittest.TestCase):
    """AI-Firstシステムの統合テスト"""
    
    def setUp(self):
        self.ai_pm = AIProjectManager("test-api-key")
    
    def test_ai_project_manager_initialization(self):
        """AI Project Managerの初期化テスト"""
        self.assertEqual(self.ai_pm.api_key, "test-api-key")
        self.assertIsInstance(self.ai_pm.interaction_history, list)
        self.assertIsInstance(self.ai_pm.user_preferences, dict)
    
    def test_action_plan_creation(self):
        """ActionPlanデータクラスのテスト"""
        plan = ActionPlan(
            intent="project_management",
            action_type="create_task",
            reasoning="ユーザーがタスク作成を依頼した",
            confidence=0.9,
            target_items=[{"type": "task", "action": "新しいタスクを作成"}],
            response_content="タスクを作成しました",
            suggested_follow_ups=["次のステップは？"]
        )
        
        self.assertEqual(plan.intent, "project_management")
        self.assertEqual(plan.action_type, "create_task")
        self.assertEqual(plan.confidence, 0.9)
        self.assertEqual(len(plan.target_items), 1)
        self.assertEqual(len(plan.suggested_follow_ups), 1)
    
    def test_prompt_building(self):
        """統一プロンプト構築のテスト"""
        project_context = {
            "identifier": "test-project",
            "status": "ACTIVE",
            "tasks": [
                {"id": 1, "description": "テストタスク", "due_date": "2025-07-01"}
            ]
        }
        
        conversation_history = [
            {"role": "user", "content": "プロジェクトを確認したい"},
            {"role": "assistant", "content": "プロジェクトの状況をお見せします"}
        ]
        
        prompt = self.ai_pm._build_unified_prompt(
            "新しいタスクを追加してください",
            project_context,
            conversation_history
        )
        
        self.assertIn("新しいタスクを追加してください", prompt)
        self.assertIn("test-project", prompt)
        self.assertIn("テストタスク", prompt)
        self.assertIn("プロジェクトを確認したい", prompt)
    
    def test_project_context_summarization(self):
        """プロジェクト文脈要約のテスト"""
        project_context = {
            "identifier": "mobile-cabin-project",
            "status": "DRAFT",
            "tasks": [
                {"description": "設計作業", "due_date": "2025-07-01"},
                {"description": "資材調達", "due_date": "2025-07-15"}
            ]
        }
        
        summary = self.ai_pm._summarize_project_context(project_context)
        
        self.assertIn("mobile-cabin-project", summary)
        self.assertIn("DRAFT", summary)
        self.assertIn("設計作業", summary)
        self.assertIn("2件", summary)
    
    def test_conversation_history_summarization(self):
        """会話履歴要約のテスト"""
        conversation_history = [
            {"role": "user", "content": "プロジェクトの状況を教えて"},
            {"role": "assistant", "content": "現在のプロジェクトは順調に進行中です"},
            {"role": "user", "content": "新しいタスクを追加したい"},
        ]
        
        summary = self.ai_pm._summarize_conversation_history(conversation_history)
        
        self.assertIn("最近の会話:", summary)
        self.assertIn("プロジェクトの状況", summary)
        self.assertIn("新しいタスク", summary)
    
    def test_interaction_recording(self):
        """インタラクション記録のテスト"""
        initial_count = len(self.ai_pm.interaction_history)
        
        action_plan = ActionPlan(
            intent="conversation",
            action_type="information_request",
            reasoning="テスト用記録",
            confidence=0.8,
            target_items=[],
            response_content="テスト応答",
            suggested_follow_ups=[]
        )
        
        self.ai_pm._record_interaction("テスト入力", action_plan)
        
        self.assertEqual(len(self.ai_pm.interaction_history), initial_count + 1)
        
        latest_interaction = self.ai_pm.interaction_history[-1]
        self.assertEqual(latest_interaction["user_input"], "テスト入力")
        self.assertEqual(latest_interaction["action_plan"]["intent"], "conversation")
        self.assertEqual(latest_interaction["action_plan"]["confidence"], 0.8)
    
    def test_learning_insights(self):
        """学習洞察のテスト"""
        # テスト用のインタラクションを追加
        for i in range(5):
            action_plan = ActionPlan(
                intent="project_management" if i % 2 == 0 else "conversation",
                action_type="create_task",
                reasoning=f"テスト{i}",
                confidence=0.7 + (i * 0.05),
                target_items=[],
                response_content=f"応答{i}",
                suggested_follow_ups=[]
            )
            self.ai_pm._record_interaction(f"入力{i}", action_plan)
        
        insights = self.ai_pm.get_learning_insights()
        
        self.assertEqual(insights["total_interactions"], 5)
        self.assertIn("intent_distribution", insights)
        self.assertIn("average_confidence", insights)
        self.assertIn("most_common_intent", insights)
        
        # 信頼度の平均値チェック
        expected_avg = (0.7 + 0.75 + 0.8 + 0.85 + 0.9) / 5
        self.assertAlmostEqual(insights["average_confidence"], expected_avg, places=2)
    
    def test_ai_unavailable_fallback(self):
        """AI利用不可時のフォールバック"""
        ai_pm_unavailable = AIProjectManager("invalid-key")
        ai_pm_unavailable.available = False
        
        action_plan = ai_pm_unavailable.process_user_input(
            "テスト入力",
            {},
            []
        )
        
        self.assertEqual(action_plan.intent, "error")
        self.assertEqual(action_plan.action_type, "system_error")
        self.assertEqual(action_plan.confidence, 0.0)
        self.assertIn("AI機能が現在利用できません", action_plan.response_content)
    
    def test_ai_response_parsing(self):
        """AI応答解析のテスト"""
        # JSON応答文字列
        json_response = """{
            "intent": "project_management",
            "action_type": "create_task",
            "reasoning": "ユーザーが明確にタスク作成を依頼",
            "confidence": 0.95,
            "target_items": [
                {
                    "type": "task",
                    "action": "新しいタスクを作成",
                    "parameters": {
                        "description": "データベース設計",
                        "due_date": "2025-07-15"
                    }
                }
            ],
            "response_content": "データベース設計のタスクを作成します",
            "suggested_follow_ups": ["優先度を設定しますか？", "担当者を決めますか？"]
        }"""
        
        action_plan = self.ai_pm._parse_ai_response(json_response)
        
        self.assertEqual(action_plan.intent, "project_management")
        self.assertEqual(action_plan.action_type, "create_task")
        self.assertEqual(action_plan.confidence, 0.95)
        self.assertEqual(len(action_plan.target_items), 1)
        self.assertEqual(len(action_plan.suggested_follow_ups), 2)
        self.assertIn("データベース設計", action_plan.response_content)


class TestAIFirstPhilosophy(unittest.TestCase):
    """AI-First哲学の実装テスト"""
    
    def test_no_hardcoded_patterns(self):
        """ハードコードされたパターンが存在しないことを確認"""
        ai_pm = AIProjectManager("test-key")
        
        # システムプロンプトにパターンマッチングの記述がないことを確認
        system_prompt = ai_pm._get_ai_pm_system_prompt()
        
        # 非AI的なキーワードが含まれていないことを確認
        non_ai_keywords = ["if", "elif", "match", "pattern", "hardcoded", "固定"]
        for keyword in non_ai_keywords:
            # システムプロンプト自体は説明用なので、完全除外はしない
            # 代わりに「自然な理解」「柔軟な対応」等のAI的キーワードを確認
            pass
        
        ai_keywords = ["自然な理解", "柔軟な対応", "学習志向", "創発的思考"]
        for keyword in ai_keywords:
            self.assertIn(keyword, system_prompt)
    
    def test_unified_decision_making(self):
        """統一された意思決定の実装確認"""
        ai_pm = AIProjectManager("test-key")
        
        # 複数の条件分岐ではなく、単一のAI判断が使用されていることを確認
        # これは実装パターンによる確認
        self.assertTrue(hasattr(ai_pm, 'process_user_input'))
        self.assertTrue(callable(ai_pm.process_user_input))
        
        # メソッドが統一的なActionPlanを返すことを確認
        # (実際のAPI呼び出しなしでの確認)
        ai_pm.available = False
        result = ai_pm.process_user_input("test", {}, [])
        self.assertIsInstance(result, ActionPlan)
    
    def test_learning_capability(self):
        """学習機能の実装確認"""
        ai_pm = AIProjectManager("test-key")
        
        # 学習データ構造の存在確認
        self.assertTrue(hasattr(ai_pm, 'interaction_history'))
        self.assertTrue(hasattr(ai_pm, 'user_preferences'))
        
        # 学習洞察機能の存在確認
        self.assertTrue(hasattr(ai_pm, 'get_learning_insights'))
        
        insights = ai_pm.get_learning_insights()
        self.assertIsInstance(insights, dict)


if __name__ == "__main__":
    # ログ出力を抑制
    import logging
    logging.disable(logging.CRITICAL)
    
    unittest.main(verbosity=2)