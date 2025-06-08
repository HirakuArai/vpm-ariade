# UI Migration Guide: Kai VPM v2 Multipage Application

## Overview

The Kai VPM v2 system has been refactored from a single-file Streamlit application into a structured multipage layout with improved navigation and user experience.

## Architecture

### File Structure
```
├── app_multipage.py          # Main entry point for multipage app
├── libs/
│   └── ui_layout.py          # Common UI functions and helpers
├── pages/
│   ├── page_1_new_project.py    # Charter generation via Q&A
│   ├── page_2_preview_charter.py # Charter editing and review
│   └── page_3_persona_and_wbs.py # Analysis and WBS generation
└── docs/
    └── ui_migration.md       # This documentation
```

### Legacy Files (Preserved)
- `streamlit_v2.py` - Original single-file application (not removed)
- `app.py` - Original chat-based Streamlit application

## How to Run

### Option 1: New Multipage Application (Recommended)
```bash
streamlit run app_multipage.py
```

### Option 2: Legacy Single-File Application
```bash
streamlit run streamlit_v2.py
```

### Option 3: Original Chat Application
```bash
streamlit run app.py
```

## Application Workflow

### Page 1: New Project (1️⃣)
**Purpose:** Create project charters through guided Q&A

**Features:**
- Interactive chat interface for charter generation
- Questions loaded from `data/charter_questions.yaml`
- Progress tracking through questions
- Smart answer parsing for different field types
- Automatic charter saving to `data/charters/`

**Navigation:** Automatically sets up charter file in session state for next pages

### Page 2: Preview Charter (2️⃣)
**Purpose:** Review and edit charter details before analysis

**Features:**
- Comprehensive charter overview display
- Tabbed editing interface:
  - **Basic Info:** Name, purpose, budget, deadline
  - **Goals & Scope:** Outcomes, scope in/out, success metrics
  - **Stakeholders:** Name and role management
  - **Timeline & Risks:** Milestones and risk assessment
- All sections use `st.data_editor` for dynamic editing
- Save changes back to charter file
- Validation and error handling

**Prerequisites:** Requires charter file from Page 1

### Page 3: Analysis & WBS (3️⃣)
**Purpose:** Run AI analysis and generate work breakdown structure

**Features:**
- **Persona Analysis:** Calls `core.v2.persona_core.analyze_charter()`
  - Priority goal ranking
  - Risk assessment with editable impact levels
  - Milestone recommendations
  - AI persona commentary
- **WBS Generation:** Calls `core.v2.planning_core.generate_wbs()`
  - Detailed task breakdown
  - Dependency mapping
  - Timeline visualization
  - Editable task properties (status, assignment, priority)
- **Results Export:** Save complete analysis to `data/results/`

**Prerequisites:** Requires charter file and analysis execution

## Session State Management

### Key Session Variables
```python
{
    "current_page": str,              # Current page identifier
    "selected_charter_file": str,     # Path to active charter file
    "charter_created": bool,          # Page 1 completion status
    "charter_reviewed": bool,         # Page 2 completion status  
    "analysis_complete": bool,        # Page 3 completion status
    "persona_result": dict,           # Persona analysis output
    "wbs_result": list,              # WBS generation output
    "edited_wbs_df": DataFrame       # User-edited WBS data
}
```

### Session Persistence
- Session state persists across page navigation
- Progress indicators show completion status
- Prerequisites check prevents invalid navigation
- Reset functionality available for starting over

## Common UI Components

### Located in `libs/ui_layout.py`

**Navigation:**
- `setup_sidebar()` - Unified sidebar with progress tracking
- `navigation_buttons()` - Previous/Next/Home navigation
- Automatic page routing and state management

**Data Handling:**
- `load_charter_data()` / `save_charter_data()` - YAML file operations
- `format_persona_results()` - Analysis result formatting
- `format_wbs_for_editor()` - WBS data preparation for editing
- `save_results_to_json()` - Export functionality

**Error Handling:**
- `@error_boundary` decorator for robust error management
- `check_prerequisites()` - Validation before page access
- Comprehensive error logging and user feedback

## Integration with Core v2 Modules

### Persona Analysis Integration
```python
from core.v2.persona_core import analyze_charter
result = analyze_charter(charter_file_path)
```

### WBS Generation Integration  
```python
from core.v2.planning_core import generate_wbs
wbs = generate_wbs(persona_result)
```

### Charter Questions Integration
```python
questions = get_charter_questions()  # Loads from data/charter_questions.yaml
```

## Data Flow

1. **Charter Creation:** Page 1 → `data/charters/charter_YYYYMMDD_HHMMSS.yaml`
2. **Charter Editing:** Page 2 → Updates same charter file
3. **Analysis Results:** Page 3 → `data/results/charter_name_analysis_YYYYMMDD_HHMMSS.json`

## Error Handling & Recovery

### Prerequisites Validation
- Each page checks for required session state
- User-friendly error messages with navigation guidance
- Automatic fallback to appropriate starting point

### File Operation Safety
- Graceful handling of missing/corrupt charter files
- Backup creation before overwrites
- Clear error reporting with recovery options

### Analysis Failures
- Detailed error logging for debugging
- Ability to retry failed operations
- Session state preservation during errors

## Development Notes

### Adding New Pages
1. Create new file in `pages/` directory
2. Implement `show_page()` function with `@error_boundary`
3. Add route in `app_multipage.py`
4. Update sidebar navigation in `libs/ui_layout.py`

### Customizing UI Components
- Modify `libs/ui_layout.py` for shared functionality
- Use existing error handling patterns
- Follow session state naming conventions

### Dependencies
- Core dependencies remain unchanged
- No new packages required for multipage functionality
- Streamlit multipage features used natively

## Migration Benefits

1. **Improved UX:** Clear workflow with progress tracking
2. **Better Organization:** Logical separation of concerns
3. **Enhanced Editing:** Rich data_editor interfaces for all content
4. **Robust Error Handling:** Comprehensive validation and recovery
5. **Maintainable Code:** Modular structure with shared components
6. **Preserved Legacy:** Original applications remain functional

## Troubleshooting

### Common Issues
- **"Missing prerequisites":** Ensure previous steps completed
- **"Charter file not found":** Check `data/charters/` directory
- **Analysis failures:** Verify core v2 modules are working

### Debug Mode
Set `st.set_option('client.showErrorDetails', True)` for detailed error information.

### Session Reset
Use the "Start Over" functionality or clear browser session to reset state.

---

*Last updated: 2025-06-08 - Multipage UI refactor completion*