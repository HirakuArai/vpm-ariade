# --- core/conversation_analyzer.py ---
"""
Conversation Analyzer - 会話内容の構造化分析
会話から具体的な情報を抽出し、プロジェクト情報を更新
"""

import json
import logging
import openai
import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime

from .dynamic_schema import DynamicProjectSchema, get_project_schema

logger = logging.getLogger(__name__)

@dataclass
class ExtractedInformation:
    """抽出された情報"""
    field_name: str
    value: Any
    confidence: float
    source: str
    extraction_method: str
    original_text: str
    
    def to_dict(self) -> Dict:
        return asdict(self)

@dataclass 
class InformationConflict:
    """情報の矛盾"""
    field_name: str
    existing_value: Any
    new_value: Any
    confidence_existing: float
    confidence_new: float
    conflict_type: str  # "value_change", "contradiction", "refinement"
    description: str

class ConversationAnalyzer:
    """会話内容の分析"""
    
    def __init__(self, api_key: str = None):
        """
        初期化
        
        Args:
            api_key: OpenAI API key (Noneの場合は環境変数から取得)
        """
        if api_key:
            openai.api_key = api_key
        self.model = "gpt-4.1"
        
        # パターンベースの抽出ルール（フォールバック用）
        self.extraction_patterns = {
            "participants": [
                r"(\d+)名",
                r"(\d+)人",
                r"参加者(?:は)?(\d+)",
                r"メンバー(?:は)?(\d+)"
            ],
            "budget": [
                r"予算(?:は)?([0-9,]+)円",
                r"(\d+)万円",
                r"([0-9,]+)円(?:以内|まで|程度)"
            ],
            "timeline": [
                r"(\d{4})年(\d{1,2})月",
                r"(\d{1,2})月(\d{1,2})日",
                r"(\d+)日間",
                r"(\d+)泊(\d+)日"
            ]
        }
    
    def extract_information_from_conversation(self, messages: List[Dict],
                                            project_schema: DynamicProjectSchema) -> List[ExtractedInformation]:
        """
        会話から構造化情報を抽出
        
        Args:
            messages: 会話メッセージリスト
            project_schema: プロジェクトの動的スキーマ
            
        Returns:
            List[ExtractedInformation]: 抽出された情報のリスト
        """
        extracted_info = []
        
        try:
            # 最新の数メッセージを分析対象とする
            recent_messages = messages[-10:] if len(messages) > 10 else messages
            
            # AI分析による抽出
            ai_extracted = self._extract_with_ai(recent_messages, project_schema)
            extracted_info.extend(ai_extracted)
            
            # パターンベース抽出（フォールバック）
            pattern_extracted = self._extract_with_patterns(recent_messages, project_schema)
            extracted_info.extend(pattern_extracted)
            
            # 重複を除去（信頼度の高いものを優先）
            extracted_info = self._deduplicate_extractions(extracted_info)
            
            return extracted_info
            
        except Exception as e:
            logger.error(f"Information extraction failed: {e}")
            return []
    
    def _extract_with_ai(self, messages: List[Dict], 
                        project_schema: DynamicProjectSchema) -> List[ExtractedInformation]:
        """AI による情報抽出"""
        try:
            # プロジェクトスキーマから期待される情報を取得
            expected_fields = {}
            for field_name, field in project_schema.fields.items():
                if field.status.value == "undefined":
                    expected_fields[field_name] = {
                        "priority": field.priority.value,
                        "questions": field.questions
                    }
            
            if not expected_fields:
                return []  # 抽出すべき情報がない
            
            # システムプロンプトの構築
            system_prompt = self._build_extraction_prompt(expected_fields)
            
            # 会話内容を整形
            conversation_text = self._format_conversation(messages)
            
            # OpenAI API呼び出し
            response = openai.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"会話内容:\n{conversation_text}"}
                ],
                temperature=0.1,
                max_tokens=1500
            )
            
            # レスポンスを解析
            extraction_text = response.choices[0].message.content.strip()
            return self._parse_extraction_response(extraction_text, "ai_analysis")
            
        except Exception as e:
            logger.error(f"AI extraction failed: {e}")
            return []
    
    def _build_extraction_prompt(self, expected_fields: Dict) -> str:
        """情報抽出用システムプロンプトを構築"""
        fields_desc = "\n".join([
            f"- **{name}** ({info['priority']}): {', '.join(info['questions'][:2])}"
            for name, info in expected_fields.items()
        ])
        
        return f"""あなたは会話から具体的な情報を抽出する専門家です。

# 抽出対象の情報

{fields_desc}

# 抽出ルール

1. **明示的な情報のみ** - 推測や想定は含めない
2. **具体的な値** - 曖昧な表現ではなく明確な値を抽出
3. **信頼度評価** - 情報の確実性を0.0〜1.0で評価
4. **文脈考慮** - 質問と回答の流れを理解する

# 出力形式

以下のJSON形式で回答してください:

```json
{{
  "extracted": [
    {{
      "field_name": "フィールド名",
      "value": "抽出された値",
      "confidence": 0.9,
      "original_text": "元の発言内容",
      "explanation": "抽出理由"
    }}
  ]
}}
```

# 例

**会話**: 
ユーザー: "参加者は4名です。初心者が2名、経験者が2名います"
AI: "4名の構成ですね。どのような活動を予定していますか？"

**出力**:
```json
{{
  "extracted": [
    {{
      "field_name": "participants",
      "value": "4名（初心者2名、経験者2名）",
      "confidence": 0.95,
      "original_text": "参加者は4名です。初心者が2名、経験者が2名います",
      "explanation": "参加者数と経験レベルが明確に述べられている"
    }}
  ]
}}
```

情報が見つからない場合は extracted を空配列にしてください。"""
    
    def _format_conversation(self, messages: List[Dict]) -> str:
        """会話を読みやすい形式に整形"""
        formatted = []
        for msg in messages:
            role = "ユーザー" if msg["role"] == "user" else "AI"
            content = msg["content"]
            formatted.append(f"{role}: {content}")
        
        return "\n".join(formatted)
    
    def _parse_extraction_response(self, response_text: str, 
                                 extraction_method: str) -> List[ExtractedInformation]:
        """AI応答をパースして抽出情報リストに変換"""
        extracted_info = []
        
        try:
            # JSONブロックを抽出
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', response_text, re.DOTALL)
            if json_match:
                json_text = json_match.group(1)
            else:
                json_text = response_text
            
            # JSONをパース
            data = json.loads(json_text)
            
            # ExtractedInformationオブジェクトを構築
            for item in data.get("extracted", []):
                extracted_info.append(ExtractedInformation(
                    field_name=item["field_name"],
                    value=item["value"],
                    confidence=item["confidence"],
                    source="conversation",
                    extraction_method=extraction_method,
                    original_text=item.get("original_text", "")
                ))
                
        except Exception as e:
            logger.error(f"Failed to parse extraction response: {e}")
            logger.debug(f"Response text: {response_text}")
        
        return extracted_info
    
    def _extract_with_patterns(self, messages: List[Dict],
                             project_schema: DynamicProjectSchema) -> List[ExtractedInformation]:
        """パターンベースの情報抽出（フォールバック）"""
        extracted_info = []
        
        try:
            # 全メッセージのテキストを結合
            all_text = " ".join([msg["content"] for msg in messages])
            
            # パターンマッチング
            for field_name, patterns in self.extraction_patterns.items():
                if field_name in project_schema.fields and \
                   project_schema.fields[field_name].status.value == "undefined":
                    
                    for pattern in patterns:
                        matches = re.finditer(pattern, all_text, re.IGNORECASE)
                        for match in matches:
                            value = self._format_pattern_match(field_name, match)
                            if value:
                                extracted_info.append(ExtractedInformation(
                                    field_name=field_name,
                                    value=value,
                                    confidence=0.7,  # パターンマッチは中程度の信頼度
                                    source="conversation",
                                    extraction_method="pattern_matching",
                                    original_text=match.group(0)
                                ))
                                break  # 最初のマッチのみ
        
        except Exception as e:
            logger.error(f"Pattern extraction failed: {e}")
        
        return extracted_info
    
    def _format_pattern_match(self, field_name: str, match) -> str:
        """パターンマッチの結果を適切な形式にフォーマット"""
        try:
            if field_name == "participants":
                return f"{match.group(1)}名"
            elif field_name == "budget":
                return match.group(0)  # マッチした全体
            elif field_name == "timeline":
                return match.group(0)  # マッチした全体
            else:
                return match.group(0)
        except:
            return None
    
    def _deduplicate_extractions(self, extracted_info: List[ExtractedInformation]) -> List[ExtractedInformation]:
        """抽出情報の重複を除去（信頼度の高いものを優先）"""
        field_best = {}
        
        for info in extracted_info:
            field_name = info.field_name
            if field_name not in field_best or info.confidence > field_best[field_name].confidence:
                field_best[field_name] = info
        
        return list(field_best.values())
    
    def detect_information_conflicts(self, extracted_info: List[ExtractedInformation],
                                   project_schema: DynamicProjectSchema) -> List[InformationConflict]:
        """情報の矛盾を検出"""
        conflicts = []
        
        for info in extracted_info:
            field_name = info.field_name
            if field_name in project_schema.fields:
                existing_field = project_schema.fields[field_name]
                
                # 既存の値がある場合に矛盾をチェック
                if existing_field.value is not None and existing_field.value != info.value:
                    conflict_type = self._determine_conflict_type(
                        existing_field.value, info.value
                    )
                    
                    conflicts.append(InformationConflict(
                        field_name=field_name,
                        existing_value=existing_field.value,
                        new_value=info.value,
                        confidence_existing=existing_field.confidence,
                        confidence_new=info.confidence,
                        conflict_type=conflict_type,
                        description=f"{field_name}の値が変更されました: '{existing_field.value}' → '{info.value}'"
                    ))
        
        return conflicts
    
    def _determine_conflict_type(self, existing_value: Any, new_value: Any) -> str:
        """矛盾のタイプを判定"""
        existing_str = str(existing_value).lower()
        new_str = str(new_value).lower()
        
        # 値の詳細化（例: "4名" → "4名（初心者2名、経験者2名）"）
        if existing_str in new_str or new_str in existing_str:
            return "refinement"
        
        # 明確な変更
        return "value_change"
    
    def apply_extracted_information(self, extracted_info: List[ExtractedInformation],
                                  project_id: str, projects_dir=None) -> Tuple[int, List[InformationConflict]]:
        """
        抽出された情報をプロジェクトスキーマに適用
        
        Args:
            extracted_info: 抽出された情報のリスト
            project_id: プロジェクトID
            projects_dir: プロジェクトディレクトリ
            
        Returns:
            Tuple[int, List[InformationConflict]]: (適用された情報数, 矛盾リスト)
        """
        try:
            schema = get_project_schema(project_id, projects_dir)
            
            # 矛盾をチェック
            conflicts = self.detect_information_conflicts(extracted_info, schema)
            
            applied_count = 0
            
            # 矛盾のない情報を適用
            for info in extracted_info:
                # 矛盾がない、または信頼度が十分高い場合に適用
                has_conflict = any(c.field_name == info.field_name for c in conflicts)
                
                if not has_conflict or info.confidence > 0.9:
                    success = schema.update_field_value(
                        info.field_name,
                        info.value,
                        info.confidence,
                        info.source
                    )
                    
                    if success:
                        applied_count += 1
                        logger.info(f"Applied {info.field_name}: {info.value} (confidence: {info.confidence})")
            
            # スキーマを保存
            if applied_count > 0:
                schema.save_to_project_file()
            
            return applied_count, conflicts
            
        except Exception as e:
            logger.error(f"Failed to apply extracted information: {e}")
            return 0, []


# ユーティリティ関数
def analyze_conversation_and_update_project(messages: List[Dict], project_id: str,
                                          api_key: str = None,
                                          projects_dir=None) -> Tuple[int, List[InformationConflict]]:
    """
    会話分析とプロジェクト更新のヘルパー関数
    
    Args:
        messages: 会話メッセージリスト
        project_id: プロジェクトID
        api_key: OpenAI API key
        projects_dir: プロジェクトディレクトリ
        
    Returns:
        Tuple[int, List[InformationConflict]]: (更新された情報数, 矛盾リスト)
    """
    analyzer = ConversationAnalyzer(api_key)
    schema = get_project_schema(project_id, projects_dir)
    
    # 情報抽出
    extracted_info = analyzer.extract_information_from_conversation(messages, schema)
    
    # プロジェクトに適用
    return analyzer.apply_extracted_information(extracted_info, project_id, projects_dir)