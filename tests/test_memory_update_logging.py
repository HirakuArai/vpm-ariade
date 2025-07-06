"""
Test Memory Update LLM Logging
記憶アップデート時のLLMコールログ記録テスト
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.v2.openai_config import create_chat_completion, create_memory_update_completion, get_openai_model
from core.memory_bridge import update_memory_with_llm, get_context_for_ai
from core.llm_logger import get_recent_llm_calls


def test_two_llm_calls_per_conversation():
    """
    1回の会話で2回のLLM呼び出しが記録されることをテスト
    """
    print("🧪 記憶アップデートLLMコールログテスト開始")
    
    # APIキー確認
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ OPENAI_API_KEY が設定されていません")
        return False
    
    # テスト用の会話
    test_user_message = "Memory Updateのテストです。私の好きな色は青色です。"
    memory_context = get_context_for_ai(max_events=10)
    
    print("\n1️⃣ 会話応答を生成（1回目のLLM呼び出し）")
    
    # 会話応答生成（Memory Chat βと同じ）
    system_prompt = f"""あなたはKai VPMの個人秘書Ariadeです。ユーザーとの会話履歴と重要な情報を記憶して、一貫性のある回答を提供してください。

【記憶している情報】
{memory_context if memory_context else "まだ記憶している情報はありません"}
"""
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": test_user_message}
    ]
    
    try:
        # 1回目: 会話応答（ui_chat）
        response = create_chat_completion(
            model=get_openai_model(),
            messages=messages,
            max_tokens=100,
            temperature=0.7
        )
        
        assistant_reply = response.choices[0].message.content
        print(f"✅ 会話応答生成完了: {assistant_reply[:50]}...")
        
    except Exception as e:
        print(f"❌ 会話応答生成エラー: {e}")
        return False
    
    print("\n2️⃣ 記憶を更新（2回目のLLM呼び出し）")
    
    try:
        # 2回目: 記憶更新（memory_update）
        memory_patch = update_memory_with_llm(
            user_message=test_user_message,
            assistant_response=assistant_reply,
            memory_context=memory_context
        )
        
        if memory_patch:
            print(f"✅ 記憶更新完了: {memory_patch[:100]}...")
        else:
            print("⚠️ 記憶パッチが生成されませんでした")
            
    except Exception as e:
        print(f"❌ 記憶更新エラー: {e}")
        return False
    
    print("\n3️⃣ LLM Call Logsの検証")
    
    # ログファイルを直接読んで検証
    log_file = Path("logs/llm") / f"{datetime.now().strftime('%Y-%m-%d')}.jsonl"
    
    if not log_file.exists():
        print("❌ ログファイルが存在しません")
        return False
    
    with open(log_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    entries = []
    for line in lines:
        if line.strip():
            try:
                entries.append(json.loads(line.strip()))
            except json.JSONDecodeError:
                continue
    
    print(f"📊 記録されたLLMコール数: {len(entries)}")
    
    # 最新の2件を確認
    if len(entries) >= 2:
        recent_entries = entries[-2:]
        
        # 1件目: ui_chat
        first = recent_entries[0]
        print(f"\n1件目:")
        print(f"  - kind: {first.get('kind')}")
        print(f"  - model: {first.get('model')}")
        print(f"  - tokens: {first.get('prompt_tokens')} + {first.get('completion_tokens')}")
        
        # 2件目: memory_update
        second = recent_entries[1]
        print(f"\n2件目:")
        print(f"  - kind: {second.get('kind')}")
        print(f"  - subkind: {second.get('subkind')}")
        print(f"  - tokens: {second.get('prompt_tokens')} + {second.get('completion_tokens')}")
        
        # 検証
        if first.get('kind') == 'ui_chat' and second.get('kind') == 'memory_update':
            print("\n✅ テスト成功: 1回の会話で2件のLLMコールが正しく記録されました")
            print("   1件目: ui_chat（会話応答）")
            print("   2件目: memory_update（N+1パッチ生成）")
            return True
        else:
            print("\n❌ テスト失敗: kindが期待値と異なります")
            return False
    else:
        print(f"\n❌ テスト失敗: 期待した2件のログが記録されていません（実際: {len(entries)}件）")
        return False


def test_log_content_completeness():
    """
    ログに必要な情報が含まれているか検証
    """
    print("\n🔍 ログ内容の完全性テスト")
    
    log_file = Path("logs/llm") / f"{datetime.now().strftime('%Y-%m-%d')}.jsonl"
    
    if not log_file.exists():
        print("❌ ログファイルが存在しません")
        return False
    
    with open(log_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    if len(lines) >= 2:
        # 最新の2件を検証
        for i, line in enumerate(lines[-2:]):
            entry = json.loads(line.strip())
            
            print(f"\n📋 ログ {i+1} の検証:")
            
            # 必須フィールドの確認
            required_fields = ['ts', 'model', 'kind', 'prompt_tokens', 
                             'completion_tokens', 'request', 'response']
            
            missing_fields = []
            for field in required_fields:
                if field not in entry:
                    missing_fields.append(field)
                else:
                    if field == 'request' and 'messages' in entry['request']:
                        print(f"  ✅ messages: {len(entry['request']['messages'])}件")
                    elif field == 'response' and 'content' in entry['response']:
                        print(f"  ✅ response: {len(entry['response']['content'])}文字")
            
            if missing_fields:
                print(f"  ❌ 不足フィールド: {missing_fields}")
                return False
        
        print("\n✅ すべてのログに必要な情報が含まれています")
        return True
    else:
        print("❌ ログが2件未満です")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("記憶アップデートLLMコールログテスト")
    print("=" * 60)
    
    # テスト1: 2件連続記録
    test1_result = test_two_llm_calls_per_conversation()
    
    # テスト2: ログ内容の完全性
    test2_result = test_log_content_completeness()
    
    print("\n" + "=" * 60)
    print("テスト結果サマリー")
    print("=" * 60)
    print(f"テスト1（2件連続記録）: {'✅ 成功' if test1_result else '❌ 失敗'}")
    print(f"テスト2（ログ完全性）: {'✅ 成功' if test2_result else '❌ 失敗'}")
    
    if test1_result and test2_result:
        print("\n🎉 すべてのテストが成功しました！")
        print("Memory Chat βで1回の発話につき2回のLLM呼び出しが正しく記録されます。")
    else:
        print("\n⚠️ 一部のテストが失敗しました。")