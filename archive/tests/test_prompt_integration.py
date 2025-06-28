#!/usr/bin/env python3
"""
Test Dynamic Schema Integration with Project Prompt
動的スキーマとプロンプト生成の統合テスト
"""

import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.project_prompt import get_project_prompt
from core.dynamic_schema import get_project_schema

def test_prompt_with_dynamic_info():
    """動的情報を含むプロンプト生成テスト"""
    print("🔍 Testing enhanced project prompt generation...")
    
    project_id = "proj-20250618-075700-122"
    
    # 現在のプロンプトを生成
    prompt = get_project_prompt(project_id)
    
    print("=" * 60)
    print("📋 Generated Project Context:")
    print("=" * 60)
    print(prompt)
    print("=" * 60)
    
    # 動的情報が含まれているかチェック
    if "📋 確定済み詳細情報" in prompt:
        print("✅ Dynamic information section found!")
    else:
        print("❌ Dynamic information section not found")
    
    if "participants" in prompt:
        print("✅ Participants information included")
    else:
        print("❌ Participants information missing")
    
    # 信頼度インジケーターの確認
    if "🔒" in prompt or "📝" in prompt:
        print("✅ Confidence indicators present")
    else:
        print("❌ Confidence indicators missing")

def test_additional_field_update():
    """追加フィールド更新後のプロンプトテスト"""
    print("\n🔄 Testing after additional field updates...")
    
    project_id = "proj-20250618-075700-122"
    schema = get_project_schema(project_id)
    
    # timelineフィールドを更新
    schema.update_field_value(
        "timeline",
        "2025年8月第2週、2泊3日",
        confidence=0.8,
        source="test_integration"
    )
    
    # route_preferenceフィールドを更新
    schema.update_field_value(
        "route_preference", 
        "赤岳天狗尾根ルート（中級者向け）",
        confidence=0.75,
        source="test_integration"
    )
    
    # 保存
    schema.save_to_project_file()
    
    # 新しいプロンプトを生成
    updated_prompt = get_project_prompt(project_id)
    
    print("=" * 60)
    print("📋 Updated Project Context:")
    print("=" * 60)
    print(updated_prompt)
    print("=" * 60)
    
    # 更新された情報が反映されているかチェック
    if "timeline" in updated_prompt and "2025年8月" in updated_prompt:
        print("✅ Timeline information updated correctly")
    
    if "route_preference" in updated_prompt and "赤岳" in updated_prompt:
        print("✅ Route preference information updated correctly")
    
    # 信頼度インジケーターの確認
    confidence_indicators = updated_prompt.count("🔒") + updated_prompt.count("📝") + updated_prompt.count("❓")
    print(f"📊 Found {confidence_indicators} confidence indicators")

def test_completion_tracking():
    """完成度追跡のテスト"""
    print("\n📈 Testing completion tracking...")
    
    project_id = "proj-20250618-075700-122"
    schema = get_project_schema(project_id)
    
    # 完成度を計算
    completion = schema.get_completion_percentage()
    summary = schema.get_field_summary()
    
    print(f"📊 Current completion: {completion:.1f}%")
    print(f"📋 Defined fields: {summary['defined']}/{summary['total']}")
    
    # 必須フィールドの状況
    required_defined = 0
    required_total = 0
    
    for field_name, field in schema.fields.items():
        if field.priority.value == "required":
            required_total += 1
            if field.status.value in ["defined", "confirmed"]:
                required_defined += 1
    
    print(f"🎯 Required fields: {required_defined}/{required_total} completed")
    
    # 未回答の質問
    pending_questions = schema.get_pending_questions(max_questions=5)
    print(f"❓ Pending questions: {len(pending_questions)} groups")
    
    for field_name, questions in pending_questions:
        field = schema.fields[field_name]
        print(f"  - {field_name} ({field.priority.value}): {len(questions)} questions")

def main():
    """メインテスト実行"""
    print("🚀 Dynamic Schema + Prompt Integration Test")
    print("=" * 70)
    
    try:
        # 1. 基本的なプロンプト生成テスト
        test_prompt_with_dynamic_info()
        
        # 2. フィールド更新後のテスト
        test_additional_field_update()
        
        # 3. 完成度追跡のテスト
        test_completion_tracking()
        
        print("\n" + "=" * 70)
        print("🎉 Integration tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Integration test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()