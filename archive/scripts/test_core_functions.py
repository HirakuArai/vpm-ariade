import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.task_selector import select_next_task
from core.stub_writer import save_capability_stub
import json

def test_task_selector():
    print("🔍 select_next_task() 結果:")
    result = select_next_task()
    if result:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print("🎉 すべての能力がKaiに登録済みです")

def test_stub_writer():
    dummy = {
        "id": "test_capability",
        "name": "テスト能力",
        "description": "これはテスト用の能力です。",
        "code": '''def test_capability():
    print("テスト能力実行")'''
    }
    save_capability_stub(**dummy)
    print("✅ スタブ保存完了: kai_generated/test_capability.py 等を確認してください")

if __name__ == "__main__":
    test_task_selector()
    test_stub_writer()
