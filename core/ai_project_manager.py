# -*- coding: utf-8 -*-
"""
AI Project Manager - 真のAI的バーチャルプロジェクトマネージャー
統一されたAI判断による自然なプロジェクト管理

🧠 AI-FIRST PHILOSOPHY IMPLEMENTATION
❌ FORBIDDEN: Pattern matching, conditional chains, hardcoded rules
✅ REQUIRED: Unified AI decisions, contextual understanding, learning

📖 See docs/AI_FIRST_PHILOSOPHY.md for complete guidelines
🔥 This philosophy MUST NEVER be violated
"""

import json
import logging
from typing import Dict, List, Any
from datetime import datetime
from dataclasses import dataclass

try:
    import openai
    from core.v2.openai_config import get_openai_model
except ImportError:
    openai = None
    get_openai_model = None

logger = logging.getLogger(__name__)

@dataclass
class ActionPlan:
    """AIが生成するアクションプラン"""
    intent: str  # "project_management", "conversation", "clarification"
    action_type: str  # "create_project", "create_task", "remove_task", "status_update", "information_request"
    reasoning: str
    confidence: float
    
    # 実行パラメータ
    target_items: List[Dict[str, Any]]  # 対象となるタスクやプロジェクト
    response_content: str  # ユーザーへの応答
    suggested_follow_ups: List[str]  # 次に推奨される質問や行動

class AIProjectManager:
    """統一されたAI判断によるプロジェクトマネージャー"""
    
    def __init__(self, openai_api_key: str):
        """
        Initialize AI Project Manager
        
        Args:
            openai_api_key: OpenAI API key
        """
        self.api_key = openai_api_key
        
        try:
            if openai:
                self.client = openai.OpenAI(api_key=openai_api_key)
                self.available = True
            else:
                logger.error("OpenAI package not available")
                self.available = False
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
            self.available = False
        
        # 学習データ（将来的にはデータベース化）
        self.interaction_history = []
        self.user_preferences = {}
        
    def process_user_input(self, 
                          user_input: str, 
                          project_context: Dict[str, Any],
                          conversation_history: List[Dict[str, str]]) -> ActionPlan:
        """
        ユーザー入力を総合的に分析してアクションプランを生成
        
        Args:
            user_input: ユーザーの発言
            project_context: 現在のプロジェクト状況
            conversation_history: 会話履歴
            
        Returns:
            ActionPlan: 実行すべきアクションプラン
        """
        if not self.available:
            return ActionPlan(
                intent="error",
                action_type="system_error",
                reasoning="AI機能が利用できません",
                confidence=0.0,
                target_items=[],
                response_content="申し訳ありませんが、AI機能が現在利用できません。",
                suggested_follow_ups=[]
            )
        
        try:
            # 統一されたAI判断プロンプト
            unified_prompt = self._build_unified_prompt(
                user_input, project_context, conversation_history
            )
            
            response = self.client.chat.completions.create(
                model=get_openai_model() if get_openai_model else "gpt-4.1",
                messages=[
                    {
                        "role": "system", 
                        "content": self._get_ai_pm_system_prompt()
                    },
                    {
                        "role": "user", 
                        "content": unified_prompt
                    }
                ],
                temperature=0.3,
                max_tokens=1000
            )
            
            # AI応答を解析してActionPlanに変換
            ai_response = response.choices[0].message.content.strip()
            action_plan = self._parse_ai_response(ai_response)
            
            # 学習データとして記録
            self._record_interaction(user_input, action_plan)
            
            return action_plan
            
        except Exception as e:
            logger.error(f"AI project manager processing failed: {e}")
            return ActionPlan(
                intent="error",
                action_type="processing_error",
                reasoning=f"処理中にエラーが発生: {str(e)}",
                confidence=0.0,
                target_items=[],
                response_content="申し訳ありませんが、処理中にエラーが発生しました。もう一度お試しください。",
                suggested_follow_ups=["再度お試しください", "別の表現で説明してください"]
            )
    
    def _get_ai_pm_system_prompt(self) -> str:
        """AI Project Managerのシステムプロンプト"""
        return """
あなたは経験豊富なバーチャルプロジェクトマネージャーです。
ユーザーとの自然な対話を通じて、プロジェクトを効果的に管理します。

## 基本方針:
1. **自然な理解**: パターンマッチングではなく、文脈と意図を理解
2. **柔軟な対応**: 事前定義されていない状況でも適切に判断
3. **学習志向**: ユーザーの傾向を理解し、個人に最適化
4. **創発的思考**: 既存のルールにとらわれない創造的な解決策

## 判断基準:
- ユーザーの真の意図を理解（表面的な言葉ではなく）
- プロジェクトの状況と文脈を総合考慮
- 最も価値のある行動を提案
- 自然で建設的な会話を心がける

## 重要な判定ルール:
1. **プロジェクト作成要求**: 「プロジェクトを作成」「新しいプロジェクト」「開始したい」等はcreate_projectアクション
   - プロジェクト名と説明をparametersに設定
2. **削除・除去要求**: 「消してください」「削除して」「取り除いて」は必ずremove_taskアクション
   - task_idがわからない場合は、削除対象の説明文をdescriptionパラメータに設定
3. **情報要求**: 「教えて」「見せて」「確認したい」は必ずinformation_requestアクション
4. **タスク作成条件**: 明確な「作業」「やる」「実装」「対応」等の実行意図がある場合のみcreate_task
5. **質問・相談**: 「どうすれば」「方法は」「アドバイス」はgeneral_discussionアクション

## タスク削除時のパラメータ設定:
- task_id: 分かる場合は数値で設定
- description: 削除対象の説明文（「テスト: データ保存機能の確認」等）
- 両方設定されている場合はtask_idを優先使用

## 応答形式:
以下のJSON形式で必ず応答してください：

{
  "intent": "project_management|conversation|clarification",
  "action_type": "create_project|create_task|remove_task|update_status|information_request|general_discussion",
  "reasoning": "この判断に至った理由と分析",
  "confidence": 0.0-1.0の信頼度,
  "target_items": [
    {
      "type": "task|project|general",
      "action": "具体的な実行内容",
      "parameters": {"key": "value"}
    }
  ],
  "response_content": "ユーザーへの自然で有用な応答メッセージ",
  "suggested_follow_ups": ["次に聞いてみたい質問例1", "推奨される次の行動2"]
}
"""
    
    def _build_unified_prompt(self, 
                            user_input: str, 
                            project_context: Dict[str, Any],
                            conversation_history: List[Dict[str, str]]) -> str:
        """統一判断用のプロンプトを構築"""
        
        # プロジェクト状況の要約
        project_summary = self._summarize_project_context(project_context)
        
        # 会話履歴の要約
        conversation_summary = self._summarize_conversation_history(conversation_history)
        
        # 学習した傾向（将来実装）
        user_patterns = self._get_user_patterns()
        
        prompt = f"""
## ユーザー発言
"{user_input}"

## 現在のプロジェクト状況
{project_summary}

## 最近の会話の流れ
{conversation_summary}

## ユーザーの傾向
{user_patterns}

## 求められる判断
この発言に対して、プロジェクトマネージャーとして最も適切な対応を判断してください。
パターンマッチングや固定ルールではなく、状況と文脈を総合的に理解して判断してください。

特に以下を考慮：
1. ユーザーの真の意図（表面的な言葉の裏にある本当のニーズ）
2. プロジェクトの現在の状況と優先度
3. 最も価値のある次のステップ
4. 自然で建設的な会話の継続
"""
        
        return prompt
    
    def _summarize_project_context(self, project_context: Dict[str, Any]) -> str:
        """プロジェクト状況を要約"""
        if not project_context:
            return "プロジェクトが選択されていません"
        
        project_id = project_context.get("identifier", "不明")
        tasks = project_context.get("tasks", [])
        status = project_context.get("status", "不明")
        
        task_summary = ""
        if tasks:
            task_count = len(tasks)
            recent_tasks = [f"- {t.get('description', '')} (期日: {t.get('due_date', '')})" 
                          for t in tasks[-3:]]  # 最新3件
            task_summary = f"\n現在のタスク数: {task_count}件\n最新のタスク:\n" + "\n".join(recent_tasks)
        
        return f"""
プロジェクト: {project_id}
ステータス: {status}
{task_summary}
"""
    
    def _summarize_conversation_history(self, conversation_history: List[Dict[str, str]]) -> str:
        """会話履歴を要約"""
        if not conversation_history:
            return "新しい会話です"
        
        recent_messages = conversation_history[-6:]  # 最新6メッセージ
        summary = "最近の会話:\n"
        
        for msg in recent_messages:
            role = "ユーザー" if msg.get("role") == "user" else "AI"
            content = msg.get("content", "")[:100]  # 100文字で切る
            summary += f"- {role}: {content}...\n"
        
        return summary
    
    def _get_user_patterns(self) -> str:
        """ユーザーの行動パターンを分析（将来実装）"""
        # 現在は固定値、将来的には学習データから生成
        return "まだ学習データが不足しています。対話を通じて傾向を学習中です。"
    
    def _parse_ai_response(self, ai_response: str) -> ActionPlan:
        """AI応答をActionPlanに変換"""
        try:
            # JSONの抽出（```json で囲まれている場合を考慮）
            if "```json" in ai_response:
                start = ai_response.find("```json") + 7
                end = ai_response.find("```", start)
                json_str = ai_response[start:end].strip()
            elif ai_response.strip().startswith("{"):
                json_str = ai_response.strip()
            else:
                # JSONが見つからない場合のフォールバック
                return ActionPlan(
                    intent="conversation",
                    action_type="general_discussion",
                    reasoning="AI応答の解析に失敗",
                    confidence=0.5,
                    target_items=[],
                    response_content=ai_response,
                    suggested_follow_ups=[]
                )
            
            parsed = json.loads(json_str)
            
            return ActionPlan(
                intent=parsed.get("intent", "conversation"),
                action_type=parsed.get("action_type", "general_discussion"),
                reasoning=parsed.get("reasoning", ""),
                confidence=float(parsed.get("confidence", 0.5)),
                target_items=parsed.get("target_items", []),
                response_content=parsed.get("response_content", ""),
                suggested_follow_ups=parsed.get("suggested_follow_ups", [])
            )
            
        except Exception as e:
            logger.error(f"Failed to parse AI response: {e}")
            return ActionPlan(
                intent="conversation",
                action_type="general_discussion", 
                reasoning=f"応答解析エラー: {str(e)}",
                confidence=0.3,
                target_items=[],
                response_content="申し訳ありません。応答の処理中にエラーが発生しました。",
                suggested_follow_ups=["もう一度お聞かせください"]
            )
    
    def _record_interaction(self, user_input: str, action_plan: ActionPlan):
        """インタラクションを学習データとして記録"""
        interaction = {
            "timestamp": datetime.now().isoformat(),
            "user_input": user_input,
            "action_plan": {
                "intent": action_plan.intent,
                "action_type": action_plan.action_type,
                "confidence": action_plan.confidence
            }
        }
        
        self.interaction_history.append(interaction)
        
        # メモリ制限のため最新100件のみ保持
        if len(self.interaction_history) > 100:
            self.interaction_history = self.interaction_history[-100:]
    
    def get_learning_insights(self) -> Dict[str, Any]:
        """学習した洞察を取得"""
        if not self.interaction_history:
            return {"message": "まだ学習データが不足しています"}
        
        # 簡単な統計分析
        intent_counts = {}
        confidence_sum = 0
        
        for interaction in self.interaction_history:
            intent = interaction["action_plan"]["intent"]
            intent_counts[intent] = intent_counts.get(intent, 0) + 1
            confidence_sum += interaction["action_plan"]["confidence"]
        
        avg_confidence = confidence_sum / len(self.interaction_history)
        
        return {
            "total_interactions": len(self.interaction_history),
            "intent_distribution": intent_counts,
            "average_confidence": avg_confidence,
            "most_common_intent": max(intent_counts.items(), key=lambda x: x[1])[0] if intent_counts else None
        }

def create_ai_project_manager(api_key: str) -> AIProjectManager:
    """AI Project Managerのファクトリ関数"""
    return AIProjectManager(api_key)