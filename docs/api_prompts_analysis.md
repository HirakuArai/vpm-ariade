# Kai VPM - OpenAI API Prompts and Request Patterns Analysis

## Overview

This document analyzes all the different OpenAI API request patterns and prompts used throughout the Kai VPM (Virtual Project Manager) application. The analysis covers system prompts, user prompts, models used, temperature settings, and different contexts where API calls are made.

## 1. Core AI Components

### 1.1 AI Project Manager (`core/ai_project_manager.py`)

**Purpose**: Unified AI decision-making for natural project management

**Model**: `gpt-4o`
**Temperature**: `0.3`
**Max Tokens**: `1000`

**System Prompt**:
```
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
1. **削除・除去要求**: 「消してください」「削除して」「取り除いて」は必ずremove_taskアクション
2. **情報要求**: 「教えて」「見せて」「確認したい」は必ずinformation_requestアクション
3. **タスク作成条件**: 明確な「作業」「やる」「実装」「対応」等の実行意図がある場合のみcreate_task
4. **質問・相談**: 「どうすれば」「方法は」「アドバイス」はgeneral_discussionアクション

## 応答形式:
以下のJSON形式で必ず応答してください：
{
  "intent": "project_management|conversation|clarification",
  "action_type": "create_task|remove_task|update_status|information_request|general_discussion",
  "reasoning": "この判断に至った理由と分析",
  "confidence": 0.0-1.0の信頼度,
  "target_items": [...],
  "response_content": "ユーザーへの自然で有用な応答メッセージ",
  "suggested_follow_ups": ["次に聞いてみたい質問例1", "推奨される次の行動2"]
}
```

**User Prompt Construction**:
- Includes current user input
- Project context summary (ID, status, recent tasks)
- Recent conversation history (last 6 messages)
- User behavior patterns (future implementation)

### 1.2 AI Intent Detector (`core/ai_intent_detector.py`)

**Purpose**: AI-based user intent detection for project and task management

#### Project Creation Intent Detection
**Model**: `gpt-3.5-turbo`
**Temperature**: `0.1`
**Max Tokens**: `500`

**Prompt includes**:
- Clear creation intent criteria
- Exclusion patterns (questions, suggestions, consultations)
- Confidence threshold requirements (0.8+ for clear requests)
- JSON response format with reasoning

#### Task Addition Intent Detection
**Model**: `gpt-3.5-turbo`
**Temperature**: `0.1`
**Max Tokens**: `400`

**Prompt includes**:
- Execution intent patterns
- Strict exclusion criteria (information requests, deletions, conversations)
- Task details extraction (description, due date, priority)

#### Task Removal Intent Detection
**Model**: `gpt-4o-mini`
**Temperature**: `0.1`
**Max Tokens**: `300`

**System Role**: "あなたはタスク削除意図の検出専門家です。ユーザーの発言を正確に分析してください。"

### 1.3 AI Quality Manager (`core/ai_quality_manager.py`)

**Purpose**: AI response quality monitoring and error handling

**Features**:
- Retry logic with exponential backoff
- Response quality scoring
- Error type classification
- Metrics tracking

**Request Parameters**:
- Configurable model, temperature, and max_tokens
- Default timeout: 30 seconds
- Max retries: 3
- Quality threshold: 0.7

### 1.4 AI Context Manager (`core/ai_context_manager.py`)

**Purpose**: Advanced conversation context management

#### Conversation Summarization
**Model**: `gpt-3.5-turbo`
**Temperature**: `0.3`
**Max Tokens**: `300`

**System Prompt**:
```
あなたは会話要約の専門家です。簡潔で有用な要約を作成してください。
```

**Summary Format**:
- 主要トピック
- 重要な決定/合意
- 次のアクション
- キーワード

## 2. Conversation Analysis

### 2.1 Conversation Analyzer (`core/conversation_analyzer.py`)

**Purpose**: Extract structured information from conversations

**Model**: `gpt-4.1`
**Temperature**: `0.1`
**Max Tokens**: `1500`

**System Prompt Structure**:
```
あなたは会話から具体的な情報を抽出する専門家です。

# 抽出対象の情報
[Dynamic field list based on project schema]

# 抽出ルール
1. **明示的な情報のみ** - 推測や想定は含めない
2. **具体的な値** - 曖昧な表現ではなく明確な値を抽出
3. **信頼度評価** - 情報の確実性を0.0〜1.0で評価
4. **文脈考慮** - 質問と回答の流れを理解する
5. **更新情報も抽出** - 既存の値から変更された情報も抽出する

# 出力形式
[JSON format specification]
```

## 3. Charter Generation

### 3.1 OpenAI Helper (`libs/openai_helper.py`)

**Purpose**: Conversational charter generation

**Model**: `gpt-4.1`
**Temperature**: `0.7`
**Max Tokens**: `1000`

**System Prompt**:
```
You are **Kai**, an expert project manager.

* Goal: help the user define a complete project charter via natural conversation.
* Ask **exactly ONE** question at a time in Japanese.
* At each turn follow this algorithm:
  1. Inspect the JSON charter schema keys and note which keys are still empty or [].
  2. Choose the **most important missing key** and ask a concise, domain‑appropriate question to fill it.
  3. Never repeat a question that is semantically similar to any of the last 3 questions.
  4. Keep the tone friendly and practical; avoid abstract business jargon if the context is leisure / personal projects.
* When **all keys are filled**, reply with:
  <charter_complete/>
  ```json
  { <fully‑populated charter JSON> }
  ```
```

#### Next Question Generation (Meta-planner)
**Model**: `gpt-4.1`
**Temperature**: `0.2`
**Max Tokens**: `50`

**Controller Prompt**: Determines the most important missing charter key based on logical dependencies

## 4. Project Context and System Prompts

### 4.1 Project Prompt (`core/project_prompt.py`)

**Base System Prompt Construction**:
- Loads from `docs/base_os_rules.md`
- Includes DSL definitions from `dsl/integrated_dsl.jsonl`
- Adds project definition and architecture overview
- Appends current date/time context
- Includes project-specific context if selected

**Project Context includes**:
- Project overview, status, and ID
- Top 3 incomplete tasks
- Confirmed project details with confidence indicators
- Additional information (repository, deadline, budget)
- Critical response rules for information consistency

## 5. Minutes Generation

### 5.1 Minutes Utils (`core/minutes_utils.py`)

**Purpose**: Generate daily meeting minutes from conversations

**Model**: `gpt-4.1`
**Temperature**: `0`

**System Prompt**:
```
You are Kai's Minutes Assistant.
Output valid YAML (schema v2). Summarise decisions only.

<conversation>
{log_text}
</conversation>
```

## 6. Capability Generation Scripts

### 6.1 GPT Generate Capability (`scripts/gpt_generate_capability.py`)

**Purpose**: Generate Python function skeletons for new capabilities

**Model**: `gpt-4-1106-preview`
**Temperature**: `0.3`

**System Prompt**:
```
あなたはPython開発に精通したアシスタントです。
以下の機能IDが示す Kai に必要な機能について、日本語でその役割・目的を説明し、
Kai の core/ ディレクトリに追加すべき関数スケルトンを出力してください。

制約:
- docstring を詳細に記述すること
- 関数名は機能IDに準拠
- 実装は未完成で構いません。`pass` でOKです。
```

## 7. Common Patterns Observed

### Temperature Settings
- **0.1**: Intent detection, information extraction (high precision tasks)
- **0.2**: Meta-planning, priority determination
- **0.3**: General AI interactions, quality management
- **0.7**: Conversational charter generation (more creative)
- **0**: Minutes generation (deterministic summaries)

### Model Selection
- **gpt-4o**: Complex reasoning, project management decisions
- **gpt-4o-mini**: Simpler intent detection tasks
- **gpt-3.5-turbo**: Quick extraction and summarization tasks
- **gpt-4.1**: Main conversational model, charter generation

### Response Formats
1. **Structured JSON**: For actionable decisions and data extraction
2. **Natural Language**: For user-facing responses
3. **Hybrid**: JSON with embedded natural language explanations

### Context Management Strategies
1. **Sliding Window**: Recent N messages for context
2. **Summarization**: Compress older conversations
3. **Relevance Scoring**: Select context based on current query
4. **Token Budgeting**: Optimize context within token limits

### Error Handling
- Graceful degradation when AI unavailable
- Retry logic with exponential backoff
- Fallback to pattern-based extraction
- Quality scoring and confidence thresholds

## 8. Key Insights

1. **AI-First Philosophy**: The system avoids hardcoded rules and pattern matching, preferring unified AI decisions

2. **Contextual Understanding**: Multiple layers of context (project, conversation, user patterns) inform AI decisions

3. **Confidence-Based Actions**: All extractions and decisions include confidence scores for reliability

4. **Japanese Language Focus**: Most prompts are in Japanese, reflecting the target user base

5. **Structured Output Requirements**: Most API calls require specific JSON formats for downstream processing

6. **Quality Assurance**: Built-in quality management tracks performance and suggests improvements

7. **Modular Design**: Each AI component has a specific purpose with clear interfaces

This comprehensive system demonstrates sophisticated prompt engineering and context management for a production AI-powered project management application.