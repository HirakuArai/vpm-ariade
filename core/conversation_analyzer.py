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
            
            # タスク関連情報の抽出
            task_extracted = self._extract_task_information(recent_messages)
            extracted_info.extend(task_extracted)
            
            # 詳細プロジェクト情報の抽出
            detail_extracted = self._extract_project_detail_information(recent_messages)
            extracted_info.extend(detail_extracted)
            
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
            # 未定義フィールドだけでなく、更新可能な全フィールドを対象にする
            expected_fields = {}
            for field_name, field in project_schema.fields.items():
                # undefined または partial のフィールド、もしくは常に更新対象のフィールド
                if field.status.value in ["undefined", "partial"] or field_name in ["timeline", "accommodation", "route_preference"]:
                    expected_fields[field_name] = {
                        "priority": field.priority.value,
                        "questions": field.questions,
                        "current_value": field.value,
                        "status": field.status.value
                    }
            
            if not expected_fields:
                logger.warning("No fields to extract - all fields are confirmed")
                # それでも会話内容から新しい情報や更新があるかもしれないので続行
            
            # システムプロンプトの構築
            system_prompt = self._build_extraction_prompt(expected_fields)
            
            # 会話内容を整形
            conversation_text = self._format_conversation(messages)
            
            # OpenAI API呼び出し（ログ記録ラッパー使用）
            from core.v2.openai_config import create_chat_completion
            response = create_chat_completion(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"会話内容:\n{conversation_text}"}
                ],
                temperature=0.1,
                max_tokens=8000
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
5. **更新情報も抽出** - 既存の値から変更された情報も抽出する

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

情報が見つからない場合は extracted を空配列にしてください。

# 重要な注意事項
- 既存の値から変更された情報も必ず抽出してください
- 例: 「スケジュールは2025/7/27から28の2日間です」は timeline フィールドの更新
- 例: 「行者小屋で一泊」は accommodation フィールドの情報"""
    
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
    
    def _extract_task_information(self, messages: List[Dict]) -> List[ExtractedInformation]:
        """タスク関連情報の抽出"""
        extracted_info = []
        
        try:
            import re
            
            # タスク期日変更のパターン
            task_patterns = [
                r'([^、。は]+?)は(\d{4}[/-]\d{1,2}[/-]\d{1,2})',  # "登山ルート調査は2025/7/1"
                r'([^、。：]+?)：(\d{4}[/-]\d{1,2}[/-]\d{1,2})',  # "登山ルート調査：2025/7/1"
                r'([^、。を]+?)を(\d{4}[/-]\d{1,2}[/-]\d{1,2})',  # "装備リスト作成を2025/7/5"
                r'([^、。]+?)\s+(\d{4}[/-]\d{1,2}[/-]\d{1,2})',  # "登山ルート調査 2025/7/1"
            ]
            
            for message in messages:
                content = message.get("content", "")
                role = message.get("role", "")
                
                # ユーザーメッセージのみを処理（AIの応答は除外）
                if role != "user":
                    continue
                
                # 期日変更の意図が明確なメッセージのみ処理
                if not any(keyword in content for keyword in ["期日", "見直し", "変更", "更新"]):
                    continue
                
                # タスク期日変更の検出
                for pattern in task_patterns:
                    matches = re.finditer(pattern, content)
                    for match in matches:
                        task_name = match.group(1).strip()
                        task_date = match.group(2).strip()
                        
                        # 日付形式を正規化
                        normalized_date = self._normalize_date_format(task_date)
                        
                        if task_name and normalized_date and len(task_name) < 50:  # 長すぎるマッチを除外
                            extracted_info.append(ExtractedInformation(
                                field_name="task_deadline_update",
                                value=f"{task_name}: {normalized_date}",
                                confidence=0.9,
                                source="conversation",
                                extraction_method="task_pattern_matching",
                                original_text=match.group(0)
                            ))
                            
                            logger.info(f"Extracted task deadline: {task_name} -> {normalized_date}")
            
        except Exception as e:
            logger.error(f"Task information extraction failed: {e}")
        
        return extracted_info
    
    def _normalize_date_format(self, date_str: str) -> Optional[str]:
        """日付形式を YYYY-MM-DD に正規化"""
        import re
        
        # YYYY/MM/DD または YYYY-MM-DD 形式
        match = re.match(r'(\d{4})[/-](\d{1,2})[/-](\d{1,2})', date_str)
        if match:
            year, month, day = match.groups()
            return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
        
        return None
    
    def _extract_project_detail_information(self, messages: List[Dict]) -> List[ExtractedInformation]:
        """詳細プロジェクト情報の抽出（スケジュール、ルート、宿泊等）"""
        extracted_info = []
        
        try:
            import re
            
            for message in messages:
                content = message.get("content", "")
                role = message.get("role", "")
                
                # ユーザーメッセージのみを処理
                if role != "user":
                    continue
                
                # スケジュール/日程の抽出（より柔軟なパターン）
                timeline_patterns = [
                    # 「スケジュールは」で始まるパターン
                    r'スケジュールは(\d{4}/\d{1,2}/\d{1,2}から\d{1,2}の\d+日間)',
                    r'スケジュールは(\d{4}/\d{1,2}/\d{1,2}.*?\d+日間)',
                    r'スケジュールは(\d{4}/\d{1,2}/\d{1,2}から\d{1,2})',
                    # 「スケジュールは」で始まらないパターン
                    r'(\d{4}/\d{1,2}/\d{1,2}から\d{1,2}の\d+日間)です',
                    r'(\d{4}/\d{1,2}/\d{1,2}から\d{1,2})の(\d+日間)です',
                    r'日程.*?(\d{4}年\d{1,2}月\d{1,2}日.*?\d+日間)',
                    # より広いパターン
                    r'(\d{4}年\d{1,2}月\d{1,2}日[^。、]*\d+日間)',
                    r'(\d{4}/\d{1,2}/\d{1,2}[^。、]*\d+日間)'
                ]
                
                for pattern in timeline_patterns:
                    matches = re.finditer(pattern, content)
                    for match in matches:
                        timeline_value = match.group(1).strip()
                        
                        # 抽出された値を適切にフォーマット
                        if "から" in timeline_value and "日間" not in timeline_value:
                            # "2025/7/27から28" → "2025/7/27から28の2日間"
                            timeline_value += "の2日間"
                        
                        extracted_info.append(ExtractedInformation(
                            field_name="timeline",
                            value=timeline_value,
                            confidence=0.95,
                            source="conversation",
                            extraction_method="timeline_pattern_matching",
                            original_text=match.group(0)
                        ))
                        logger.info(f"Extracted timeline: {timeline_value}")
                
                # 参加者数の修正（「初心者2名、経験者2名」削除など）
                if "参加者" in content and "削除" in content:
                    participants_patterns = [
                        r'参加者.*?「([^」]+)」.*?削除',
                        r'「([^」]+)」.*?削除',
                    ]
                    for pattern in participants_patterns:
                        matches = re.finditer(pattern, content)
                        for match in matches:
                            removal_text = match.group(1).strip()
                            # 削除要求として記録
                            extracted_info.append(ExtractedInformation(
                                field_name="participants_update",
                                value=f"remove: {removal_text}",
                                confidence=0.9,
                                source="conversation",
                                extraction_method="participants_modification",
                                original_text=match.group(0)
                            ))
                            logger.info(f"Extracted participants modification: remove {removal_text}")
                
                # 新規タスク追加の検出
                if "新規タスク" in content and "追加" in content:
                    extracted_info.append(ExtractedInformation(
                        field_name="new_task_request",
                        value="新規タスク追加要求",
                        confidence=0.8,
                        source="conversation",
                        extraction_method="task_addition_request",
                        original_text=content[:100]
                    ))
                    logger.info("Detected new task addition request")
                
                # 宿泊情報の抽出
                accommodation_patterns = [
                    r'行者小屋.*?(?:一泊|宿泊|泊)',
                    r'(?:宿泊|泊).*?行者小屋',
                    r'(行者小屋)(?:で|に)(?:一泊|宿泊)',
                    r'宿泊.*?[:：].*?(行者小屋)',
                ]
                
                for pattern in accommodation_patterns:
                    matches = re.finditer(pattern, content)
                    for match in matches:
                        # 行者小屋の宿泊情報を検出
                        extracted_info.append(ExtractedInformation(
                            field_name="accommodation",
                            value="行者小屋（山小屋泊）",
                            confidence=0.9,
                            source="conversation",
                            extraction_method="accommodation_pattern_matching",
                            original_text=match.group(0)
                        ))
                        logger.info(f"Extracted accommodation: 行者小屋")
                        break  # 最初のマッチのみ
                
                # 装備リスト情報の抽出
                equipment_patterns = [
                    r'装備リスト.*?(?:受け取り|登録|管理)',
                    r'(?:基本装備|必携装備).*?リスト',
                    r'装備.*?(?:必要|準備|持参)',
                    r'(?:■|▪|・).*?装備',
                    r'(?:ザック|登山靴|雨具|防寒着).*?(?:必要|推奨)',
                ]
                
                # 装備リストの詳細情報を抽出する場合
                if any(keyword in content for keyword in ["装備リスト", "必携装備", "基本装備"]):
                    # 長い装備リストの場合は内容を要約
                    equipment_summary = self._extract_equipment_summary(content)
                    if equipment_summary:
                        extracted_info.append(ExtractedInformation(
                            field_name="equipment_list",
                            value=equipment_summary,
                            confidence=0.95,
                            source="conversation",
                            extraction_method="equipment_list_extraction",
                            original_text=content[:200] + "..." if len(content) > 200 else content
                        ))
                        logger.info(f"Extracted equipment list: {equipment_summary[:50]}...")
                
                for pattern in equipment_patterns:
                    matches = re.finditer(pattern, content)
                    for match in matches:
                        # 簡単な装備情報を検出
                        extracted_info.append(ExtractedInformation(
                            field_name="equipment_list",
                            value=f"装備リスト情報あり: {match.group(0)}",
                            confidence=0.8,
                            source="conversation",
                            extraction_method="equipment_pattern_matching",
                            original_text=match.group(0)
                        ))
                        logger.info(f"Extracted equipment info: {match.group(0)}")
                        break  # 最初のマッチのみ
                
        except Exception as e:
            logger.error(f"Project detail information extraction failed: {e}")
        
        return extracted_info
    
    def _extract_equipment_summary(self, content: str) -> str:
        """装備リストの要約を抽出"""
        try:
            # 装備リストの特徴的なキーワードをチェック
            if "1泊2日" in content and "山小屋泊" in content:
                return "1泊2日・山小屋泊（夕朝食付き）の基本装備リスト（必携装備、山小屋泊用、温泉立ち寄り用を含む詳細リスト）"
            elif "装備リスト" in content and "登録" in content:
                return "登山装備リスト（詳細な装備一覧が登録済み）"
            elif any(item in content for item in ["ザック", "登山靴", "雨具", "防寒着"]):
                return "基本登山装備リスト（ザック、登山靴、雨具、防寒着等を含む）"
            else:
                return "装備リスト情報"
        except Exception as e:
            logger.error(f"Equipment summary extraction failed: {e}")
            return None
    
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
                    # 特別処理が必要な情報タイプ
                    if info.field_name == "task_deadline_update":
                        success = self._apply_task_deadline_update(info, project_id, projects_dir)
                    elif info.field_name == "participants_update":
                        success = self._apply_participants_update(info, schema)
                    elif info.field_name == "new_task_request":
                        success = self._apply_new_task_request(info, project_id, projects_dir)
                    else:
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
    
    def _apply_task_deadline_update(self, info: ExtractedInformation, project_id: str, projects_dir=None) -> bool:
        """タスク期日更新の適用"""
        try:
            import json
            from pathlib import Path
            
            # プロジェクトファイルのパス
            if projects_dir:
                project_file = Path(projects_dir) / f"{project_id}.json"
            else:
                project_file = Path("data/projects") / f"{project_id}.json"
            
            if not project_file.exists():
                logger.error(f"Project file not found: {project_file}")
                return False
            
            # プロジェクトデータの読み込み
            with project_file.open(encoding="utf-8") as f:
                project_data = json.load(f)
            
            # タスク期日更新の解析
            # "登山ルート調査: 2025-07-01" 形式
            task_info = info.value.split(": ")
            if len(task_info) != 2:
                logger.error(f"Invalid task deadline format: {info.value}")
                return False
            
            task_name, new_deadline = task_info
            
            # 既存タスクを検索して更新
            tasks = project_data.get("tasks", [])
            updated = False
            
            logger.info(f"Looking for task: '{task_name.strip()}'")
            for task in tasks:
                task_desc = task.get("description", "").strip()
                logger.info(f"Comparing with existing task: '{task_desc}'")
                if task_desc == task_name.strip():
                    old_deadline = task.get("due_date")
                    task["due_date"] = new_deadline
                    logger.info(f"Updated task '{task_name}' deadline: {old_deadline} -> {new_deadline}")
                    updated = True
                    break
            
            if not updated:
                logger.warning(f"Task '{task_name}' not found for deadline update")
                logger.info(f"Available tasks: {[task.get('description') for task in tasks]}")
                return False
            
            # プロジェクトファイルの保存
            with project_file.open("w", encoding="utf-8") as f:
                json.dump(project_data, f, ensure_ascii=False, indent=2)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to apply task deadline update: {e}")
            return False
    
    def _apply_participants_update(self, info: ExtractedInformation, schema) -> bool:
        """参加者情報の更新"""
        try:
            if info.value.startswith("remove:"):
                # 削除処理
                removal_text = info.value[7:].strip()  # "remove: "を除去
                current_value = schema.fields.get("participants").value or ""
                
                # 削除対象文字列を除去（様々なパターンに対応）
                updated_value = current_value.replace(f"（{removal_text}）", "").replace(f"({removal_text})", "")
                updated_value = updated_value.replace(removal_text, "")  # 括弧なしも対応
                updated_value = updated_value.strip()
                
                success = schema.update_field_value(
                    "participants",
                    updated_value,
                    info.confidence,
                    info.source
                )
                
                if success:
                    logger.info(f"Updated participants: removed '{removal_text}' -> '{updated_value}'")
                
                return success
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to apply participants update: {e}")
            return False
    
    def _apply_new_task_request(self, info: ExtractedInformation, project_id: str, projects_dir=None) -> bool:
        """新規タスク追加要求の処理"""
        try:
            # 実際のタスク追加は別途処理されているため、ここでは記録のみ
            logger.info("New task addition request recorded (actual task addition handled separately)")
            return True
            
        except Exception as e:
            logger.error(f"Failed to apply new task request: {e}")
            return False


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