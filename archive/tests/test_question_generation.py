#!/usr/bin/env python3
"""
Question Generation Integration Test
質問生成・タイミング制御機能の統合テスト
"""

import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.question_generator import (
    AdaptiveQuestionGenerator, 
    create_conversation_context,
    Question, QuestionType, QuestionUrgency
)
from core.dynamic_schema import get_project_schema
from core.models import ProjectPhase

def test_question_generation():
    """質問生成機能のテスト"""
    print("❓ Testing Adaptive Question Generation...")
    
    # OpenAI API キーの確認
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("⚠️ OPENAI_API_KEY not found. Testing with fallback generation.")
    
    # 既存プロジェクトのスキーマを使用
    project_id = "proj-20250618-075700-122"
    schema = get_project_schema(project_id)
    
    # テスト用会話文脈
    test_messages = [
        {"role": "user", "content": "八ヶ岳登山について相談したいです"},
        {"role": "assistant", "content": "八ヶ岳登山の計画ですね。どのような登山を予定していますか？"},
        {"role": "user", "content": "友人と一緒に行く予定です"},
        {"role": "assistant", "content": "友人との登山ですね。楽しそうです！"}
    ]
    
    # 会話文脈を作成
    session_start = datetime.now() - timedelta(minutes=5)
    context = create_conversation_context(
        test_messages, 
        ProjectPhase.DEFINITION, 
        session_start
    )
    
    print(f"📊 Context created:")
    print(f"  - Messages: {context.conversation_length}")
    print(f"  - Engagement: {context.user_engagement_level:.2f}")
    print(f"  - Session duration: {context.session_duration} minutes")
    
    # 質問生成器を作成
    generator = AdaptiveQuestionGenerator(api_key)
    
    try:
        # 質問生成
        questions = generator.generate_contextual_questions(
            schema, context, max_questions=3
        )
        
        print(f"\n✅ Generated {len(questions)} questions:")
        
        for i, question in enumerate(questions, 1):
            print(f"\n--- Question {i} ---")
            print(f"🎯 Field: {question.field_name}")
            print(f"❓ Text: {question.text}")
            print(f"🔥 Urgency: {question.urgency.value}")
            print(f"📝 Type: {question.question_type.value}")
            print(f"🔒 Confidence: {question.confidence:.2f}")
            
            if question.prerequisites:
                print(f"📋 Prerequisites: {', '.join(question.prerequisites)}")
        
        # タイミング判定テスト
        print(f"\n⏰ Testing timing determination...")
        
        timed_questions = generator.determine_question_timing(questions, context)
        
        print(f"✅ {len(timed_questions)} questions approved for current timing")
        
        for question in timed_questions:
            urgency_icon = "🔥" if question.urgency.value == "immediate" else "📝"
            print(f"  {urgency_icon} {question.text}")
        
    except Exception as e:
        print(f"❌ Question generation failed: {e}")
        import traceback
        traceback.print_exc()

def test_timing_conditions():
    """タイミング制御のテスト"""
    print("\n⏰ Testing Question Timing Conditions...")
    
    generator = AdaptiveQuestionGenerator()
    
    # 様々な条件でのテストケース
    test_cases = [
        {
            "name": "Fresh session - High engagement",
            "answered_questions": 1,
            "engagement": 0.8,
            "session_minutes": 3,
            "expected": True
        },
        {
            "name": "User fatigue - Many questions answered",
            "answered_questions": 6,
            "engagement": 0.7,
            "session_minutes": 10,
            "expected": False
        },
        {
            "name": "Low engagement",
            "answered_questions": 2,
            "engagement": 0.4,
            "session_minutes": 5,
            "expected": False
        },
        {
            "name": "Long session - Moderate engagement",
            "answered_questions": 3,
            "engagement": 0.7,
            "session_minutes": 15,
            "expected": True
        }
    ]
    
    for test_case in test_cases:
        print(f"\n📋 Test: {test_case['name']}")
        
        # テスト用文脈を作成
        session_start = datetime.now() - timedelta(minutes=test_case["session_minutes"])
        
        # ダミーメッセージを作成
        messages = []
        for i in range(test_case["answered_questions"]):
            messages.extend([
                {"role": "user", "content": f"テスト回答 {i+1}"},
                {"role": "assistant", "content": f"テスト質問 {i+1}？"}
            ])
        
        context = create_conversation_context(messages, ProjectPhase.DEFINITION, session_start)
        context.user_engagement_level = test_case["engagement"]
        
        # ダミー質問を作成
        test_question = Question(
            id="test_question",
            field_name="test_field",
            text="テスト質問ですか？",
            question_type=QuestionType.INFORMATION,
            urgency=QuestionUrgency.SOON,
            context="test",
            prerequisites=[],
            follow_up_fields=[],
            created_at=datetime.now().isoformat(),
            confidence=0.8
        )
        
        # タイミング判定
        timed_questions = generator.determine_question_timing([test_question], context)
        
        should_ask = len(timed_questions) > 0
        result = "✅ PASS" if should_ask == test_case["expected"] else "❌ FAIL"
        
        print(f"  Expected: {'Ask' if test_case['expected'] else 'Skip'}")
        print(f"  Actual: {'Ask' if should_ask else 'Skip'}")
        print(f"  Result: {result}")

def test_question_enhancement():
    """質問改善機能のテスト"""
    print("\n✨ Testing Question Enhancement...")
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("⚠️ OPENAI_API_KEY not found. Skipping AI enhancement test.")
        return
    
    generator = AdaptiveQuestionGenerator(api_key)
    
    # テスト用プロジェクトスキーマ
    project_id = "proj-20250618-075700-122"
    schema = get_project_schema(project_id)
    
    # 登山に関する会話文脈
    context_messages = [
        {"role": "user", "content": "八ヶ岳の赤岳に登山したいと思っています"},
        {"role": "assistant", "content": "赤岳は八ヶ岳の最高峰ですね。素晴らしい選択です！"},
        {"role": "user", "content": "初心者も含めた登山になる予定です"},
        {"role": "assistant", "content": "初心者の方もいらっしゃるんですね。安全に配慮した計画が重要です。"}
    ]
    
    context = create_conversation_context(
        context_messages, 
        ProjectPhase.DEFINITION,
        datetime.now() - timedelta(minutes=8)
    )
    
    try:
        print("🔍 Generating enhanced questions...")
        
        questions = generator.generate_contextual_questions(
            schema, context, max_questions=2
        )
        
        if questions:
            print(f"✅ Generated {len(questions)} context-aware questions:")
            
            for i, question in enumerate(questions, 1):
                print(f"\n{i}. {question.text}")
                print(f"   📊 Field: {question.field_name}")
                print(f"   🎯 Type: {question.question_type.value}")
                print(f"   ⚡ Urgency: {question.urgency.value}")
        else:
            print("❌ No questions generated")
            
    except Exception as e:
        print(f"❌ Enhancement test failed: {e}")

def test_end_to_end_flow():
    """エンドツーエンドフローのテスト"""
    print("\n🔄 Testing End-to-End Question Flow...")
    
    api_key = os.getenv("OPENAI_API_KEY")
    project_id = "proj-20250618-075700-122"
    
    # 実際の会話フローをシミュレート
    conversation_turns = [
        {
            "user": "登山の装備について相談したいです",
            "expected_topics": ["budget", "accommodation", "route_preference"]
        },
        {
            "user": "予算は一人15万円程度を考えています",
            "expected_topics": ["accommodation", "timeline"]
        },
        {
            "user": "8月のお盆休みに実施予定です",
            "expected_topics": ["accommodation", "route_preference"]
        }
    ]
    
    generator = AdaptiveQuestionGenerator(api_key)
    schema = get_project_schema(project_id)
    
    accumulated_messages = []
    session_start = datetime.now()
    
    for turn_num, turn in enumerate(conversation_turns, 1):
        print(f"\n--- Turn {turn_num} ---")
        print(f"👤 User: {turn['user']}")
        
        # メッセージを蓄積
        accumulated_messages.extend([
            {"role": "user", "content": turn['user']},
            {"role": "assistant", "content": f"ターン{turn_num}の応答"}
        ])
        
        # 文脈を作成
        context = create_conversation_context(
            accumulated_messages,
            ProjectPhase.DEFINITION,
            session_start
        )
        
        try:
            # 質問生成
            questions = generator.generate_contextual_questions(
                schema, context, max_questions=2
            )
            
            # タイミング判定
            timed_questions = generator.determine_question_timing(questions, context)
            
            if timed_questions:
                print(f"🤖 Generated {len(timed_questions)} follow-up questions:")
                for q in timed_questions:
                    urgency = "🔥" if q.urgency.value == "immediate" else "📝"
                    print(f"   {urgency} {q.text}")
                    
                # 期待されるトピックが含まれているかチェック
                generated_fields = [q.field_name for q in timed_questions]
                relevant_fields = [f for f in generated_fields if f in turn["expected_topics"]]
                
                if relevant_fields:
                    print(f"✅ Relevant topics generated: {', '.join(relevant_fields)}")
                else:
                    print(f"⚠️ Expected topics not found: {', '.join(turn['expected_topics'])}")
            else:
                print("🤖 No questions generated for this turn")
                
        except Exception as e:
            print(f"❌ Turn {turn_num} failed: {e}")

def main():
    """メインテスト実行"""
    print("🚀 Question Generation Integration Test")
    print("=" * 70)
    
    try:
        # 1. 基本的な質問生成テスト
        test_question_generation()
        
        # 2. タイミング制御テスト
        test_timing_conditions()
        
        # 3. 質問改善テスト
        test_question_enhancement()
        
        # 4. エンドツーエンドフローテスト
        test_end_to_end_flow()
        
        print("\n" + "=" * 70)
        print("🎉 All question generation tests completed!")
        
    except Exception as e:
        print(f"\n❌ Test suite failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()