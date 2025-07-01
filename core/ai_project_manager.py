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
    from .prompt_builder import create_prompt_builder
except ImportError:
    openai = None
    get_openai_model = None
    create_prompt_builder = None

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
        
        # PromptBuilderの初期化
        self.prompt_builder = create_prompt_builder() if create_prompt_builder else None
        
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
            # 統一されたAI判断プロンプト（PromptBuilderを使用）
            if self.prompt_builder:
                unified_prompt = self.prompt_builder.build_unified_prompt(
                    user_input, project_context, conversation_history
                )
                system_prompt = self.prompt_builder.build_system_prompt()
            else:
                # フォールバック: 従来の方法
                unified_prompt = self._build_unified_prompt(
                    user_input, project_context, conversation_history
                )
                system_prompt = self._get_ai_pm_system_prompt()
            
            # LLM call loggingを統合
            from .prompt_logger import log_call
            from .log_schema import RequestKind, RequestContext
            
            # Determine subkind based on project context
            subkind = RequestContext.PROJECT_CHAT if project_context else RequestContext.HOME_CHAT
            
            with log_call("kai", RequestKind.UI_CHAT, subkind=subkind) as log:
                request_data = {
                    "model": get_openai_model() if get_openai_model else "gpt-4.1",
                    "messages": [
                        {
                            "role": "system", 
                            "content": system_prompt
                        },
                        {
                            "role": "user", 
                            "content": unified_prompt
                        }
                    ],
                    "temperature": 0.3,
                    "max_tokens": 1000
                }
                
                # リクエストをログ
                log['log_request'](request_data)
                
                # API呼び出し
                response = self.client.chat.completions.create(**request_data)
                
                # レスポンスをログ
                log['log_response'](
                    response.model_dump() if hasattr(response, 'model_dump') else response.dict(),
                    response.usage.prompt_tokens,
                    response.usage.completion_tokens
                )
            
            # AI応答を解析してActionPlanに変換
            ai_response = response.choices[0].message.content.strip()
            action_plan = self._parse_ai_response(ai_response)
            
            # 学習データとして記録
            self._record_interaction(user_input, action_plan)
            
            return action_plan
            
        except Exception as e:
            logger.error(f"AI project manager processing failed: {e}")
            
            # 詳細なエラー情報をログに出力
            import traceback
            error_trace = traceback.format_exc()
            logger.error(f"AI project manager error trace: {error_trace}")
            print(f"🚨 AIプロジェクトマネージャーエラー: {error_trace}", flush=True)
            
            # エラーもログに記録
            try:
                from .prompt_logger import log_call
                from .log_schema import RequestKind
                with log_call("kai", RequestKind.UI_CHAT) as log:
                    log['log_error'](f"processing_error: {type(e).__name__}")
            except:
                pass  # ログ記録の失敗は無視
            
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
1. **プロジェクト作成要求（文脈依存）**: 
   - **プロジェクト未選択時**: 「プロジェクトを作成」「プロジェクトとして設定」「新しいプロジェクト」等 → create_projectアクション
   - **プロジェクト選択済み時**: 同じキーワードでも → general_discussionアクション（既存プロジェクトに関する相談として処理）
   - 判定基準: プロジェクト状況セクションで「プロジェクトが選択されていません」かどうかを必ず確認
2. **削除・除去要求**: 「消してください」「削除して」「取り除いて」は必ずremove_taskアクション
   - task_idがわからない場合は、削除対象の説明文をdescriptionパラメータに設定
3. **情報要求**: 「教えて」「見せて」「確認したい」は必ずinformation_requestアクション
4. **プロジェクト情報更新**: 「日程」「参加者」「予算」「場所」等のプロジェクト属性更新はupdate_projectアクション
   - 「参加者は4名です」「日程は8月2日から3日です」等 → update_projectアクション
   - propertiesパラメータに複数のフィールドをまとめて設定可能
5. **タスク作成条件**: 明確な「作業」「やる」「実装」「対応」等の実行意図がある場合のみcreate_task
6. **質問・相談**: 「どうすれば」「方法は」「アドバイス」はgeneral_discussionアクション

## タスク削除時のパラメータ設定:
- task_id: 分かる場合は数値で設定
- description: 削除対象の説明文（「テスト: データ保存機能の確認」等）
- 両方設定されている場合はtask_idを優先使用

## 応答形式:
以下のJSON形式で必ず応答してください：

{
  "intent": "project_management|conversation|clarification",
  "action_type": "create_project|create_task|remove_task|update_project|information_request|general_discussion",
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

## 文脈依存の判定例:

### ホーム会話（プロジェクト未選択）:
入力: 「長岡の花火大会の準備をプロジェクトとして設定してください」
プロジェクト状況: 「プロジェクトが選択されていません」
→ {
  "intent": "project_management",
  "action_type": "create_project",
  "reasoning": "プロジェクト未選択状態でプロジェクト作成を要求している",
  "confidence": 0.9,
  "target_items": [
    {
      "type": "project",
      "action": "create_new_project",
      "parameters": {
        "name": "長岡の花火大会の準備",
        "description": "長岡の花火大会開催に向けた準備プロジェクト"
      }
    }
  ],
  "response_content": "長岡の花火大会の準備プロジェクトを作成しました。",
  "suggested_follow_ups": ["会場準備について相談したい", "スケジュールを確認したい"]
}

### プロジェクト会話（プロジェクト選択済み）:
入力: 「このプロジェクトをもっと本格的にプロジェクトとして進めたいです」
プロジェクト状況: 「プロジェクト: proj-20250629-182909-854, ステータス: DRAFT」
→ {
  "intent": "conversation", 
  "action_type": "general_discussion",
  "reasoning": "既にプロジェクト選択済みのため、プロジェクト運営に関する相談として処理",
  "confidence": 0.8,
  "target_items": [
    {
      "type": "general",
      "action": "project_management_consultation",
      "parameters": {}
    }
  ],
  "response_content": "現在のプロジェクトをより本格的に進めるためのアドバイスをいたします。まず、プロジェクトのステータスをDRAFTからACTIVEに変更し、具体的なタスクとマイルストーンを設定することをお勧めします。",
  "suggested_follow_ups": ["ステータスをACTIVEに変更したい", "タスクを追加したい"]
}

### プロジェクト情報更新の例:
入力: 「参加者は4名です。日程は2025年8月2日、3日の2日間です。」
プロジェクト状況: 「プロジェクト: proj-20250629-182909-854, ステータス: DRAFT」
→ {
  "intent": "project_management",
  "action_type": "update_project",
  "reasoning": "プロジェクト情報（参加者数・日程）の更新要求。複数フィールドを一度に設定",
  "confidence": 0.9,
  "target_items": [
    {
      "type": "project",
      "action": "set_properties",
      "parameters": {
        "identifier": "proj-20250629-182909-854",
        "properties": {
          "participants_count": 4,
          "start_date": "2025-08-02",
          "end_date": "2025-08-03"
        }
      }
    }
  ],
  "response_content": "参加者数4名、日程2025年8月2日〜3日で設定しました。",
  "suggested_follow_ups": ["参加者の役割分担を決めたい", "会場の準備について相談したい"]
}
"""
    
    def _build_unified_prompt(self, 
                            user_input: str, 
                            project_context: Dict[str, Any],
                            conversation_history: List[Dict[str, str]]) -> str:
        """統一判断用のプロンプトを構築"""
        
        # プロジェクト状況の要約（質問内容に応じて適応的に）
        project_summary = self._summarize_project_context(project_context, user_input)
        
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
    
    def _summarize_project_context(self, project_context: Dict[str, Any], user_input: str = "") -> str:
        """プロジェクト状況を要約（詳細情報含む・質問内容に適応）"""
        if not project_context:
            return "プロジェクトが選択されていません"
        
        project_id = project_context.get("identifier", "不明")
        display_name = project_context.get("display_name", "不明")
        overview = project_context.get("overview", "")
        status = project_context.get("status", "不明")
        phase = project_context.get("phase", "不明")
        completion = project_context.get("completion_percentage", "不明")
        tasks = project_context.get("tasks", [])
        
        # 基本情報
        basic_info = f"""プロジェクト: {project_id}
プロジェクト名: {display_name}
概要: {overview}
ステータス: {status}
フェーズ: {phase}
進捗: {completion}%"""
        
        # タスク情報
        task_summary = ""
        if tasks:
            task_count = len(tasks)
            pending_tasks = [t for t in tasks if t.get('status') == 'pending']
            recent_tasks = [f"- [{t.get('id')}] {t.get('description', '')} (期日: {t.get('due_date', '')}, ステータス: {t.get('status', '')})" 
                          for t in tasks[-3:]]  # 最新3件
            task_summary = f"\n\nタスク情報:\n現在のタスク数: {task_count}件 (うち未完了: {len(pending_tasks)}件)\n最新のタスク:\n" + "\n".join(recent_tasks)
        
        # 動的情報（質問内容に応じて適応的に抽出）
        dynamic_summary = ""
        dynamic_info = project_context.get("dynamic_info", {})
        if dynamic_info and "fields" in dynamic_info:
            fields = dynamic_info["fields"]
            important_fields = []
            
            # 質問内容に応じて関連フィールドを優先
            question_related_fields = self._identify_relevant_fields(user_input, fields)
            
            # 基本的な優先度順
            default_priority_order = ["participants", "timeline", "budget", "route_preference", "accommodation"]
            
            # 質問関連フィールドを最優先で処理
            for field_name in question_related_fields:
                if field_name in fields:
                    field_data = fields[field_name]
                    if field_data.get("status") == "defined" and field_data.get("value"):
                        value = field_data["value"]
                        # 質問に関連するフィールドは長めに表示
                        if isinstance(value, str) and len(value) > 500:
                            value = value[:500] + "..."
                        important_fields.append(f"- {field_name}: {value}")
            
            # 残りの基本フィールドを処理
            for field_name in default_priority_order:
                if len(important_fields) >= 6:  # 質問関連があるため制限を緩める
                    break
                if field_name not in question_related_fields and field_name in fields:
                    field_data = fields[field_name]
                    if field_data.get("status") == "defined" and field_data.get("value"):
                        value = field_data["value"]
                        if isinstance(value, str) and len(value) > 80:
                            value = value[:80] + "..."
                        important_fields.append(f"- {field_name}: {value}")
            
            # その他のフィールドも少し追加
            for field_name, field_data in fields.items():
                if len(important_fields) >= 8:  # 最大8項目
                    break
                if field_name not in question_related_fields and field_name not in default_priority_order:
                    if field_data.get("status") == "defined" and field_data.get("value"):
                        value = field_data["value"]
                        if isinstance(value, str) and len(value) > 80:
                            value = value[:80] + "..."
                        important_fields.append(f"- {field_name}: {value}")
            
            if important_fields:
                dynamic_summary = f"\n\n重要な項目:\n" + "\n".join(important_fields)
        
        # 基本的なトークン制限チェック（概算）
        full_summary = basic_info + task_summary + dynamic_summary
        
        # プロジェクト情報が長すぎる場合は動的情報を削減
        if len(full_summary) > 1200:  # 文字数による制限
            if dynamic_summary:
                lines = dynamic_summary.split('\n')
                truncated_lines = lines[:4]  # 最初の3項目のみ
                dynamic_summary = '\n'.join(truncated_lines) + "\n... (他の項目は省略)"
                full_summary = basic_info + task_summary + dynamic_summary
        
        return full_summary
    
    def _identify_relevant_fields(self, user_input: str, fields: Dict[str, Any]) -> List[str]:
        """質問内容から関連するフィールドを特定"""
        relevant_fields = []
        user_input_lower = user_input.lower()
        
        # キーワードベースの関連性マップ
        keyword_field_map = {
            "装備": ["equipment_list"],
            "道具": ["equipment_list"],
            "持ち物": ["equipment_list"],
            "リスト": ["equipment_list"],
            "ルート": ["route_preference", "itinerary_details"],
            "行程": ["itinerary_details", "time_estimates"],
            "スケジュール": ["itinerary_details", "timeline"],
            "日程": ["timeline", "itinerary_details"],
            "宿泊": ["accommodation"],
            "山小屋": ["accommodation"],
            "参加者": ["participants"],
            "人数": ["participants"],
            "予算": ["budget"],
            "費用": ["budget"],
            "標高": ["elevation_info"],
            "時間": ["time_estimates"],
            "温泉": ["post_activity"],
            "下山後": ["post_activity"]
        }
        
        # ユーザー入力から関連キーワードを検索
        for keyword, field_names in keyword_field_map.items():
            if keyword in user_input_lower:
                for field_name in field_names:
                    if field_name in fields and field_name not in relevant_fields:
                        relevant_fields.append(field_name)
        
        return relevant_fields
    
    def _summarize_conversation_history(self, conversation_history: List[Dict[str, str]]) -> str:
        """会話履歴を要約"""
        if not conversation_history:
            return "新しい会話です"
        
        # より多くのメッセージを含めて文脈を改善
        recent_messages = conversation_history[-10:]  # 最新10メッセージ
        total_messages = len(conversation_history)
        
        summary = f"最近の会話（直近{len(recent_messages)}件／全{total_messages}件）:\n"
        
        for msg in recent_messages:
            role = "ユーザー" if msg.get("role") == "user" else "AI"
            content = msg.get("content", "")
            
            # 重要な情報を含む場合は長めに保持
            if any(keyword in content for keyword in ["タスク", "完了", "進捗", "予定", "変更", "問題"]):
                content_preview = content[:150]  # 重要な内容は150文字
            else:
                content_preview = content[:80]   # 通常は80文字
                
            summary += f"- {role}: {content_preview}...\n"
        
        # プロジェクト固有の履歴がある場合の注釈
        if total_messages > len(recent_messages):
            summary += f"\n※ このプロジェクトには他に{total_messages - len(recent_messages)}件の過去の会話があります\n"
        
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