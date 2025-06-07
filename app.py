"""
Kai VPM v2 - Main Landing Page
AI Project Manager with Charter-driven Workflow
"""

import streamlit as st

# Set page config as the very first Streamlit command
st.set_page_config(
    page_title="Kai VPM v2 - AI Project Manager",
    page_icon="🌟",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Main landing page content
st.title("🌟 Kai VPM v2")
st.markdown("## AI Project Manager")

st.markdown("""
Welcome to **Kai VPM v2** - an intelligent project management system that transforms 
your ideas into structured, actionable project plans.

### 🚀 Getting Started

Use the sidebar to navigate through the project workflow:

1. **📝 New Project** - Create a project charter through guided questions
2. **✏️ Preview Charter** - Review and edit your charter details  
3. **🧠 Analysis & WBS** - AI-powered analysis and work breakdown structure

### ✨ Key Features

- **Charter-Driven Approach**: Every project starts with a clear charter
- **AI Persona Analysis**: Intelligent prioritization and risk assessment
- **Work Breakdown Structure**: Automated task generation with dependencies
- **Interactive Editing**: Rich data editors for all project components
- **Export & Save**: Complete project data export for external use

### 🔄 Workflow Overview

```
Charter Creation → Review & Edit → AI Analysis → WBS Generation → Export
```

### 🎯 Benefits

- **Structured Planning**: Ensures all projects have clear scope and objectives
- **Risk Awareness**: AI identifies potential issues early in the process
- **Task Organization**: Generates realistic timelines with proper dependencies
- **Collaborative**: Easy review and editing of all project components

---

**Ready to start?** Select a page from the sidebar menu to begin your project journey!
""")

# Show system status
with st.expander("🔧 System Status", expanded=False):
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Core Modules", "✅ Active")
        st.caption("persona_core, planning_core")
    
    with col2:
        st.metric("Data Storage", "✅ Ready")
        st.caption("charters/, results/")
    
    with col3:
        st.metric("UI Framework", "✅ Multipage")
        st.caption("Native Streamlit routing")

# Footer
st.markdown("---")
st.markdown("*Kai VPM v2 - Idempotent, Self-evolving AI Project Manager*")