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

判定基準:
- 新しいプロジェクト、計画、企画、開発、事業などを始めたい意図
- 何かを作成・実行・管理したい意図
- 具体的な活動や目標の実現意図
- 「〜をやりたい」「〜を始める」「〜を計画する」のような表現

以下のJSON形式で回答してください:
{{
  "is_creation_intent": true/false,
  "confidence": 0.0-1.0の信頼度,
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

判定基準:
- 新しいタスク、作業、TODOを追加したい意図
- 何かをやる、実行する、完了する必要があることの表現
- 期限や優先度の指定
- 「〜をする」「〜をやる」「〜を完了する」「〜が必要」のような表現

以下のJSON形式で回答してください:
{{
  "is_task_intent": true/false,
  "confidence": 0.0-1.0の信頼度,
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