# --- core/auto_update_engine.py ---
"""
AutoUpdateEngine - プロジェクトデータ自動更新エンジン
"""

import json
import logging
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

from .models import ProjectPhase, DEFAULT_UNDEF
from .project_service import get_project, update_project_field
from .lifecycle_manager import ProjectLifecycleManager
from .conversation_engine import PhaseAwareConversationEngine

logger = logging.getLogger(__name__)

@dataclass
class UpdateCandidate:
    """自動更新候補"""
    field: str
    old_value: Any
    new_value: Any
    confidence: float
    source: str
    reasoning: str
    timestamp: str

@dataclass
class AutoUpdateResult:
    """自動更新結果"""
    success: bool
    updates_applied: List[UpdateCandidate]
    updates_rejected: List[UpdateCandidate]
    phase_advanced: bool
    notifications: List[Dict[str, Any]]
    errors: List[str]

class AutoUpdateEngine:
    """プロジェクトデータ自動更新エンジン"""
    
    def __init__(self, projects_dir: Path | None = None):
        self.projects_dir = projects_dir
        self.lifecycle_manager = ProjectLifecycleManager(projects_dir)
        self.confidence_threshold = 0.8  # 自動適用の信頼度閾値（より厳格に）
        
        # 自動更新パターン定義（より厳格な基準）
        self.update_patterns = {
            "task_completion": {
                "patterns": [
                    r"(.{5,30}?)(?:が|を|は)(?:完了|終了|完成)(?:しました|した|です)",
                    r"(.{5,30}?)(?:finish|complete|done)",
                    r"(.{5,30}?)(?:の|を)(?:fix|fixed|resolve|resolved)",
                ],
                "confidence": 0.9,
                "field": "task_completion"
            },
            "task_creation": {
                "patterns": [
                    r"(?:タスク|作業|TODO):\s*([^。！？\n]{8,50})",
                    r"(?:次は|今度は|新しく)(.{8,30}?)(?:する|やる|作る|実装)(?:必要|すべき|したい)",
                ],
                "confidence": 0.9,
                "field": "new_task"
            },
            "blocker_identification": {
                "patterns": [
                    r"(.+?)(?:でエラー|で問題|で障害|が動かない|ができない)",
                    r"(.+?)(?:がブロック|で詰まっ|で止まっ)",
                    r"(?:問題|課題|エラー|障害):?\s*(.+)",
                ],
                "confidence": 0.85,
                "field": "blocking_issues"
            },
            "progress_update": {
                "patterns": [
                    r"(.+?)(?:の進捗|は)(\d{1,3})%",
                    r"(.+?)(?:が|は)(\d{1,3})(?:%|パーセント)(?:完了|進んだ)",
                ],
                "confidence": 0.9,
                "field": "task_progress"
            },
            "deadline_update": {
                "patterns": [
                    r"(.+?)(?:の期限|は)(\d{4}[-/]\d{1,2}[-/]\d{1,2})",
                    r"(.+?)(?:を|は)(\d{1,2}月\d{1,2}日)(?:まで|に)",
                ],
                "confidence": 0.8,
                "field": "task_deadline"
            }
        }
    
    def process_conversation(self, project_id: str, user_input: str, assistant_reply: str) -> AutoUpdateResult:
        """会話を処理してプロジェクトデータを自動更新"""
        
        try:
            # 現在のプロジェクトデータを取得
            project_data = get_project(project_id, self.projects_dir)
            if not project_data:
                return AutoUpdateResult(
                    success=False,
                    updates_applied=[],
                    updates_rejected=[],
                    phase_advanced=False,
                    notifications=[],
                    errors=[f"Project {project_id} not found"]
                )
            
            # 会話から更新候補を抽出
            update_candidates = self._extract_update_candidates(project_id, user_input, assistant_reply)
            
            # 高信頼度の更新を自動適用
            applied_updates = []
            rejected_updates = []
            
            for candidate in update_candidates:
                if candidate.confidence >= self.confidence_threshold:
                    success = self._apply_update_candidate(project_id, candidate)
                    if success:
                        applied_updates.append(candidate)
                    else:
                        rejected_updates.append(candidate)
                else:
                    rejected_updates.append(candidate)
            
            # フェーズ進行チェック
            phase_advanced = self._check_and_advance_phase(project_id)
            
            # 通知生成
            notifications = self._generate_notifications(project_id, applied_updates, phase_advanced)
            
            return AutoUpdateResult(
                success=True,
                updates_applied=applied_updates,
                updates_rejected=rejected_updates,
                phase_advanced=phase_advanced,
                notifications=notifications,
                errors=[]
            )
            
        except Exception as e:
            logger.error("Error processing conversation for project %s: %s", project_id, str(e))
            return AutoUpdateResult(
                success=False,
                updates_applied=[],
                updates_rejected=[],
                phase_advanced=False,
                notifications=[],
                errors=[str(e)]
            )
    
    def _extract_update_candidates(self, project_id: str, user_input: str, assistant_reply: str) -> List[UpdateCandidate]:
        """会話から更新候補を抽出"""
        candidates = []
        combined_text = f"{user_input} {assistant_reply}"
        
        for update_type, config in self.update_patterns.items():
            for pattern in config["patterns"]:
                matches = re.finditer(pattern, combined_text, re.IGNORECASE)
                for match in matches:
                    candidate = self._create_update_candidate(
                        project_id,
                        update_type,
                        match,
                        config,
                        combined_text
                    )
                    if candidate:
                        candidates.append(candidate)
        
        # 追加の特定ロジック
        candidates.extend(self._extract_task_updates(project_id, combined_text))
        candidates.extend(self._extract_milestone_updates(project_id, combined_text))
        
        return candidates
    
    def _create_update_candidate(self, project_id: str, update_type: str, match: re.Match, 
                                config: Dict[str, Any], text: str) -> Optional[UpdateCandidate]:
        """正規表現マッチから更新候補を作成"""
        
        project_data = get_project(project_id, self.projects_dir)
        if not project_data:
            return None
        
        timestamp = datetime.utcnow().isoformat()
        
        if update_type == "task_completion":
            task_name = match.group(1).strip()
            
            # バリデーション: 意味のないフラグメントを除外
            if not self._is_valid_task_description(task_name):
                return None
                
            return UpdateCandidate(
                field="task_completion",
                old_value=None,
                new_value={"task": task_name, "status": "completed"},
                confidence=config["confidence"],
                source="auto_pattern_match",
                reasoning=f"タスク完了パターンにマッチ: '{task_name}'",
                timestamp=timestamp
            )
        
        elif update_type == "task_creation":
            task_name = match.group(1).strip()
            
            # バリデーション: 意味のないフラグメントを除外
            if not self._is_valid_task_description(task_name):
                return None
                
            return UpdateCandidate(
                field="new_task",
                old_value=None,
                new_value={"description": task_name, "status": "pending"},
                confidence=config["confidence"],
                source="auto_pattern_match",
                reasoning=f"新規タスクパターンにマッチ: '{task_name}'",
                timestamp=timestamp
            )
        
        elif update_type == "blocker_identification":
            issue_description = match.group(1).strip()
            blocking_issues = project_data.get("blocking_issues", [])
            if not isinstance(blocking_issues, list):
                blocking_issues = []
            
            return UpdateCandidate(
                field="blocking_issues",
                old_value=blocking_issues,
                new_value=blocking_issues + [{
                    "description": issue_description,
                    "identified_at": timestamp,
                    "status": "active"
                }],
                confidence=config["confidence"],
                source="auto_pattern_match",
                reasoning=f"ブロッカー識別パターンにマッチ: '{issue_description}'",
                timestamp=timestamp
            )
        
        elif update_type == "progress_update":
            task_name = match.group(1).strip()
            progress = int(match.group(2))
            return UpdateCandidate(
                field="task_progress",
                old_value=None,
                new_value={"task": task_name, "progress": progress},
                confidence=config["confidence"],
                source="auto_pattern_match",
                reasoning=f"進捗更新パターンにマッチ: '{task_name}' {progress}%",
                timestamp=timestamp
            )
        
        return None
    
    def _extract_task_updates(self, project_id: str, text: str) -> List[UpdateCandidate]:
        """タスク関連の更新を抽出"""
        candidates = []
        project_data = get_project(project_id, self.projects_dir)
        if not project_data:
            return candidates
        
        tasks = project_data.get("tasks", [])
        if not isinstance(tasks, list):
            return candidates
        
        # 既存タスクの状態更新を検出
        for task in tasks:
            if not isinstance(task, dict):
                continue
                
            task_desc = task.get("description", "")
            task_id = task.get("id")
            
            if task_desc and task_id:
                # タスク完了の検出
                completion_patterns = [
                    rf"{re.escape(task_desc)}.*(?:完了|終了|済み|done|finished)",
                    rf"(?:完了|終了|済み|done|finished).*{re.escape(task_desc)}"
                ]
                
                for pattern in completion_patterns:
                    if re.search(pattern, text, re.IGNORECASE):
                        candidates.append(UpdateCandidate(
                            field="task_status_update",
                            old_value=task.get("status"),
                            new_value="completed",
                            confidence=0.9,
                            source="task_matching",
                            reasoning=f"タスク '{task_desc}' の完了を検出",
                            timestamp=datetime.utcnow().isoformat()
                        ))
        
        return candidates
    
    def _extract_milestone_updates(self, project_id: str, text: str) -> List[UpdateCandidate]:
        """マイルストーン関連の更新を抽出"""
        candidates = []
        
        # マイルストーン達成の検出
        milestone_patterns = [
            r"(?:マイルストーン|milestone)\s*(.+?)(?:達成|完了|クリア)",
            r"(.+?)(?:マイルストーン|milestone)(?:を|が)(?:達成|完了|クリア)"
        ]
        
        for pattern in milestone_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                milestone_name = match.group(1).strip()
                candidates.append(UpdateCandidate(
                    field="milestone_achievement",
                    old_value=None,
                    new_value={
                        "name": milestone_name,
                        "achieved_at": datetime.utcnow().isoformat(),
                        "status": "completed"
                    },
                    confidence=0.85,
                    source="milestone_pattern",
                    reasoning=f"マイルストーン達成を検出: '{milestone_name}'",
                    timestamp=datetime.utcnow().isoformat()
                ))
        
        return candidates
    
    def _apply_update_candidate(self, project_id: str, candidate: UpdateCandidate) -> bool:
        """更新候補を実際に適用"""
        
        try:
            if candidate.field == "task_completion":
                return self._apply_task_completion(project_id, candidate)
            elif candidate.field == "new_task":
                return self._apply_new_task(project_id, candidate)
            elif candidate.field == "blocking_issues":
                return update_project_field(project_id, "blocking_issues", candidate.new_value, self.projects_dir)
            elif candidate.field == "task_status_update":
                return self._apply_task_status_update(project_id, candidate)
            elif candidate.field == "milestone_achievement":
                return self._apply_milestone_achievement(project_id, candidate)
            else:
                logger.warning("Unknown update field: %s", candidate.field)
                return False
                
        except Exception as e:
            logger.error("Error applying update candidate %s: %s", candidate.field, str(e))
            return False
    
    def _apply_task_completion(self, project_id: str, candidate: UpdateCandidate) -> bool:
        """タスク完了の適用"""
        project_data = get_project(project_id, self.projects_dir)
        if not project_data:
            return False
        
        tasks = project_data.get("tasks", [])
        if not isinstance(tasks, list):
            return False
        
        task_name = candidate.new_value.get("task", "")
        
        # 柔軟なマッチングでタスクを見つけて更新
        updated = False
        for task in tasks:
            if isinstance(task, dict) and task.get("description"):
                task_desc = task["description"].lower()
                task_name_lower = task_name.lower()
                
                # 直接マッチまたは部分マッチ
                if (task_name_lower in task_desc or task_desc in task_name_lower or
                    # 主要キーワードマッチング（"ログイン機能"など）
                    self._fuzzy_match(task_name_lower, task_desc)):
                    task["status"] = "completed"
                    task["completed_at"] = candidate.timestamp
                    updated = True
                    break
        
        if updated:
            return update_project_field(project_id, "tasks", tasks, self.projects_dir)
        
        return False
    
    def _apply_new_task(self, project_id: str, candidate: UpdateCandidate) -> bool:
        """新規タスクの追加"""
        from .project_service import add_task
        
        try:
            task_desc = candidate.new_value.get("description", "")
            if task_desc:
                # デフォルトの期限を設定（1週間後）
                due_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
                add_task(project_id, task_desc, due_date, "auto_detected", self.projects_dir)
                return True
        except Exception as e:
            logger.error("Error adding new task: %s", str(e))
        
        return False
    
    def _apply_task_status_update(self, project_id: str, candidate: UpdateCandidate) -> bool:
        """タスクステータス更新の適用"""
        # 実装は _apply_task_completion と類似
        return self._apply_task_completion(project_id, candidate)
    
    def _apply_milestone_achievement(self, project_id: str, candidate: UpdateCandidate) -> bool:
        """マイルストーン達成の記録"""
        project_data = get_project(project_id, self.projects_dir)
        if not project_data:
            return False
        
        milestones = project_data.get("milestones", [])
        if not isinstance(milestones, list):
            milestones = []
        
        milestone = candidate.new_value
        milestones.append(milestone)
        
        return update_project_field(project_id, "milestones", milestones, self.projects_dir)
    
    def _check_and_advance_phase(self, project_id: str) -> bool:
        """フェーズ進行チェックと自動進行"""
        try:
            can_advance, requirements = self.lifecycle_manager.can_advance_to_next_phase(project_id)
            if can_advance:
                return self.lifecycle_manager.advance_phase(project_id)
        except Exception as e:
            logger.error("Error checking phase advancement for project %s: %s", project_id, str(e))
        
        return False
    
    def _generate_notifications(self, project_id: str, applied_updates: List[UpdateCandidate], 
                              phase_advanced: bool) -> List[Dict[str, Any]]:
        """通知を生成"""
        notifications = []
        
        if applied_updates:
            notifications.append({
                "type": "auto_updates_applied",
                "message": f"{len(applied_updates)}件の自動更新を適用しました",
                "details": [f"- {u.reasoning}" for u in applied_updates],
                "timestamp": datetime.utcnow().isoformat()
            })
        
        if phase_advanced:
            current_phase = self.lifecycle_manager.get_current_phase(project_id)
            notifications.append({
                "type": "phase_advancement",
                "message": f"プロジェクトが{current_phase.value}フェーズに進行しました",
                "timestamp": datetime.utcnow().isoformat()
            })
        
        return notifications
    
    def get_pending_updates(self, project_id: str) -> List[UpdateCandidate]:
        """保留中の更新候補を取得"""
        # 実装: 低信頼度の更新候補を一時保存・取得する機能
        # ここでは簡易実装
        return []
    
    def approve_pending_update(self, project_id: str, candidate_id: str) -> bool:
        """保留中の更新を承認"""
        # 実装: 保留中の更新候補を手動承認する機能
        return True
    
    def reject_pending_update(self, project_id: str, candidate_id: str) -> bool:
        """保留中の更新を拒否"""
        # 実装: 保留中の更新候補を拒否する機能
        return True
    
    def _fuzzy_match(self, text1: str, text2: str) -> bool:
        """柔軟なマッチング（日本語対応）"""
        # 主要なキーワードを抽出
        keywords1 = self._extract_keywords(text1)
        keywords2 = self._extract_keywords(text2)
        
        # キーワードが1つ以上一致する場合はマッチとみなす
        common_keywords = set(keywords1) & set(keywords2)
        return len(common_keywords) >= 1
    
    def _extract_keywords(self, text: str) -> List[str]:
        """テキストからキーワードを抽出"""
        import re
        
        keywords = []
        
        # カタカナ語を抽出
        katakana = re.findall(r'[ァ-ヾ]+', text)
        keywords.extend(katakana)
        
        # 漢字語を抽出  
        kanji = re.findall(r'[一-龯]+', text)
        keywords.extend(kanji)
        
        # ひらがな語を抽出（助詞は除外）
        hiragana = re.findall(r'[あ-ん]+', text)
        keywords.extend([h for h in hiragana if h not in ['の', 'を', 'が', 'に', 'は', 'で', 'と', 'から', 'まで']])
        
        # 英数字の単語も抽出
        english_keywords = re.findall(r'[a-zA-Z0-9]+', text)
        keywords.extend(english_keywords)
        
        # 2文字以上のキーワードのみ
        return [kw for kw in keywords if len(kw) >= 2]
    
    def _is_valid_task_description(self, description: str) -> bool:
        """タスク説明の有効性を検証"""
        if not description or len(description.strip()) < 3:
            return False
        
        # 無効なパターンを除外
        invalid_patterns = [
            r'^[。、！？\s]*$',  # 句読点のみ
            r'^[はをがにでとからまでもや\s]*$',  # 助詞のみ
            r'^[\*\(\)（）\[\]「」『』\s]*$',  # 記号のみ
            r'^[のですますである\s]*$',  # 語尾のみ
            r'^\*\*.*\*\*$',  # Markdown太字のみ
            r'^を[追加|更新|削除]',  # 文の一部
            r'^[や|と|も].*',  # 文の一部
            r'.*[ですか|でしょうか|ますか]$',  # 質問文の一部
            r'^[（|＜].*[）|＞]$',  # 説明の括弧部分のみ
            r'^[上位|下位]\d+件',  # リストの説明部分
            r'^が\d+件',  # 数量説明のみ
            r'^の[期限|期日|スケジュール]',  # 属性説明のみ
        ]
        
        for pattern in invalid_patterns:
            if re.search(pattern, description.strip()):
                return False
        
        # 最小限の意味を持つ内容かチェック
        # 動詞または名詞が含まれているかの簡易チェック
        meaningful_patterns = [
            r'[調査|作成|実装|検討|確認|準備|計画|設計|開発|テスト|修正|更新|追加|削除]',  # 動詞
            r'[登山|ルート|装備|リスト|機能|システム|データ|ファイル|コード|文書]',  # 名詞
        ]
        
        has_meaning = any(re.search(pattern, description) for pattern in meaningful_patterns)
        
        return has_meaning