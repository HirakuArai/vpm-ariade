# --- core/simple_conversation_analyzer.py ---
"""
Simple Conversation Analyzer - シンプルな会話分析
AIに会話とプロジェクト情報を渡して更新を完全に任せる
"""

import json
import logging
import openai
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

class SimpleConversationAnalyzer:
    """シンプルな会話分析器"""
    
    def __init__(self, api_key: str = None):
        if api_key:
            openai.api_key = api_key
        self.model = "gpt-4.1"
    
    def analyze_and_update_project(self, messages: List[Dict], project_id: str, 
                                   projects_dir: Path = None, dry_run: bool = False) -> Tuple[Dict, int]:
        """
        会話を分析してプロジェクト情報を更新
        
        Args:
            messages: 会話メッセージリスト
            project_id: プロジェクトID
            projects_dir: プロジェクトディレクトリ
            
        Returns:
            Tuple[Dict, int]: (更新結果, 更新フィールド数)
        """
        try:
            # プロジェクトファイルを読み込み
            projects_dir = projects_dir or Path("data/projects")
            project_file = projects_dir / f"{project_id}.json"
            
            if not project_file.exists():
                logger.error(f"Project file not found: {project_file}")
                return {"success": False, "message": "プロジェクトファイルが見つかりません"}, 0
            
            with open(project_file, 'r', encoding='utf-8') as f:
                current_project_data = json.load(f)
            
            # dynamic_info部分を取得
            current_dynamic_info = current_project_data.get("dynamic_info", {})
            current_fields = current_dynamic_info.get("fields", {})
            
            # 会話を整形
            conversation_text = self._format_conversation(messages)
            
            # システムプロンプトを構築
            system_prompt = self._build_update_prompt()
            
            # 現在のプロジェクト情報をJSON形式で提供
            current_info_json = json.dumps(current_fields, ensure_ascii=False, indent=2)
            
            # AIに更新を依頼
            user_prompt = f"""## 現在のプロジェクト情報

```json
{current_info_json}
```

## 会話内容

{conversation_text}

上記の会話内容を分析し、プロジェクト情報の更新が必要な部分を特定してください。
会話から明確に読み取れる情報のみを抽出し、推測は含めないでください。"""

            response = openai.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_tokens=2000
            )
            
            # レスポンスを解析
            response_text = response.choices[0].message.content.strip()
            updates = self._parse_update_response(response_text)
            
            if not updates or not updates.get("fields"):
                return {"success": True, "message": "更新すべき情報はありません", "updates": updates}, 0
            
            # ドライランモードの場合は更新を適用しない
            if dry_run:
                # 更新予定数をカウント
                updated_count = len(updates.get("fields", {}))
                logger.info(f"Dry run: Would update {updated_count} fields")
                return {
                    "success": True, 
                    "message": f"ドライラン: {updated_count}個のフィールドが更新対象です",
                    "updates": updates,
                    "updated_count": updated_count
                }, updated_count
            
            # 更新を適用
            updated_count = self._apply_updates(current_fields, updates["fields"], current_project_data)
            
            # ファイルを保存
            if updated_count > 0:
                current_dynamic_info["last_analyzed"] = datetime.now().isoformat()
                with open(project_file, 'w', encoding='utf-8') as f:
                    json.dump(current_project_data, f, ensure_ascii=False, indent=2)
                
                logger.info(f"Updated {updated_count} fields in project {project_id}")
            
            return {
                "success": True, 
                "message": f"{updated_count}個のフィールドを更新しました",
                "updates": updates,
                "updated_count": updated_count
            }, updated_count
            
        except Exception as e:
            logger.error(f"Failed to analyze and update project: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {"success": False, "message": f"エラー: {str(e)}"}, 0
    
    def _format_conversation(self, messages: List[Dict]) -> str:
        """会話を読みやすい形式に整形"""
        formatted = []
        for msg in messages:
            role = "ユーザー" if msg["role"] == "user" else "AI"
            content = msg["content"]
            formatted.append(f"{role}: {content}")
        
        return "\n\n".join(formatted)
    
    def _build_update_prompt(self) -> str:
        """プロジェクト情報更新用のシステムプロンプト"""
        return """あなたはプロジェクト情報を管理する専門家です。

# タスク
会話内容を分析し、プロジェクト情報の更新が必要な部分を特定してください。

# プロジェクト情報のフィールド

- **participants**: 参加者数（例: "4名"）
- **timeline**: 日程・スケジュール（例: "2025年8月第2週、2泊3日"）
- **budget**: 予算
- **route_preference**: ルート希望（例: "赤岳天狗尾根ルート（中級者向け）"）
- **accommodation**: 宿泊方法（例: "行者小屋（山小屋泊）"）
- **itinerary_details**: 行程詳細（標高、距離、所要時間など）
- **elevation_info**: 標高情報（登山口、山頂、宿泊地の標高）
- **time_estimates**: 各区間の想定所要時間

# 更新ルール

1. **明示的な情報のみ** - 会話で明確に述べられた情報のみを更新
2. **既存情報の置き換え** - 新しい情報は既存の情報を完全に置き換える
3. **部分的な削除** - 「〜を削除」という指示があれば、その部分のみを削除
4. **信頼度評価** - 情報の確実性を0.0〜1.0で評価

# 重要な注意事項

- 「参加者の『（初心者2名、経験者2名）』を削除」→ participants を "4名" に更新
- 「スケジュールは2025/7/27から28の2日間です」→ timeline を更新
- 「行者小屋で一泊」→ accommodation を "行者小屋（山小屋泊）" に更新
- 標高や所要時間の詳細情報 → itinerary_details に保存
- 各地点の標高情報 → elevation_info に保存
- 区間ごとの想定時間 → time_estimates に保存

# 出力形式

以下のJSON形式で回答してください:

```json
{
  "fields": {
    "フィールド名": {
      "value": "新しい値",
      "confidence": 0.9,
      "reason": "更新理由"
    }
  },
  "summary": "更新内容の要約"
}
```

更新が不要な場合:
```json
{
  "fields": {},
  "summary": "更新すべき情報は見つかりませんでした"
}
```"""
    
    def _parse_update_response(self, response_text: str) -> Dict:
        """AI応答をパースして更新情報を取得"""
        try:
            # JSONブロックを抽出
            import re
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', response_text, re.DOTALL)
            if json_match:
                json_text = json_match.group(1)
            else:
                json_text = response_text
            
            # JSONをパース
            return json.loads(json_text)
            
        except Exception as e:
            logger.error(f"Failed to parse update response: {e}")
            logger.debug(f"Response text: {response_text}")
            return {}
    
    def _apply_updates(self, current_fields: Dict, updates: Dict, project_data: Dict) -> int:
        """更新を適用"""
        updated_count = 0
        
        for field_name, update_info in updates.items():
            if field_name not in current_fields:
                # 新規フィールドの場合は作成
                current_fields[field_name] = {
                    "value": None,
                    "priority": "recommended",
                    "status": "undefined",
                    "confidence": 0.0,
                    "source": None,
                    "last_updated": None,
                    "questions": [],
                    "ask_after": None
                }
            
            # 値を更新
            old_value = current_fields[field_name].get("value")
            new_value = update_info["value"]
            
            if old_value != new_value:
                current_fields[field_name]["value"] = new_value
                current_fields[field_name]["confidence"] = update_info.get("confidence", 0.9)
                current_fields[field_name]["source"] = "conversation"
                current_fields[field_name]["last_updated"] = datetime.now().isoformat()
                current_fields[field_name]["status"] = "defined" if new_value else "undefined"
                
                updated_count += 1
                logger.info(f"Updated {field_name}: '{old_value}' -> '{new_value}'")
        
        return updated_count


# ユーティリティ関数
def analyze_conversation_simple(messages: List[Dict], project_id: str, 
                               api_key: str = None, projects_dir=None) -> Tuple[Dict, int]:
    """
    シンプルな会話分析のヘルパー関数
    
    Args:
        messages: 会話メッセージリスト
        project_id: プロジェクトID
        api_key: OpenAI API key
        projects_dir: プロジェクトディレクトリ
        
    Returns:
        Tuple[Dict, int]: (更新結果, 更新フィールド数)
    """
    analyzer = SimpleConversationAnalyzer(api_key)
    return analyzer.analyze_and_update_project(messages, project_id, projects_dir)