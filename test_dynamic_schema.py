#!/usr/bin/env python3
"""
Dynamic Schema Test Script
動的スキーマの基本機能テスト
"""

import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.dynamic_schema import DynamicProjectSchema, FieldPriority, FieldStatus, get_project_schema

def test_schema_loading():
    """既存プロジェクトからのスキーマ読み込みテスト"""
    print("🔍 Testing schema loading...")
    
    project_id = "proj-20250618-075700-122"
    schema = get_project_schema(project_id)
    
    print(f"✅ Loaded schema for project: {schema.project_id}")
    print(f"📊 Schema version: {schema.schema_version}")
    print(f"📅 Last analyzed: {schema.last_analyzed}")
    print(f"🗂️ Fields count: {len(schema.fields)}")
    
    # フィールド一覧表示
    for name, field in schema.fields.items():
        print(f"  - {name}: {field.priority.value}, {field.status.value}")
        if field.questions:
            for i, q in enumerate(field.questions[:2]):  # 最初の2つだけ表示
                print(f"    Q{i+1}: {q}")
    
    return schema

def test_pending_questions(schema):
    """質問取得機能のテスト"""
    print("\n❓ Testing pending questions...")
    
    pending = schema.get_pending_questions(max_questions=3)
    print(f"📝 Found {len(pending)} pending question groups:")
    
    for field_name, questions in pending:
        field = schema.fields[field_name]
        print(f"  🎯 {field_name} ({field.priority.value}):")
        for i, question in enumerate(questions[:2], 1):
            print(f"    {i}. {question}")

def test_field_update(schema):
    """フィールド更新機能のテスト"""
    print("\n✏️ Testing field updates...")
    
    # participantsフィールドを更新
    success = schema.update_field_value(
        "participants", 
        "4名（初心者2名、経験者2名）", 
        confidence=0.9,
        source="test_conversation"
    )
    
    if success:
        field = schema.fields["participants"]
        print(f"✅ Updated participants: {field.value}")
        print(f"📊 Status: {field.status.value}, Confidence: {field.confidence}")
    
    # 質問状況の再確認
    pending = schema.get_pending_questions(max_questions=2)
    print(f"📝 Remaining pending questions: {len(pending)}")

def test_completion_percentage(schema):
    """完成度計算のテスト"""
    print("\n📊 Testing completion percentage...")
    
    summary = schema.get_field_summary()
    completion = schema.get_completion_percentage()
    
    print(f"📈 Project information completion: {completion:.1f}%")
    print(f"📋 Field summary:")
    print(f"  - Total: {summary['total']}")
    print(f"  - Required: {summary['required']}")
    print(f"  - Recommended: {summary['recommended']}")
    print(f"  - Defined: {summary['defined']}")
    print(f"  - Undefined: {summary['undefined']}")

def test_priority_adjustment(schema):
    """優先度調整機能のテスト"""
    print("\n⚙️ Testing priority adjustment...")
    
    # budgetの優先度をrequiredに変更
    success = schema.set_field_priority("budget", FieldPriority.REQUIRED)
    if success:
        field = schema.fields["budget"]
        print(f"✅ Changed budget priority to: {field.priority.value}")
    
    # 新しい完成度を計算
    new_completion = schema.get_completion_percentage()
    print(f"📈 Updated completion percentage: {new_completion:.1f}%")

def test_save_and_reload(schema):
    """保存・再読み込み機能のテスト"""
    print("\n💾 Testing save and reload...")
    
    # 保存
    success = schema.save_to_project_file()
    if success:
        print("✅ Schema saved successfully")
    
    # 新しいインスタンスで再読み込み
    new_schema = get_project_schema(schema.project_id)
    
    # 保存されたデータの検証
    participants_field = new_schema.fields.get("participants")
    if participants_field and participants_field.value:
        print(f"✅ Reload verification: participants = {participants_field.value}")
        print(f"📊 Status: {participants_field.status.value}")
    
    budget_field = new_schema.fields.get("budget")
    if budget_field:
        print(f"✅ Priority preserved: budget = {budget_field.priority.value}")

def main():
    """メインテスト実行"""
    print("🚀 Dynamic Schema Test Started")
    print("=" * 50)
    
    try:
        # 1. スキーマ読み込みテスト
        schema = test_schema_loading()
        
        # 2. 質問取得テスト
        test_pending_questions(schema)
        
        # 3. フィールド更新テスト
        test_field_update(schema)
        
        # 4. 完成度計算テスト
        test_completion_percentage(schema)
        
        # 5. 優先度調整テスト
        test_priority_adjustment(schema)
        
        # 6. 保存・再読み込みテスト
        test_save_and_reload(schema)
        
        print("\n" + "=" * 50)
        print("🎉 All tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()