# AI Request Locations Analysis

## Overview
This document analyzes which AI request locations are actually being used in the VPM Ariade codebase, based on the implementation and actual log data.

## AI Request Locations (RequestKind Enum)

The `RequestKind` enum in `core/log_schema.py` defines all possible AI request types:

```python
class RequestKind(Enum):
    UI_CHAT = "ui_chat"                               # Main UI chat interactions
    PROJECT_DETAIL = "project_detail"                  # Project details generation
    CONVERSATION_ANALYSIS = "conversation_analysis"    # Conversation analysis
    INTENT_DETECT = "intent_detect"                   # Intent detection
    MINUTES = "minutes"                                # Minutes generation
    FILE_EDIT = "file_edit"                           # File editing
    CODE_GENERATION = "code_generation"               # Code generation
    SPEC_SCAN = "spec_scan"                          # Specification scanning
    DOCS_UPDATE = "docs_update"                       # Documentation updates
    DOC_ANALYSIS = "doc_analysis"                     # Document analysis
    CAPABILITY_PROPOSAL = "capability_proposal"        # Capability proposals
    SIMPLE_QA = "simple_qa"                           # Simple Q&A
    RESEARCH = "research"                             # Research tasks
```

## Actually Used AI Request Locations

Based on the codebase analysis and log files, the following RequestKind values are actually being used:

### 1. **UI_CHAT** ✅
- **Location**: `core/ai_project_manager.py` (line 118)
- **Usage**: Main AI-First chat processing for user interactions
- **Function**: `process_user_input()` - processes all user chat inputs
- **Log Evidence**: Found in logs as "ui_chat"

### 2. **PROJECT_DETAIL** ✅  
- **Location**: `core/pages.py` (line 260)
- **Usage**: Generating AI explanations of project details
- **Function**: `_generate_ai_explanation()` in `ProjectDetailsPage`
- **Log Evidence**: Found 8 times in logs as "project_detail"

### 3. **CONVERSATION_ANALYSIS** ✅
- **Location**: `core/simple_conversation_analyzer.py` (line 80)
- **Usage**: Analyzing conversations to update project information
- **Function**: `analyze_and_update_project()`
- **Log Evidence**: Not found in current logs (may be unused feature)

### 4. **INTENT_DETECT** ✅
- **Location**: `core/ai_intent_detector.py` (line 330)
- **Usage**: Detecting task removal intent from user input
- **Function**: `detect_task_removal_intent()`
- **Log Evidence**: Not found in current logs

### 5. **SPEC_SCAN** ✅
- **Location**: Found in logs
- **Usage**: Specification scanning (implementation not found in main flow)
- **Log Evidence**: Found 1 time in logs as "spec_scan"

## Unused AI Request Locations

The following RequestKind values are defined but not currently used in the main application flow:

- **MINUTES** ❌ - No log_call usage found
- **FILE_EDIT** ❌ - No log_call usage found
- **CODE_GENERATION** ❌ - No log_call usage found  
- **DOCS_UPDATE** ❌ - No log_call usage found
- **DOC_ANALYSIS** ❌ - No log_call usage found
- **CAPABILITY_PROPOSAL** ❌ - No log_call usage found
- **SIMPLE_QA** ❌ - No log_call usage found
- **RESEARCH** ❌ - No log_call usage found

## Call Chain Summary

### Main User Interaction Flow:
1. **app.py** → `render_chat_interface()` 
2. → `core/chat_handler_ai.py` → `process_chat_input_ai()`
3. → `core/ai_project_manager.py` → `process_user_input()` 
4. → Uses **UI_CHAT** RequestKind

### Project Details Page:
1. **app.py** → `render_page_content()` → `ProjectDetailsPage.render()`
2. → `core/pages.py` → `_generate_ai_explanation()`
3. → Uses **PROJECT_DETAIL** RequestKind

### Intent Detection (Task Removal):
1. **core/ai_intent_detector.py** → `detect_task_removal_intent()`
2. → Uses **INTENT_DETECT** RequestKind

### Conversation Analysis:
1. **core/simple_conversation_analyzer.py** → `analyze_and_update_project()`
2. → Uses **CONVERSATION_ANALYSIS** RequestKind

## Recommendations

1. **Remove Unused RequestKind Values**: Consider removing the unused enum values to simplify the codebase
2. **Consolidate AI Calls**: The main AI interaction happens through UI_CHAT, which handles multiple action types
3. **Document Usage**: Add comments in `log_schema.py` indicating which RequestKind values are actively used
4. **Log Monitoring**: Set up monitoring for unused RequestKind values to identify deprecated features

## Log File Observations

- Log files use "kind" field instead of "request_kind" field
- Most AI interactions go through UI_CHAT (general chat) and PROJECT_DETAIL (project page)
- The AI-First philosophy is implemented primarily through the unified `AIProjectManager` class