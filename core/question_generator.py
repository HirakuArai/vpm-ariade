# --- core/question_generator.py ---
"""
Adaptive Question Generator - 適応的質問生成
文脈に応じた質問を生成し、適切なタイミングで提示
"""

import json
import logging
import openai
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

from .dynamic_schema import DynamicProjectSchema, FieldPriority, FieldStatus
from .models import ProjectPhase

logger = logging.getLogger(__name__)

class QuestionType(Enum):
    """質問のタイプ"""
    CLARIFICATION = "clarification"      # 既存情報の明確化
    INFORMATION = "information"          # 新しい情報の収集
    CONFIRMATION = "confirmation"        # 決定事項の確認
    DISCOVERY = "discovery"              # 潜在的課題の発見
    GUIDANCE = "guidance"                # 方向性の提案

class QuestionUrgency(Enum):
    """質問の緊急度"""
    IMMEDIATE = "immediate"      # 今すぐ聞くべき
    SOON = "soon"               # 近いうちに聞くべき
    EVENTUAL = "eventual"       # いずれ聞けば良い
    OPTIONAL = "optional"       # 聞かなくても良い

@dataclass
class Question:
    """質問オブジェクト"""
    id: str
    field_name: str
    text: str
    question_type: QuestionType
    urgency: QuestionUrgency
    context: str
    prerequisites: List[str]
    follow_up_fields: List[str]
    created_at: str
    confidence: float
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "field_name": self.field_name,
            "text": self.text,
            "question_type": self.question_type.value,
            "urgency": self.urgency.value,
            "context": self.context,
            "prerequisites": self.prerequisites,
            "follow_up_fields": self.follow_up_fields,
            "created_at": self.created_at,
            "confidence": self.confidence
        }

@dataclass
class ConversationContext:
    """会話の文脈情報"""
    recent_messages: List[Dict]
    current_topic: Optional[str]
    user_engagement_level: float  # 0.0-1.0
    conversation_length: int
    last_question_time: Optional[str]
    answered_questions_count: int
    project_phase: ProjectPhase
    session_duration: int  # minutes

class AdaptiveQuestionGenerator:
    """適応的質問生成"""
    
    def __init__(self, api_key: str = None):
        """
        初期化
        
        Args:
            api_key: OpenAI API key (Noneの場合は環境変数から取得)
        """
        if api_key:
            openai.api_key = api_key
        self.model = "gpt-4.1"
        
        # タイミング制御のパラメータ
        self.timing_config = {
            "max_questions_per_session": 3,
            "min_interval_between_questions": 2,  # messages
            "user_fatigue_threshold": 5,  # answered questions
            "session_length_weight": 0.1,
            "engagement_threshold": 0.3  # より積極的に質問を表示
        }
    
    def generate_contextual_questions(self, schema: DynamicProjectSchema,
                                    conversation_context: ConversationContext,
                                    max_questions: int = 3) -> List[Question]:
        """
        文脈に応じた質問を生成
        
        Args:
            schema: プロジェクトの動的スキーマ
            conversation_context: 会話の文脈
            max_questions: 最大質問数
            
        Returns:
            List[Question]: 生成された質問のリスト
        """
        try:
            # 1. 基本的な候補質問を取得
            candidate_questions = self._get_candidate_questions(schema, conversation_context)
            
            # 2. AIを使って文脈に適した質問を生成/改善
            if candidate_questions:
                enhanced_questions = self._enhance_questions_with_ai(
                    candidate_questions, schema, conversation_context
                )
            else:
                enhanced_questions = []
            
            # 3. 質問の優先順位を決定
            prioritized_questions = self._prioritize_questions(
                enhanced_questions, conversation_context
            )
            
            # 4. 最大数まで絞り込み
            return prioritized_questions[:max_questions]
            
        except Exception as e:
            logger.error(f"Question generation failed: {e}")
            # フォールバック: 基本的な質問を返す
            return self._get_fallback_questions(schema, max_questions)
    
    def _get_candidate_questions(self, schema: DynamicProjectSchema,
                               context: ConversationContext) -> List[Question]:
        """候補質問を取得"""
        candidates = []
        current_time = datetime.now().isoformat()
        
        # 未定義フィールドからの質問生成
        for field_name, field in schema.fields.items():
            if field.status in [FieldStatus.UNDEFINED, FieldStatus.PARTIAL]:
                # 前提条件をチェック
                if self._check_prerequisites(field_name, field, schema):
                    for i, question_text in enumerate(field.questions):
                        urgency = self._determine_urgency(field, context)
                        question_type = self._determine_question_type(field, context)
                        
                        candidates.append(Question(
                            id=f"{field_name}_{i}_{int(datetime.now().timestamp())}",
                            field_name=field_name,
                            text=question_text,
                            question_type=question_type,
                            urgency=urgency,
                            context=self._extract_relevant_context(context),
                            prerequisites=self._get_field_prerequisites(field_name, schema),
                            follow_up_fields=self._get_follow_up_fields(field_name, schema),
                            created_at=current_time,
                            confidence=0.8
                        ))
        
        return candidates
    
    def _check_prerequisites(self, field_name: str, field, schema: DynamicProjectSchema) -> bool:
        """前提条件をチェック"""
        if not field.ask_after:
            return True
        
        prerequisite_field = schema.fields.get(field.ask_after)
        if not prerequisite_field:
            return True
        
        # 前提フィールドが定義済みかチェック
        return prerequisite_field.status in [FieldStatus.DEFINED, FieldStatus.CONFIRMED]
    
    def _determine_urgency(self, field, context: ConversationContext) -> QuestionUrgency:
        """質問の緊急度を判定"""
        # 必須フィールドは緊急度が高い
        if field.priority == FieldPriority.REQUIRED:
            if context.project_phase in [ProjectPhase.INCEPTION, ProjectPhase.DEFINITION]:
                return QuestionUrgency.IMMEDIATE
            else:
                return QuestionUrgency.SOON
        
        # 推奨フィールドは中程度
        elif field.priority == FieldPriority.RECOMMENDED:
            if context.project_phase == ProjectPhase.PLANNING:
                return QuestionUrgency.SOON
            else:
                return QuestionUrgency.EVENTUAL
        
        # オプションフィールドは低い
        else:
            return QuestionUrgency.OPTIONAL
    
    def _determine_question_type(self, field, context: ConversationContext) -> QuestionType:
        """質問タイプを判定"""
        if field.status == FieldStatus.PARTIAL:
            return QuestionType.CLARIFICATION
        elif field.priority == FieldPriority.REQUIRED:
            return QuestionType.INFORMATION
        else:
            return QuestionType.DISCOVERY
    
    def _extract_relevant_context(self, context: ConversationContext) -> str:
        """関連する文脈を抽出"""
        if context.recent_messages:
            recent_content = " ".join([
                msg.get("content", "") for msg in context.recent_messages[-3:]
            ])
            return recent_content[:200]  # 最大200文字
        return ""
    
    def _get_field_prerequisites(self, field_name: str, schema: DynamicProjectSchema) -> List[str]:
        """フィールドの前提条件を取得"""
        field = schema.fields.get(field_name)
        if field and field.ask_after:
            return [field.ask_after]
        return []
    
    def _get_follow_up_fields(self, field_name: str, schema: DynamicProjectSchema) -> List[str]:
        """フォローアップフィールドを取得"""
        follow_ups = []
        for name, field in schema.fields.items():
            if field.ask_after == field_name:
                follow_ups.append(name)
        return follow_ups
    
    def _enhance_questions_with_ai(self, candidate_questions: List[Question],
                                 schema: DynamicProjectSchema,
                                 context: ConversationContext) -> List[Question]:
        """AIを使用して質問を改善"""
        try:
            if not candidate_questions:
                return []
            
            # 最新の会話内容を分析
            recent_conversation = self._format_recent_conversation(context.recent_messages)
            
            # プロジェクト情報の要約
            project_summary = self._create_project_summary(schema)
            
            # AI分析用プロンプト
            system_prompt = self._build_question_enhancement_prompt()
            
            user_prompt = f"""
プロジェクト情報:
{project_summary}

最近の会話:
{recent_conversation}

候補質問リスト:
{self._format_candidate_questions(candidate_questions)}

上記の文脈を考慮して、より適切で自然な質問に改善してください。
"""
            
            from core.v2.openai_config import create_chat_completion
            response = create_chat_completion(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=128000
            )
            
            # AI応答を解析して質問を改善
            enhanced_text = response.choices[0].message.content.strip()
            return self._parse_enhanced_questions(enhanced_text, candidate_questions)
            
        except Exception as e:
            logger.error(f"AI question enhancement failed: {e}")
            return candidate_questions  # フォールバック
    
    def _build_question_enhancement_prompt(self) -> str:
        """質問改善用システムプロンプトを構築"""
        return """あなたはプロジェクト管理の専門家として、ユーザーに対する質問を改善します。

# 改善の観点

## 自然さ
- 会話の流れに沿った自然な質問
- 前の発言を受けた適切な導入
- 専門用語を避けた分かりやすい表現

## 効果性
- 具体的で答えやすい質問
- 重複を避けた効率的な情報収集
- プロジェクト成功に直結する内容

## タイミング
- 現在の文脈に適した質問
- ユーザーの負担を考慮した適度な量
- フェーズに応じた適切な深さ

# 出力形式

以下のJSON形式で改善された質問を返してください:

```json
{
  "enhanced_questions": [
    {
      "original_id": "元の質問ID",
      "improved_text": "改善された質問文",
      "reasoning": "改善理由",
      "timing_recommendation": "immediate|soon|eventual",
      "confidence": 0.85
    }
  ]
}
```

# 例

**元の質問**: "参加者は何名ですか？"
**会話文脈**: ユーザーが「登山計画を立てています」と発言

**改善結果**:
```json
{
  "enhanced_questions": [
    {
      "original_id": "participants_0_xxx",
      "improved_text": "登山に参加される方は何名くらいを予定していますか？経験レベルも教えていただけると、より適切な計画を立てられます。",
      "reasoning": "登山という文脈を踏まえ、人数だけでなく経験レベルも同時に聞くことで効率化",
      "timing_recommendation": "immediate",
      "confidence": 0.9
    }
  ]
}
```"""
    
    def _format_recent_conversation(self, messages: List[Dict]) -> str:
        """最近の会話を整形"""
        if not messages:
            return "（会話なし）"
        
        formatted = []
        for msg in messages[-5:]:  # 最新5件
            role = "ユーザー" if msg.get("role") == "user" else "AI"
            content = msg.get("content", "")[:100]  # 100文字まで
            formatted.append(f"{role}: {content}")
        
        return "\n".join(formatted)
    
    def _create_project_summary(self, schema: DynamicProjectSchema) -> str:
        """プロジェクト情報の要約を作成"""
        summary_parts = []
        
        # 定義済みフィールド
        defined_fields = []
        for field_name, field in schema.fields.items():
            if field.value is not None:
                defined_fields.append(f"- {field_name}: {field.value}")
        
        if defined_fields:
            summary_parts.append("確定済み情報:\n" + "\n".join(defined_fields))
        
        # 未定義フィールド
        undefined_fields = [
            name for name, field in schema.fields.items()
            if field.status == FieldStatus.UNDEFINED
        ]
        
        if undefined_fields:
            summary_parts.append(f"未定義項目: {', '.join(undefined_fields)}")
        
        return "\n\n".join(summary_parts)
    
    def _format_candidate_questions(self, questions: List[Question]) -> str:
        """候補質問をフォーマット"""
        formatted = []
        for q in questions:
            formatted.append(f"ID: {q.id}")
            formatted.append(f"フィールド: {q.field_name}")
            formatted.append(f"質問: {q.text}")
            formatted.append(f"緊急度: {q.urgency.value}")
            formatted.append("---")
        
        return "\n".join(formatted)
    
    def _parse_enhanced_questions(self, ai_response: str,
                                original_questions: List[Question]) -> List[Question]:
        """AI応答を解析して改善された質問を取得"""
        try:
            # JSONブロックを抽出
            import re
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', ai_response, re.DOTALL)
            if json_match:
                json_text = json_match.group(1)
            else:
                json_text = ai_response
            
            data = json.loads(json_text)
            enhanced_questions = []
            
            # 元の質問をIDでマッピング
            original_by_id = {q.id: q for q in original_questions}
            
            for enhanced in data.get("enhanced_questions", []):
                original_id = enhanced.get("original_id")
                if original_id in original_by_id:
                    original = original_by_id[original_id]
                    
                    # 改善された質問を作成
                    enhanced_question = Question(
                        id=original.id,
                        field_name=original.field_name,
                        text=enhanced.get("improved_text", original.text),
                        question_type=original.question_type,
                        urgency=QuestionUrgency(enhanced.get("timing_recommendation", original.urgency.value)),
                        context=original.context,
                        prerequisites=original.prerequisites,
                        follow_up_fields=original.follow_up_fields,
                        created_at=original.created_at,
                        confidence=enhanced.get("confidence", original.confidence)
                    )
                    
                    enhanced_questions.append(enhanced_question)
            
            return enhanced_questions if enhanced_questions else original_questions
            
        except Exception as e:
            logger.error(f"Failed to parse enhanced questions: {e}")
            return original_questions
    
    def _prioritize_questions(self, questions: List[Question],
                            context: ConversationContext) -> List[Question]:
        """質問の優先順位を決定"""
        def priority_score(question: Question) -> float:
            score = 0.0
            
            # 緊急度による重み
            urgency_weights = {
                QuestionUrgency.IMMEDIATE: 1.0,
                QuestionUrgency.SOON: 0.7,
                QuestionUrgency.EVENTUAL: 0.4,
                QuestionUrgency.OPTIONAL: 0.1
            }
            score += urgency_weights.get(question.urgency, 0.0)
            
            # 質問タイプによる重み
            type_weights = {
                QuestionType.INFORMATION: 0.9,
                QuestionType.CLARIFICATION: 0.8,
                QuestionType.CONFIRMATION: 0.6,
                QuestionType.DISCOVERY: 0.5,
                QuestionType.GUIDANCE: 0.4
            }
            score += type_weights.get(question.question_type, 0.0)
            
            # 文脈の関連性
            if context.current_topic and context.current_topic.lower() in question.text.lower():
                score += 0.3
            
            # 信頼度
            score += question.confidence * 0.2
            
            return score
        
        # スコア順でソート
        return sorted(questions, key=priority_score, reverse=True)
    
    def _get_fallback_questions(self, schema: DynamicProjectSchema,
                              max_questions: int) -> List[Question]:
        """フォールバック用の基本質問"""
        fallback_questions = []
        current_time = datetime.now().isoformat()
        
        # 最も優先度の高い未定義フィールドから質問を生成
        undefined_fields = [
            (name, field) for name, field in schema.fields.items()
            if field.status == FieldStatus.UNDEFINED and field.questions
        ]
        
        # 優先度順でソート
        priority_order = {FieldPriority.REQUIRED: 0, FieldPriority.RECOMMENDED: 1, FieldPriority.OPTIONAL: 2}
        undefined_fields.sort(key=lambda x: priority_order.get(x[1].priority, 3))
        
        for i, (field_name, field) in enumerate(undefined_fields[:max_questions]):
            fallback_questions.append(Question(
                id=f"fallback_{field_name}_{int(datetime.now().timestamp())}",
                field_name=field_name,
                text=field.questions[0] if field.questions else f"{field_name}について教えてください",
                question_type=QuestionType.INFORMATION,
                urgency=QuestionUrgency.SOON if field.priority == FieldPriority.REQUIRED else QuestionUrgency.EVENTUAL,
                context="",
                prerequisites=[],
                follow_up_fields=[],
                created_at=current_time,
                confidence=0.5
            ))
        
        return fallback_questions
    
    def determine_question_timing(self, questions: List[Question],
                                context: ConversationContext) -> List[Question]:
        """質問すべきタイミングかを判定"""
        if not questions:
            return []
        
        # タイミング制御の条件をチェック
        timing_conditions = self._check_timing_conditions(context)
        
        if not timing_conditions["should_ask"]:
            logger.info(f"Question timing conditions not met: {timing_conditions['reason']}")
            return []
        
        # 適切な質問を選択
        suitable_questions = []
        
        for question in questions:
            if self._is_suitable_timing(question, context, timing_conditions):
                suitable_questions.append(question)
        
        # 最大数まで制限
        max_questions = min(
            timing_conditions["max_questions"],
            self.timing_config["max_questions_per_session"]
        )
        
        return suitable_questions[:max_questions]
    
    def _check_timing_conditions(self, context: ConversationContext) -> Dict[str, Any]:
        """タイミング条件をチェック"""
        conditions = {
            "should_ask": True,
            "reason": "",
            "max_questions": 1
        }
        
        # 1. ユーザーの疲労レベルチェック
        if context.answered_questions_count >= self.timing_config["user_fatigue_threshold"]:
            conditions["should_ask"] = False
            conditions["reason"] = "User fatigue threshold reached"
            return conditions
        
        # 2. エンゲージメントレベルチェック
        if context.user_engagement_level < self.timing_config["engagement_threshold"]:
            conditions["should_ask"] = False
            conditions["reason"] = "Low user engagement"
            return conditions
        
        # 3. 最後の質問からの間隔チェック
        if (context.last_question_time and 
            context.conversation_length - context.answered_questions_count < 
            self.timing_config["min_interval_between_questions"]):
            conditions["should_ask"] = False
            conditions["reason"] = "Too soon after last question"
            return conditions
        
        # 4. セッション長に応じた質問数調整
        if context.session_duration > 10:  # 10分以上
            conditions["max_questions"] = 2
        elif context.session_duration > 20:  # 20分以上
            conditions["max_questions"] = 3
        
        return conditions
    
    def _is_suitable_timing(self, question: Question, context: ConversationContext,
                          timing_conditions: Dict[str, Any]) -> bool:
        """個別質問のタイミング適性を判定"""
        # 緊急度による判定
        if question.urgency == QuestionUrgency.IMMEDIATE:
            return True
        
        # セッション長による判定
        if context.session_duration < 5 and question.urgency == QuestionUrgency.EVENTUAL:
            return False
        
        # 会話の文脈による判定
        if context.current_topic:
            topic_related = (
                context.current_topic.lower() in question.text.lower() or
                context.current_topic.lower() in question.field_name.lower()
            )
            if not topic_related and question.urgency != QuestionUrgency.SOON:
                return False
        
        return True


# ユーティリティ関数
def create_conversation_context(messages: List[Dict], project_phase: ProjectPhase,
                              session_start_time: datetime = None) -> ConversationContext:
    """会話文脈を作成するヘルパー関数"""
    if session_start_time is None:
        session_start_time = datetime.now() - timedelta(minutes=10)  # デフォルト10分
    
    session_duration = int((datetime.now() - session_start_time).total_seconds() / 60)
    
    # ユーザーエンゲージメントの簡易計算
    user_messages = [msg for msg in messages if msg.get("role") == "user"]
    avg_message_length = sum(len(msg.get("content", "")) for msg in user_messages) / max(len(user_messages), 1)
    engagement = min(avg_message_length / 50.0, 1.0)  # 50文字を基準に正規化
    
    # 最後の質問時刻を推定
    last_question_time = None
    for i, msg in enumerate(reversed(messages)):
        if msg.get("role") == "assistant" and "?" in msg.get("content", ""):
            last_question_time = str(len(messages) - i - 1)
            break
    
    return ConversationContext(
        recent_messages=messages[-10:],  # 最新10件
        current_topic=None,  # 実装時に改善
        user_engagement_level=engagement,
        conversation_length=len(messages),
        last_question_time=last_question_time,
        answered_questions_count=len(user_messages),
        project_phase=project_phase,
        session_duration=session_duration
    )