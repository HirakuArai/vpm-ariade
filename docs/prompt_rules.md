# AI Project Manager Prompt Rules v3.0 - Project Update Spec v1.0

## Overview
Updated prompt rules incorporating Project Update Spec v1.0 with generic property patch functionality.

## Core Rules

### 1. Project Information Updates (NEW - Project Update Spec v1.0)
**Keywords**: 「日程」「参加者」「予算」「場所」「ステータス」等のプロジェクト属性更新
- **Action**: `update_project`
- **Parameters**: Use `properties` object with multiple fields
- **Examples**:
  - 「参加者は4名です」→ `properties: {"participants_count": 4}`
  - 「日程は8月2日から3日です」→ `properties: {"start_date": "2025-08-02", "end_date": "2025-08-03"}`
  - Combined: `properties: {"participants_count": 4, "start_date": "2025-08-02", "end_date": "2025-08-03"}`

### 2. Project Creation (Context-Dependent)
- **Home Chat (No Project Selected)**: 「プロジェクトを作成」「プロジェクトとして設定」→ `create_project`
- **Project Chat (Project Selected)**: Same keywords → `general_discussion`

### 3. Task Operations
- **Create**: 「作業」「やる」「実装」「対応」→ `create_task`
- **Remove**: 「消してください」「削除して」「取り除いて」→ `remove_task`

### 4. Information Requests
- **Keywords**: 「教えて」「見せて」「確認したい」→ `information_request`

### 5. General Discussion
- **Keywords**: 「どうすれば」「方法は」「アドバイス」→ `general_discussion`

## JSON Response Format

```json
{
  "intent": "project_management|conversation|clarification",
  "action_type": "create_project|create_task|remove_task|update_project|information_request|general_discussion",
  "reasoning": "この判断に至った理由と分析",
  "confidence": 0.0-1.0,
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

## Project Update Examples

### Example 1: Participants Update
Input: 「参加者は4名です。」
Context: プロジェクト選択済み
```json
{
  "intent": "project_management",
  "action_type": "update_project",
  "reasoning": "プロジェクト情報（参加者数）の更新要求",
  "confidence": 0.9,
  "target_items": [
    {
      "type": "project",
      "action": "set_properties",
      "parameters": {
        "identifier": "proj-20250629-182909-854",
        "properties": {
          "participants_count": 4
        }
      }
    }
  ],
  "response_content": "参加者数4名で設定しました。",
  "suggested_follow_ups": ["参加者の役割分担を決めたい", "スケジュールを調整したい"]
}
```

### Example 2: Date Update
Input: 「日程は2025年8月2日、3日の2日間です。」
```json
{
  "intent": "project_management",
  "action_type": "update_project",
  "reasoning": "プロジェクト日程の更新要求",
  "confidence": 0.95,
  "target_items": [
    {
      "type": "project",
      "action": "set_properties",
      "parameters": {
        "identifier": "proj-20250629-182909-854",
        "properties": {
          "start_date": "2025-08-02",
          "end_date": "2025-08-03"
        }
      }
    }
  ],
  "response_content": "日程を2025年8月2日〜3日で設定しました。",
  "suggested_follow_ups": ["会場の手配について相談したい", "当日のスケジュールを決めたい"]
}
```

### Example 3: Combined Update
Input: 「参加者は4名で、日程は8月2日、3日です。」
```json
{
  "intent": "project_management", 
  "action_type": "update_project",
  "reasoning": "複数のプロジェクト情報（参加者数・日程）の同時更新",
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
  "suggested_follow_ups": ["参加者の役割分担を決めたい", "会場準備について相談したい"]
}
```

## Migration Notes

### DEPRECATED Actions
- `update_status` - Use `update_project` with `properties: {"status": "ACTIVE"}` instead

### New Features (Project Update Spec v1.0)
- ✅ Schema-driven validation via `schemas/project_schema.json`
- ✅ Generic `apply_property_patch()` function
- ✅ Multi-field updates in single operation
- ✅ Automatic change_log tracking
- ✅ User-friendly Japanese response messages

---

**Version**: 3.0
**Last Updated**: 2025-07-01
**Implements**: Project Update Spec v1.0
**Author**: Kai VPM Team