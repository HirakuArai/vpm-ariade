# -*- coding: utf-8 -*-
"""
AI Intent Detector - AI-based user intent detection system
パターンマッチングに代わる柔軟な意図判定システム
"""

import json
import logging
from typing import Dict, Optional, Tuple, Any, List
from datetime import datetime, date

from .date_validator import is_valid_date

try:
    import openai
    from core.v2.openai_config import get_openai_model
except ImportError:
    openai = None
    get_openai_model = None

logger = logging.getLogger(__name__)

class AIIntentDetector:
    """AI based intent detection system"""
    
    def __init__(self, openai_api_key: str):
        """
        Initialize the AI Intent Detector
        
        Args:
            openai_api_key: OpenAI API key
        """
        self.api_key = openai_api_key
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=openai_api_key)
            self.available = True
        except ImportError:
            logger.error("OpenAI package not available")
            self.available = False
            self.client = None
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
            self.available = False
            self.client = None
    
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
            return {
                "error": "AI機能が利用できません。OpenAI APIキーを確認してください。",
                "is_creation_intent": False,
                "confidence": 0.0,
                "project_name": "",
                "project_description": "",
                "extracted_data": {}
            }
        
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
                model="gpt-4.1",
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
            return {
                "error": f"AI判定でエラーが発生しました: {str(e)}",
                "is_creation_intent": False,
                "confidence": 0.0,
                "project_name": "",
                "project_description": "",
                "extracted_data": {}
            }
    
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
            return {
                "error": "AI機能が利用できません。OpenAI APIキーを確認してください。",
                "is_task_intent": False,
                "confidence": 0.0,
                "task_description": "",
                "due_date": None,
                "priority": None,
                "extracted_data": {}
            }
        
        try:
            context_info = f"プロジェクト文脈: {project_context}" if project_context else "プロジェクト文脈: なし"
            
            prompt = f"""
以下のユーザーメッセージがタスク追加の意図を含んでいるかを判定してください。

ユーザーメッセージ: "{user_input}"
{context_info}

重要な判定基準:
1. **明確な実行意図（これらのみタスク追加として判定）**:
   - 「〜を実装してください」「〜を作成してください」「〜を準備してください」
   - 「〜を調査する」「〜を開発する」「〜を設計する」
   - 「〜を課題化してください」「〜をタスクにしてください」
   
2. **絶対に除外すべきパターン**:
   - **情報取得・質問**: 「教えてください」「見せてください」「どうですか？」「なぜですか？」
   - **状況確認**: 「タスクリストを教えて」「現在のタスクは？」「進捗はどう？」
   - **削除・修正指示**: 「削除してください」「消してください」「修正してください」
   - **一般的な会話**: 「について話しましょう」「相談したい」「意見をください」
   - **説明依頼**: 「具体的に何をする必要がありますか？」「詳細を教えて」

3. **信頼度基準（非常に厳格に）**:
   - 0.8以上: 明確な「実行してください」「作成してください」「準備してください」
   - 0.7以下: 質問、相談、確認、削除指示は全て除外

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
                model="gpt-4.1",
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
                # 日付フォーマットの検証（統一された検証モジュールを使用）
                if not is_valid_date(str(result["due_date"])):
                    result["due_date"] = None
            if not result.get("extracted_data"):
                result["extracted_data"] = {}
            
            logger.info(f"Task addition intent detected: {result['is_task_intent']} (confidence: {result['confidence']})")
            return result
            
        except Exception as e:
            logger.error(f"AI task addition detection failed: {e}")
            return {
                "error": f"AI判定でエラーが発生しました: {str(e)}",
                "is_task_intent": False,
                "confidence": 0.0,
                "task_description": "",
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
            return {
                "error": "AI機能が利用できません。OpenAI APIキーを確認してください。",
                "is_removal_intent": False,
                "confidence": 0.0,
                "reasoning": "AI機能が利用できません",
                "removal_type": "none",
                "target_task_ids": [],
                "is_duplicate_removal": False
            }
        
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
1. **明確な削除意図（これらは必ず削除として判定）**:
   - 「削除してください」「消してください」「除去してください」「取り除いてください」
   - 「一つを消して」「ひとつ消して」「重複を削除」「同じものを消す」
   - 「重複除去」「ダブりを消す」「整理してください」
   
2. **対象の特定**:
   - 特定のタスクID（「タスク1を削除」「2番を消す」）
   - 「重複」「同じもの」「ダブり」「同じ内容」
   - 「全部」「すべて」

3. **厳密な除外パターン**:
   - 「タスクの削除を実装してください」→新しいタスク追加
   - 「削除機能を作成してください」→新しいタスク追加
   - 「削除について教えてください」→質問

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
            
            # LLMロギングを使用してAPIを呼び出し
            from core.prompt_logger import log_call
            from core.log_schema import RequestKind
            
            with log_call("kai", RequestKind.INTENT_DETECT) as log:
                request_data = {
                    "model": "gpt-4.1",
                    "messages": [
                        {"role": "system", "content": "あなたはタスク削除意図の検出専門家です。ユーザーの発言を正確に分析してください。"},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.1,
                    "max_tokens": 300
                }
                
                log['log_request'](request_data)
                
                response = openai.chat.completions.create(**request_data)
                
                # レスポンスをログに記録
                response_data = {
                    "choices": [
                        {
                            "message": {
                                "role": response.choices[0].message.role,
                                "content": response.choices[0].message.content
                            }
                        }
                    ],
                    "usage": {
                        "prompt_tokens": response.usage.prompt_tokens,
                        "completion_tokens": response.usage.completion_tokens,
                        "total_tokens": response.usage.total_tokens
                    }
                }
                log['log_response'](response_data, response.usage.prompt_tokens, response.usage.completion_tokens)
            
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
            return {
                "error": f"AI判定でエラーが発生しました: {str(e)}",
                "is_removal_intent": False,
                "confidence": 0.0,
                "reasoning": f"AI判定失敗: {str(e)}",
                "removal_type": "none",
                "target_task_ids": [],
                "is_duplicate_removal": False
            }
    
