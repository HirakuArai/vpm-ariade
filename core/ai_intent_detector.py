# -*- coding: utf-8 -*-
"""
AI Intent Detector - AI-based user intent detection system
パターンマッチングに代わる柔軟な意図判定システム
"""

import json
import logging
import re
from typing import Dict, Optional, Tuple, Any
from datetime import datetime, date

logger = logging.getLogger(__name__)

class AIIntentDetector:
    """AI based intent detection system"""
    
    def __init__(self, openai_api_key: str):
        """
        Initialize the AI Intent Detector
        
        Args:
            openai_api_key: OpenAI API key
        """
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=openai_api_key)
            self.available = True
        except ImportError:
            logger.error("OpenAI package not available")
            self.available = False
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
            self.available = False
    
    def detect_project_creation_intent(self, user_input: str) -> Dict[str, Any]:
        """
        プロジェクト作成意図の検出
        
        Args:
            user_input: ユーザーの入力メッセージ
            
        Returns:
            {
                "is_creation_intent": bool,
                "confidence": float,
                "project_name": str,
                "project_description": str,
                "extracted_data": dict
            }
        """
        if not self.available:
            return self._fallback_project_creation(user_input)
        
        try:
            prompt = f"""
以下のユーザーメッセージがプロジェクト作成の意図を含んでいるかを判定してください。

ユーザーメッセージ: "{user_input}"

重要な判定基準:
1. **明確な依頼表現が必要**: 
   - 「作成してください」「始めてください」「プロジェクトにしてください」
   - 「立ち上げたい」「実行したい」「進めたい」「やってください」

2. **必ず除外すべきパターン**:
   - 質問や提案依頼（「どうですか？」「提案してください」「名前を考えて」「教えて」）
   - 相談や検討段階（「思っています」「考えています」「検討中」「〜しようと思う」）
   - 情報収集や相談（「について教えて」「方法は？」「どうすれば？」）
   - アドバイス求め（「意見をください」「アイデアを」「どう思いますか」）

3. **特に注意**:
   - 「〜しようと思っています」は検討段階であり、プロジェクト作成依頼ではない
   - 「名前を提案してください」は質問であり、プロジェクト作成依頼ではない
   - 質問文（？で終わる、疑問詞で始まる）は基本的に作成意図ではない

4. **高い信頼度(0.8以上)の条件**:
   - 明確な実行指示「〜してください」「〜を始める」
   - 依頼や命令の文脈
   - 質問ではなく明確な意志表明

以下のJSON形式で回答してください:
{{
  "is_creation_intent": true/false,
  "confidence": 0.0-1.0の信頼度（0.8以上は明確な作成依頼のみ），
  "reasoning": "判定理由（なぜその判定になったか）",
  "project_name": "プロジェクト名（20文字以内、推定）",
  "project_description": "プロジェクトの説明（元のメッセージベース）",
  "extracted_data": {{
    "timeline": "期間や期限があれば抽出",
    "budget": "予算情報があれば抽出",
    "participants": "参加者情報があれば抽出",
    "scope": "範囲や規模があれば抽出"
  }}
}}
"""
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=500
            )
            
            result = json.loads(response.choices[0].message.content)
            
            # 結果の妥当性チェック
            if not isinstance(result.get("is_creation_intent"), bool):
                result["is_creation_intent"] = False
            if not isinstance(result.get("confidence"), (int, float)):
                result["confidence"] = 0.0
            if not result.get("project_name"):
                result["project_name"] = "新規プロジェクト"
            if not result.get("project_description"):
                result["project_description"] = user_input.strip()
            if not result.get("extracted_data"):
                result["extracted_data"] = {}
            
            logger.info(f"Project creation intent detected: {result['is_creation_intent']} (confidence: {result['confidence']})")
            return result
            
        except Exception as e:
            logger.error(f"AI project creation detection failed: {e}")
            return self._fallback_project_creation(user_input)
    
    def detect_task_addition_intent(self, user_input: str, project_context: Optional[str] = None) -> Dict[str, Any]:
        """
        タスク追加意図の検出
        
        Args:
            user_input: ユーザーの入力メッセージ
            project_context: プロジェクトの文脈情報
            
        Returns:
            {
                "is_task_intent": bool,
                "confidence": float,
                "task_description": str,
                "due_date": str or None,
                "priority": str or None,
                "extracted_data": dict
            }
        """
        if not self.available:
            return self._fallback_task_addition(user_input)
        
        try:
            context_info = f"プロジェクト文脈: {project_context}" if project_context else "プロジェクト文脈: なし"
            
            prompt = f"""
以下のユーザーメッセージがタスク追加の意図を含んでいるかを判定してください。

ユーザーメッセージ: "{user_input}"
{context_info}

重要な判定基準:
1. **明確な実行意図**:
   - 「〜をする」「〜をやる」「〜を完了したい」「〜を実行したい」
   - 「〜を追加して」「〜をタスクに」「〜をやってください」
   
2. **除外すべきパターン**:
   - 質問や相談（「どうすれば？」「方法は？」「どう思いますか？」）
   - 検討や思考段階（「考えています」「検討中」「悩んでいます」）
   - 一般的な会話（「について話しましょう」「教えてください」）

3. **高い信頼度が必要な場合**:
   - 明確な行動指示や依頼
   - 具体的なタスクの実行意志
   - 期限や条件が明記されている

以下のJSON形式で回答してください:
{{
  "is_task_intent": true/false,
  "confidence": 0.0-1.0の信頼度（0.7以上は明確な実行依頼のみ），
  "reasoning": "判定理由（なぜその判定になったか）",
  "task_description": "タスクの説明（50文字以内）",
  "due_date": "YYYY-MM-DD形式の期限（なければnull）",
  "priority": "high/medium/low（なければnull）",
  "extracted_data": {{
    "assignee": "担当者があれば抽出",
    "category": "カテゴリがあれば抽出",
    "dependencies": "依存関係があれば抽出",
    "estimated_hours": "予想工数があれば抽出"
  }}
}}
"""
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=400
            )
            
            result = json.loads(response.choices[0].message.content)
            
            # 結果の妥当性チェック
            if not isinstance(result.get("is_task_intent"), bool):
                result["is_task_intent"] = False
            if not isinstance(result.get("confidence"), (int, float)):
                result["confidence"] = 0.0
            if not result.get("task_description"):
                result["task_description"] = user_input.strip()[:50]
            if result.get("due_date"):
                # 日付フォーマットの検証
                if not re.match(r'\d{4}-\d{2}-\d{2}', str(result["due_date"])):
                    result["due_date"] = None
            if not result.get("extracted_data"):
                result["extracted_data"] = {}
            
            logger.info(f"Task addition intent detected: {result['is_task_intent']} (confidence: {result['confidence']})")
            return result
            
        except Exception as e:
            logger.error(f"AI task addition detection failed: {e}")
            return self._fallback_task_addition(user_input)
    
    def _fallback_project_creation(self, user_input: str) -> Dict[str, Any]:
        """
        AI判定が失敗した場合のフォールバック処理（プロジェクト作成）
        """
        patterns = [
            "プロジェクト作成", "新規プロジェクト", "プロジェクトを作成", 
            "プロジェクトとして作成", "新規に作成", "プロジェクトを新規", 
            "新しいプロジェクト", "プロジェクトを始める"
        ]
        
        is_creation = any(pattern in user_input for pattern in patterns)
        
        return {
            "is_creation_intent": is_creation,
            "confidence": 0.8 if is_creation else 0.0,
            "project_name": "新規プロジェクト",
            "project_description": user_input.strip(),
            "extracted_data": {}
        }
    
    def _fallback_task_addition(self, user_input: str) -> Dict[str, Any]:
        """
        AI判定が失敗した場合のフォールバック処理（タスク追加）
        """
        is_task = user_input.startswith("タスク ")
        
        if is_task:
            # 既存のパースロジックを使用
            parts = user_input[3:].strip().split()  # Remove "タスク " prefix
            if len(parts) >= 2:
                due_date = parts[-1]
                description = " ".join(parts[:-1])
                
                # 日付フォーマットの検証
                if re.match(r'\d{4}-\d{2}-\d{2}', due_date):
                    return {
                        "is_task_intent": True,
                        "confidence": 0.9,
                        "task_description": description,
                        "due_date": due_date,
                        "priority": None,
                        "extracted_data": {}
                    }
        
        return {
            "is_task_intent": is_task,
            "confidence": 0.8 if is_task else 0.0,
            "task_description": user_input.strip(),
            "due_date": None,
            "priority": None,
            "extracted_data": {}
        }

    def detect_task_removal_intent(self, user_input: str, current_tasks: List[Dict] = None) -> Dict[str, Any]:
        """
        タスク削除意図の検出
        
        Args:
            user_input: ユーザーの入力
            current_tasks: 現在のタスクリスト
            
        Returns:
            Dict containing removal intent analysis
        """
        if not self.api_key:
            return self._fallback_task_removal(user_input)
        
        try:
            # タスクリストの情報を含める
            tasks_info = ""
            if current_tasks:
                tasks_info = "\n現在のタスクリスト:\n"
                for task in current_tasks:
                    tasks_info += f"- [{task.get('id')}] {task.get('description')} (期日: {task.get('due_date')})\n"
            
            prompt = f"""
以下のユーザーメッセージがタスク削除・重複除去の意図を含んでいるかを判定してください。

ユーザーメッセージ: "{user_input}"
{tasks_info}

判定基準:
1. **削除意図**:
   - 「削除」「消去」「除去」「取り除く」「消す」「ひとつ消して」
   - 「重複を削除」「同じものを消す」「重複除去」
   
2. **対象の特定**:
   - 特定のタスクID（数字）
   - 「重複」「同じもの」「ダブり」
   - 「全部」「すべて」

3. **除外パターン**:
   - 新しい「削除」タスクの追加依頼
   - タスクの内容が「削除」に関する作業

以下のJSON形式で回答してください:
{{
  "is_removal_intent": true/false,
  "confidence": 0.0-1.0の信頼度,
  "reasoning": "判定理由",
  "removal_type": "specific/duplicate/all",
  "target_task_ids": [削除対象のタスクID配列],
  "is_duplicate_removal": true/false
}}
"""
            
            response = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "あなたはタスク削除意図の検出専門家です。ユーザーの発言を正確に分析してください。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=300
            )
            
            result = json.loads(response.choices[0].message.content.strip())
            
            # 必須フィールドの検証と補完
            if not isinstance(result.get("is_removal_intent"), bool):
                result["is_removal_intent"] = False
            if not isinstance(result.get("confidence"), (int, float)):
                result["confidence"] = 0.0
            if not result.get("target_task_ids"):
                result["target_task_ids"] = []
            if not isinstance(result.get("is_duplicate_removal"), bool):
                result["is_duplicate_removal"] = False
            
            logger.info(f"Task removal intent detected: {result['is_removal_intent']} (confidence: {result['confidence']})")
            return result
            
        except Exception as e:
            logger.error(f"AI task removal detection failed: {e}")
            return self._fallback_task_removal(user_input)
    
    def _fallback_task_removal(self, user_input: str) -> Dict[str, Any]:
        """
        AI判定が失敗した場合のフォールバック処理（タスク削除）
        """
        removal_patterns = [
            "削除", "消去", "除去", "取り除く", "消す", "ひとつ消して", 
            "重複削除", "重複除去", "同じものを消す", "ダブりを消す"
        ]
        
        is_removal = any(pattern in user_input for pattern in removal_patterns)
        is_duplicate = any(word in user_input for word in ["重複", "同じ", "ダブり"])
        
        # 数字を抽出してタスクIDとして認識
        import re
        task_ids = [int(match) for match in re.findall(r'\b(\d+)\b', user_input)]
        
        return {
            "is_removal_intent": is_removal,
            "confidence": 0.8 if is_removal else 0.0,
            "reasoning": "パターンマッチングによる判定",
            "removal_type": "duplicate" if is_duplicate else ("specific" if task_ids else "general"),
            "target_task_ids": task_ids,
            "is_duplicate_removal": is_duplicate
        }