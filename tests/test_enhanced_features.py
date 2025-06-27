# -*- coding: utf-8 -*-
"""
Tests for Enhanced AI and UI Features
拡張AI機能とUIコンポーネントのテスト
"""

import unittest
import os
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

# テスト用の環境変数設定
os.environ["OPENAI_API_KEY"] = "test-key-for-testing"

from core.ai_context_manager import AIContextManager, ConversationContext
from core.ai_quality_manager import AIQualityManager, AIResponse, ResponseQuality, ErrorType


class TestAIContextManager(unittest.TestCase):
    """AIコンテキスト管理のテスト"""
    
    def setUp(self):
        self.context_manager = AIContextManager("test-api-key")
    
    def test_conversation_id_generation(self):
        """会話ID生成のテスト"""
        timestamp = datetime.now()
        conv_id = self.context_manager.generate_conversation_id("test-project", timestamp)
        
        self.assertIsInstance(conv_id, str)
        self.assertEqual(len(conv_id), 12)
    
    def test_token_estimation(self):
        """トークン数推定のテスト"""
        test_text = "This is a test message with several words"
        token_count = self.context_manager.estimate_token_count(test_text)
        
        self.assertGreater(token_count, 0)
        self.assertIsInstance(token_count, float)
    
    def test_add_conversation(self):
        """会話追加のテスト"""
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"}
        ]
        
        conv_id = self.context_manager.add_conversation("test-project", messages)
        
        self.assertIn(conv_id, self.context_manager.contexts)
        context = self.context_manager.contexts[conv_id]
        self.assertEqual(context.project_id, "test-project")
        self.assertEqual(len(context.messages), 2)
    
    def test_relevance_score_calculation(self):
        """関連性スコア計算のテスト"""
        context = ConversationContext(
            project_id="test-project",
            conversation_id="test-conv",
            messages=[{"role": "user", "content": "test message"}],
            summary="Test conversation about project planning"
        )
        
        # 同じプロジェクトの場合
        score1 = self.context_manager.calculate_relevance_score(
            context, "project planning", "test-project"
        )
        
        # 異なるプロジェクトの場合
        score2 = self.context_manager.calculate_relevance_score(
            context, "project planning", "other-project"
        )
        
        self.assertGreater(score1, score2)
        self.assertLessEqual(score1, 1.0)
        self.assertGreaterEqual(score2, 0.0)


class TestAIQualityManager(unittest.TestCase):
    """AI品質管理のテスト"""
    
    def setUp(self):
        self.quality_manager = AIQualityManager("test-api-key")
    
    def test_request_id_generation(self):
        """リクエストID生成のテスト"""
        prompt = "Test prompt for ID generation"
        req_id = self.quality_manager.generate_request_id(prompt)
        
        self.assertIsInstance(req_id, str)
        self.assertEqual(len(req_id), 12)
    
    def test_error_response_creation(self):
        """エラー応答作成のテスト"""
        error_response = self.quality_manager._create_error_response(
            "test-id", "test prompt", "Test error", ErrorType.API_ERROR
        )
        
        self.assertEqual(error_response.request_id, "test-id")
        self.assertEqual(error_response.quality_level, ResponseQuality.ERROR)
        self.assertEqual(error_response.error_type, ErrorType.API_ERROR)
        self.assertEqual(error_response.error_message, "Test error")
    
    def test_response_quality_evaluation(self):
        """応答品質評価のテスト"""
        # 高品質応答のテスト
        good_response = AIResponse(
            request_id="test-1",
            prompt="test prompt",
            response="This is a comprehensive and helpful response with good length and quality.",
            model="gpt-4",
            timestamp=datetime.now(),
            response_time=2.0,
            token_count=50
        )
        
        self.quality_manager._evaluate_response_quality(good_response)
        
        self.assertIsNotNone(good_response.quality_score)
        self.assertGreater(good_response.quality_score, 0.7)
        self.assertIn(good_response.quality_level, [
            ResponseQuality.GOOD, ResponseQuality.EXCELLENT
        ])
        
        # 低品質応答のテスト
        poor_response = AIResponse(
            request_id="test-2",
            prompt="test prompt",
            response="Bad",  # 短すぎる応答
            model="gpt-4",
            timestamp=datetime.now(),
            response_time=15.0,  # 遅い応答
            token_count=5,
            retry_count=2  # 複数回リトライ
        )
        
        self.quality_manager._evaluate_response_quality(poor_response)
        
        self.assertIsNotNone(poor_response.quality_score)
        self.assertLess(poor_response.quality_score, 0.7)
        self.assertEqual(poor_response.quality_level, ResponseQuality.POOR)
    
    def test_json_validation(self):
        """JSON検証のテスト"""
        # 有効なJSON
        valid_json = '{"key": "value", "number": 42}'
        self.assertTrue(self.quality_manager._is_valid_json(valid_json))
        
        # 無効なJSON
        invalid_json = '{"key": "value", "incomplete"'
        self.assertFalse(self.quality_manager._is_valid_json(invalid_json))
    
    def test_quality_report_generation(self):
        """品質レポート生成のテスト"""
        # テスト用の応答データを追加
        test_response = AIResponse(
            request_id="test-report",
            prompt="test",
            response="test response",
            model="gpt-4",
            timestamp=datetime.now(),
            response_time=3.0,
            token_count=20,
            quality_score=0.8,
            quality_level=ResponseQuality.GOOD
        )
        
        self.quality_manager.responses["test-report"] = test_response
        self.quality_manager._update_metrics(success=True, response_time=3.0)
        
        report = self.quality_manager.get_quality_report()
        
        self.assertIn("metrics", report)
        self.assertIn("recent_errors", report)
        self.assertIn("quality_distribution", report)
        self.assertIn("report_generated_at", report)
        
        # メトリクスの内容確認
        metrics = report["metrics"]
        self.assertGreater(metrics["total_requests"], 0)
        self.assertGreaterEqual(metrics["average_quality_score"], 0)
    
    def test_recommendations_generation(self):
        """推奨事項生成のテスト"""
        # メトリクスを初期化（良好な状態）
        self.quality_manager.metrics.error_rate = 0.0
        self.quality_manager.metrics.average_response_time = 3.0
        self.quality_manager.metrics.average_quality_score = 0.8
        self.quality_manager.metrics.last_24h_requests = 100
        
        # 正常状態
        recommendations = self.quality_manager.get_recommendations()
        self.assertIn("✅ システムは正常に動作しています。", recommendations)
        
        # エラー率が高い状態をシミュレート
        self.quality_manager.metrics.error_rate = 0.2
        recommendations = self.quality_manager.get_recommendations()
        
        error_recommendation = next(
            (rec for rec in recommendations if "エラー率が高い" in rec), 
            None
        )
        self.assertIsNotNone(error_recommendation)


class TestIntegration(unittest.TestCase):
    """統合テスト"""
    
    def test_context_and_quality_integration(self):
        """コンテキスト管理と品質管理の統合テスト"""
        context_mgr = AIContextManager("test-key")
        quality_mgr = AIQualityManager("test-key")
        
        # 会話を追加
        messages = [
            {"role": "user", "content": "プロジェクトについて教えて"},
            {"role": "assistant", "content": "プロジェクト管理について説明します..."}
        ]
        
        conv_id = context_mgr.add_conversation("test-project", messages)
        
        # コンテキストウィンドウを構築
        context_window = context_mgr.build_context_window(
            current_messages=[{"role": "user", "content": "新しい質問"}],
            current_query="新しい質問",
            project_id="test-project",
            system_prompt="あなたはプロジェクト管理の専門家です。"
        )
        
        self.assertIsNotNone(context_window)
        self.assertGreater(len(context_window.system_prompt), 0)
        self.assertGreaterEqual(context_window.total_tokens, 0)
        
        # 品質管理との連携確認
        self.assertEqual(len(context_mgr.contexts), 1)
        self.assertIn(conv_id, context_mgr.contexts)


if __name__ == "__main__":
    # ログ出力を抑制
    import logging
    logging.disable(logging.CRITICAL)
    
    unittest.main(verbosity=2)