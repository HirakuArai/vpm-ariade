# API Prompts Analysis

## Overview
This document analyzes all API prompt locations in the VPM Ariade codebase, documenting where prompts are constructed and how they're used for different AI interactions.

## Main Prompt Locations

### 1. AI Project Manager System Prompt
**Location**: `core/ai_project_manager.py` → `_get_ai_pm_system_prompt()` (line 179-251)

**Purpose**: Main system prompt for the AI-First Project Manager

**Key Features**:
- Defines the AI's role as an experienced virtual project manager
- Sets basic principles: natural understanding, flexible response, learning orientation, emergent thinking
- Provides detailed judgment rules for different action types
- Specifies JSON response format for structured action plans

**Action Types Handled**:
- `create_project` - Project creation requests
- `create_task` - Task creation 
- `remove_task` - Task deletion/removal
- `update_status` - Status updates
- `information_request` - Information queries
- `general_discussion` - General conversation

### 2. Project Details Generation Prompt
**Location**: `core/pages.py` → `_generate_ai_explanation()` (line 247-274)

**Purpose**: Generate human-readable explanations of project data

**System Prompt**: "あなたはプロジェクトマネジメントの専門家で、複雑なプロジェクト情報をわかりやすく整理して説明することが得意です。"

**User Prompt Structure**:
- Requests explanation of project JSON data
- Specifies 7 required elements (overview, status, stakeholders, milestones, risks, team, updates)
- Requests markdown formatting with emojis

### 3. Intent Detection Prompts

#### Project Creation Intent Detection
**Location**: `core/ai_intent_detector.py` → `detect_project_creation_intent()` (line 74-114)

**Key Features**:
- Strict criteria for identifying creation intent
- Exclusion patterns for questions/suggestions
- Confidence scoring (0.8+ for clear requests)
- Extracts project name, description, and metadata

#### Task Addition Intent Detection  
**Location**: `core/ai_intent_detector.py` → `detect_task_addition_intent()` (line 183-221)

**Key Features**:
- Very strict criteria to avoid false positives
- Explicit exclusion of information requests, deletions, general conversation
- Extracts task description, due date, priority
- Additional metadata extraction (assignee, category, dependencies)

#### Task Removal Intent Detection
**Location**: `core/ai_intent_detector.py` → `detect_task_removal_intent()` (line 293-324)

**Key Features**:
- Identifies deletion/removal requests
- Handles specific IDs, duplicates, or all tasks
- Strict exclusion of implementation requests about deletion

### 4. Conversation Analysis Prompt
**Location**: `core/simple_conversation_analyzer.py` → `analyze_and_update_project()` (line 57-75)

**Purpose**: Analyze conversations to extract project updates

**System Prompt**: Built by `_build_update_prompt()` (implementation not shown in excerpt)

**User Prompt Structure**:
- Provides current project info as JSON
- Includes conversation text
- Requests identification of necessary updates
- Emphasizes extracting only clear information, no speculation

### 5. Unified Prompt Builder
**Location**: `core/ai_project_manager.py` → `_build_unified_prompt()` (line 253-292)

**Components**:
- User input
- Project context summary (ID, status, recent tasks)
- Conversation history summary (last 6 messages)
- User patterns (placeholder for future learning)

**Instructions**: 
- Understand true intent behind surface words
- Consider project situation and priorities
- Identify most valuable next steps
- Maintain natural, constructive conversation

## Prompt Patterns

### Common Elements Across Prompts:
1. **Role Definition**: Clear specification of AI's expertise/role
2. **Strict Criteria**: Explicit inclusion/exclusion rules
3. **JSON Response Format**: Structured output for parsing
4. **Confidence Scoring**: Self-assessment of decision confidence
5. **Context Awareness**: Project state and conversation history

### Temperature Settings:
- Intent Detection: 0.1 (very deterministic)
- General Chat: 0.3 (somewhat deterministic)  
- Project Details: 0.7 (more creative)

### Model Usage:
- Primary model: "gpt-4.1" (configured via `core/v2/openai_config.py`)
- Consistent across all prompt locations

## Recommendations

1. **Centralize Prompt Management**: Consider creating a dedicated prompt template system
2. **Version Control**: Add versioning to prompts for A/B testing
3. **Prompt Optimization**: Monitor success rates per prompt type
4. **Internationalization**: Current prompts mix Japanese and English - consider standardizing
5. **Prompt Length**: Some prompts are quite long - consider optimization for token efficiency

## Key Observations

1. The AI-First philosophy is well-implemented with unified decision-making
2. Prompts are carefully crafted to avoid false positives (especially for destructive actions)
3. The system uses structured JSON responses for reliable parsing
4. Context (project state, conversation history) is consistently provided
5. The main interaction flow uses a sophisticated action planning system rather than simple pattern matching