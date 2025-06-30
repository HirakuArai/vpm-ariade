# AI Project Manager Prompt Rules v2.0

## Overview
This document defines the context-dependent prompt rules for the AI Project Manager, ensuring appropriate behavior based on whether a project is currently selected or not.

## Context-Dependent Intent Routing

### 1. Project Creation Intent Detection

#### Rule: Context-Dependent Project Creation
**Problem**: Previously, project creation keywords would always trigger `create_project` action regardless of context, causing unwanted project creation within existing project conversations.

**Solution**: Project creation intent is now context-dependent:

- **Home Chat (No Project Selected)**:
  - Keywords: "プロジェクトを作成", "プロジェクトとして設定", "新しいプロジェクト", etc.
  - Action: `create_project`
  - Reasoning: User is in home context with no project selected

- **Project Chat (Project Already Selected)**:
  - Same keywords → Action: `general_discussion`
  - Reasoning: User is discussing project management within existing project context
  - Exception: Explicit "新しい" (new) keyword still triggers `create_project`

#### Implementation Location
- File: `core/ai_project_manager.py`
- Method: `_get_ai_pm_system_prompt()`
- Lines: 198-201 (updated prompt rules)

### 2. Context Detection Logic

#### Project Context Determination
```python
# Determine if project is selected
project_selected = bool(project_context and project_context.get("identifier"))

# Set appropriate subkind for logging
subkind = RequestContext.PROJECT_CHAT if project_selected else RequestContext.HOME_CHAT
```

#### Prompt Context Information
The AI receives explicit context information:
- **Home Chat**: "プロジェクトが選択されていません"
- **Project Chat**: "プロジェクト: proj-xxx, ステータス: DRAFT, タスク数: 3件"

### 3. Updated Prompt Examples

#### Example 1: Home Chat Context
```
Input: "花火大会をプロジェクトとして設定してください"
Context: "プロジェクトが選択されていません"
Expected Output:
{
  "action_type": "create_project",
  "reasoning": "プロジェクト未選択状態でプロジェクト作成を要求している"
}
```

#### Example 2: Project Chat Context
```
Input: "このプロジェクトをもっと本格的にプロジェクトとして進めたいです"
Context: "プロジェクト: proj-xxx, ステータス: DRAFT"
Expected Output:
{
  "action_type": "general_discussion",
  "reasoning": "既にプロジェクト選択済みのため、プロジェクト運営に関する相談として処理"
}
```

### 4. Logging Enhancement

#### RequestContext Enum
New `RequestContext` enum added for granular analysis:
- `HOME_CHAT`: Chat from home page (no project selected)
- `PROJECT_CHAT`: Chat from within a specific project
- `GENERAL`: General context

#### LogEntry Schema Update
```python
class LogEntry(BaseModel):
    # ... existing fields ...
    subkind: Optional[RequestContext] = Field(None, description="Request context for granular analysis")
```

#### Usage in Code
```python
subkind = RequestContext.PROJECT_CHAT if project_context else RequestContext.HOME_CHAT
with log_call("kai", RequestKind.UI_CHAT, subkind=subkind) as log:
    # ... LLM call ...
```

## Testing Strategy

### Test Coverage
- **File**: `tests/test_intent_routing.py`
- **Scope**: Context-dependent intent routing
- **Test Cases**:
  1. Home chat project creation intents
  2. Project chat context handling
  3. RequestContext logging verification

### Test Examples
```python
def test_home_chat_project_creation():
    """Test project creation intent from home chat (no project selected)"""
    result = ai_pm.process_user_input(
        user_input="花火大会をプロジェクトとして設定してください",
        project_context={},  # Empty = no project selected
        conversation_history=[]
    )
    assert result.action_type == "create_project"

def test_project_chat_context_handling():
    """Test project-related keywords within existing project context"""
    project_context = {"identifier": "proj-test-123", "status": "DRAFT"}
    result = ai_pm.process_user_input(
        user_input="このプロジェクトをプロジェクトとして進めたい",
        project_context=project_context,
        conversation_history=[]
    )
    assert result.action_type == "general_discussion"
```

## Migration Notes

### Breaking Changes
1. `LogEntry` schema now includes optional `subkind` field
2. `log_call()` function signature updated with `subkind` parameter
3. AI prompt behavior changed for project creation in project contexts

### Backward Compatibility
- Existing logs without `subkind` remain valid (field is optional)
- Old `log_call()` usage continues to work (subkind defaults to None)

## Future Enhancements

### Planned Improvements
1. **Machine Learning Integration**: Use historical context patterns to improve intent detection
2. **User Preference Learning**: Adapt behavior based on individual user patterns
3. **Multi-Project Context**: Handle scenarios where multiple projects are referenced
4. **Context Confidence Scoring**: Add confidence metrics for context detection

### Analytics Opportunities
With `subkind` logging, we can now analyze:
- Home vs. Project chat usage patterns
- Intent distribution by context
- Context-specific error rates
- User behavior transitions between contexts

---

**Version**: 2.0  
**Last Updated**: 2025-06-30  
**Author**: AI Project Manager Team  
**Related Files**: 
- `core/ai_project_manager.py`
- `core/log_schema.py`
- `core/prompt_logger.py`
- `tests/test_intent_routing.py`