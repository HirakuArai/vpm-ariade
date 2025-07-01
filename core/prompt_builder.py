"""
Prompt Builder for Kai VPM - JSON安定化とトークン管理

このモジュールは以下の機能を提供します:
1. JSONエスケープ重複の解消
2. プロンプト長のトークン制限管理
3. システムルールの外部ファイル化
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# トークン制限
MAX_PROMPT_TOKENS = 900
TOKEN_ESTIMATE_RATIO = 4  # 文字数をトークン数に変換する概算比率

class PromptBuilder:
    """安全なJSON出力とトークン管理を行うプロンプトビルダー"""
    
    def __init__(self):
        """PromptBuilderを初期化"""
        self.rules_cache = None  # Force reload each time for development
        self._load_prompt_rules()
    
    def _load_prompt_rules(self) -> str:
        """docs/prompt_rules.mdからルールを読み込み"""
        # Always reload for development - remove cache check
        # if self.rules_cache is not None:
        #     return self.rules_cache
            
        try:
            rules_path = Path(__file__).parent.parent / "docs" / "prompt_rules.md"
            if rules_path.exists():
                self.rules_cache = rules_path.read_text(encoding="utf-8")
            else:
                logger.warning(f"Prompt rules file not found: {rules_path}")
                self.rules_cache = "# Rules file not found"
        except Exception as e:
            logger.error(f"Failed to load prompt rules: {e}")
            self.rules_cache = "# Error loading rules"
        
        return self.rules_cache
    
    def estimate_tokens(self, text: str) -> int:
        """テキストのトークン数を概算"""
        # 簡易的な概算: 文字数 / TOKEN_ESTIMATE_RATIO
        return len(text) // TOKEN_ESTIMATE_RATIO
    
    def truncate_conversation_summary(self, summary: str, max_tokens: int = 200) -> str:
        """会話履歴を指定トークン数以内に切り詰め"""
        estimated_tokens = self.estimate_tokens(summary)
        
        if estimated_tokens <= max_tokens:
            return summary
        
        # トークン数超過の場合、文字数で切り詰め
        target_chars = max_tokens * TOKEN_ESTIMATE_RATIO
        lines = summary.split('\n')
        
        truncated_lines = []
        current_chars = 0
        
        for line in lines:
            if current_chars + len(line) > target_chars:
                break
            truncated_lines.append(line)
            current_chars += len(line) + 1  # +1 for newline
        
        result = '\n'.join(truncated_lines)
        if len(truncated_lines) < len(lines):
            result += "\n... (会話履歴を切り詰めました)"
        
        return result
    
    def build_system_prompt(self) -> str:
        """システムプロンプトを構築"""
        base_prompt = """あなたは経験豊富なバーチャルプロジェクトマネージャーです。
ユーザーとの自然な対話を通じて、プロジェクトを効果的に管理します。

<RULES>

以下のJSON形式で必ず応答してください。json.dumps()を使用して正確にフォーマットしてください：

```json
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
```
"""
        # <RULES>プレースホルダーを実際のルールに置換
        rules_content = self._load_prompt_rules()
        return base_prompt.replace("<RULES>", rules_content)
    
    def build_unified_prompt(
        self, 
        user_input: str, 
        project_context: Dict[str, Any],
        conversation_history: List[Dict[str, str]]
    ) -> str:
        """統一プロンプトを構築（トークン制限付き）"""
        
        # プロジェクト状況の要約（質問内容に応じて適応的に）
        project_summary = self._summarize_project_context(project_context, user_input)
        
        # 会話履歴の要約
        conversation_summary = self._summarize_conversation_history(conversation_history)
        
        # ベースプロンプトの作成
        base_prompt = f"""## ユーザー発言
"{user_input}"

## 現在のプロジェクト状況
{project_summary}

## 最近の会話の流れ
{conversation_summary}

## ユーザーの傾向
まだ学習データが不足しています。対話を通じて傾向を学習中です。

## 求められる判断
この発言に対して、プロジェクトマネージャーとして最も適切な対応を判断してください。
パターンマッチングや固定ルールではなく、状況と文脈を総合的に理解して判断してください。

特に以下を考慮：
1. ユーザーの真の意図（表面的な言葉の裏にある本当のニーズ）
2. プロジェクトの現在の状況と優先度
3. 最も価値のある次のステップ
4. 自然で建設的な会話の継続
"""
        
        # トークン数チェック
        estimated_tokens = self.estimate_tokens(base_prompt)
        
        if estimated_tokens > MAX_PROMPT_TOKENS:
            logger.warning(f"Prompt tokens ({estimated_tokens}) exceed limit ({MAX_PROMPT_TOKENS}). Truncating conversation summary.")
            
            # 会話履歴を短縮して再構築
            truncated_summary = self.truncate_conversation_summary(
                conversation_summary, 
                max_tokens=150  # 会話履歴用の制限
            )
            
            base_prompt = f"""## ユーザー発言
"{user_input}"

## 現在のプロジェクト状況
{project_summary}

## 最近の会話の流れ
{truncated_summary}

## 求められる判断
この発言に対して、プロジェクトマネージャーとして最も適切な対応を判断してください。
パターンマッチングや固定ルールではなく、状況と文脈を総合的に理解して判断してください。
"""
        
        return base_prompt
    
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
        
        # トークン制限チェック
        full_summary = basic_info + task_summary + dynamic_summary
        estimated_tokens = self.estimate_tokens(full_summary)
        
        # プロジェクト情報が長すぎる場合は切り詰め
        if estimated_tokens > 300:  # プロジェクト情報の上限
            # 動的情報を削減
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
        
        recent_messages = conversation_history[-6:]  # 最新6メッセージ
        summary = "最近の会話:\n"
        
        for msg in recent_messages:
            role = "ユーザー" if msg.get("role") == "user" else "AI"
            content = msg.get("content", "")[:100]  # 100文字で切る
            summary += f"- {role}: {content}...\n"
        
        return summary
    
    def safe_json_response(self, response_dict: Dict[str, Any]) -> str:
        """安全なJSON文字列を生成（エスケープ重複を防ぐ）"""
        try:
            return json.dumps(response_dict, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to serialize response to JSON: {e}")
            # フォールバック応答
            return json.dumps({
                "intent": "error",
                "action_type": "processing_error",
                "reasoning": f"JSON serialization failed: {str(e)}",
                "confidence": 0.0,
                "target_items": [],
                "response_content": "申し訳ありませんが、応答の生成中にエラーが発生しました。",
                "suggested_follow_ups": ["もう一度お試しください"]
            }, ensure_ascii=False, indent=2)


def create_prompt_builder() -> PromptBuilder:
    """PromptBuilderのファクトリ関数"""
    return PromptBuilder()