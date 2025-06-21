#!/usr/bin/env python3
"""
Conversation Analysis Integration Test
会話分析機能の統合テスト
"""

import sys
import os
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.project_analyzer import ProjectContentAnalyzer, analyze_project_and_create_schema
from core.conversation_analyzer import ConversationAnalyzer, analyze_conversation_and_update_project
from core.dynamic_schema import get_project_schema

def test_project_analysis():
    """プロジェクト分析機能のテスト"""
    print("🔍 Testing Project Content Analysis...")
    
    # OpenAI API キーの確認
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("⚠️ OPENAI_API_KEY not found. Using fallback analysis.")
    
    # テストプロジェクト概要
    test_descriptions = [
        "地域の高齢者向けスマホ教室を企画します",
        "新しいWebアプリケーションを開発します", 
        "会社の忘年会を企画します"
    ]
    
    analyzer = ProjectContentAnalyzer(api_key)
    
    for i, description in enumerate(test_descriptions, 1):
        print(f"\n--- Test Case {i}: {description} ---")
        
        try:
            analysis = analyzer.analyze_project_description(description)
            
            print(f"✅ Project Type: {analysis.project_type}")
            print(f"📊 Complexity: {analysis.complexity.value}")
            print(f"🎯 Stakeholders: {', '.join(analysis.key_stakeholders[:3])}")
            print(f"📋 Required Fields: {len(analysis.required_fields)}")
            print(f"💡 Recommended Fields: {len(analysis.recommended_fields)}")
            print(f"🔒 Confidence: {analysis.confidence:.2f}")
            
            # 重要なフィールドを表示
            for field_name, field_info in list(analysis.required_fields.items())[:2]:
                questions = field_info.get("questions", [])
                print(f"  📝 {field_name}: {questions[0] if questions else 'No questions'}")
                
        except Exception as e:
            print(f"❌ Analysis failed: {e}")

def test_conversation_extraction():
    """会話情報抽出のテスト"""
    print("\n🗣️ Testing Conversation Information Extraction...")
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("⚠️ OPENAI_API_KEY not found. Using pattern-based extraction only.")
    
    # 既存プロジェクトのスキーマを使用
    project_id = "proj-20250618-075700-122"
    schema = get_project_schema(project_id)
    
    # テスト会話
    test_conversations = [
        [
            {"role": "user", "content": "予算は15万円以内で考えています"},
            {"role": "assistant", "content": "15万円の予算ですね。どのような内訳をお考えですか？"}
        ],
        [
            {"role": "user", "content": "宿泊は山小屋を希望します。テントは初心者には厳しそうなので"},
            {"role": "assistant", "content": "山小屋泊ですね。快適で安全です。"}
        ],
        [
            {"role": "user", "content": "8月15日から17日の2泊3日で考えています"},
            {"role": "assistant", "content": "お盆の時期ですね。山小屋の予約は早めにした方が良いでしょう。"}
        ]
    ]
    
    analyzer = ConversationAnalyzer(api_key)
    
    for i, conversation in enumerate(test_conversations, 1):
        print(f"\n--- Conversation Test {i} ---")
        
        try:
            # 情報抽出
            extracted = analyzer.extract_information_from_conversation(conversation, schema)
            
            print(f"📊 Extracted {len(extracted)} pieces of information:")
            for info in extracted:
                print(f"  📝 {info.field_name}: {info.value}")
                print(f"      🔒 Confidence: {info.confidence:.2f}")
                print(f"      🔧 Method: {info.extraction_method}")
                
            # 矛盾チェック
            conflicts = analyzer.detect_information_conflicts(extracted, schema)
            if conflicts:
                print(f"⚠️ Found {len(conflicts)} conflicts:")
                for conflict in conflicts:
                    print(f"  🔄 {conflict.field_name}: {conflict.existing_value} → {conflict.new_value}")
            else:
                print("✅ No conflicts detected")
                
        except Exception as e:
            print(f"❌ Extraction failed: {e}")

def test_end_to_end_workflow():
    """エンドツーエンドワークフローのテスト"""
    print("\n🔄 Testing End-to-End Workflow...")
    
    api_key = os.getenv("OPENAI_API_KEY")
    
    # 1. 新しいプロジェクトの分析とスキーマ作成
    test_project_id = "test-project-001"
    test_description = "大学のサークル向け合宿旅行を企画します"
    
    print(f"📋 Creating schema for: {test_description}")
    
    try:
        # プロジェクト分析
        analyzer = ProjectContentAnalyzer(api_key)
        analysis, schema_success = analyzer.analyze_and_initialize_project(
            test_project_id, test_description
        )
        
        if schema_success:
            print("✅ Schema created successfully")
            print(f"📊 Added {len(analysis.required_fields)} required fields")
            print(f"💡 Added {len(analysis.recommended_fields)} recommended fields")
        else:
            print("❌ Schema creation failed")
            return
        
        # 2. 会話による情報更新
        test_conversation = [
            {"role": "user", "content": "参加者は20名の予定です"},
            {"role": "assistant", "content": "20名の合宿ですね。宿泊施設の手配が重要になりそうです。"},
            {"role": "user", "content": "予算は一人当たり8000円で、総額16万円です"},
            {"role": "assistant", "content": "一人8000円で16万円の予算ですね。"},
            {"role": "user", "content": "9月の3連休を予定しています"},
            {"role": "assistant", "content": "9月の3連休でしたら、予約が混み合いそうですね。"}
        ]
        
        print("\n📞 Processing conversation...")
        
        # 会話分析と更新
        conv_analyzer = ConversationAnalyzer(api_key)
        schema = get_project_schema(test_project_id)
        
        extracted = conv_analyzer.extract_information_from_conversation(test_conversation, schema)
        applied_count, conflicts = conv_analyzer.apply_extracted_information(
            extracted, test_project_id
        )
        
        print(f"✅ Applied {applied_count} pieces of information")
        if conflicts:
            print(f"⚠️ {len(conflicts)} conflicts detected")
        
        # 3. 最終的なスキーマ状態を確認
        updated_schema = get_project_schema(test_project_id)
        completion = updated_schema.get_completion_percentage()
        
        print(f"\n📈 Final Project Status:")
        print(f"🎯 Completion: {completion:.1f}%")
        
        # 定義済みフィールドを表示
        for field_name, field in updated_schema.fields.items():
            if field.value is not None:
                print(f"  📝 {field_name}: {field.value}")
        
        # 残りの質問を表示
        pending_questions = updated_schema.get_pending_questions(max_questions=3)
        if pending_questions:
            print(f"\n❓ Remaining questions ({len(pending_questions)} groups):")
            for field_name, questions in pending_questions:
                print(f"  🎯 {field_name}: {questions[0]}")
        
        print("\n🎉 End-to-end test completed successfully!")
        
    except Exception as e:
        print(f"❌ End-to-end test failed: {e}")
        import traceback
        traceback.print_exc()

def main():
    """メインテスト実行"""
    print("🚀 Conversation Analysis Integration Test")
    print("=" * 70)
    
    try:
        # 1. プロジェクト分析テスト
        test_project_analysis()
        
        # 2. 会話抽出テスト
        test_conversation_extraction()
        
        # 3. エンドツーエンドテスト
        test_end_to_end_workflow()
        
        print("\n" + "=" * 70)
        print("🎉 All conversation analysis tests completed!")
        
    except Exception as e:
        print(f"\n❌ Test suite failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()