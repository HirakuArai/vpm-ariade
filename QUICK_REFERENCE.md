# 🚀 Quick Reference

## Current System State (2025-06-21)

### ✅ Working Entry Point
```bash
streamlit run app.py
```

### 🏗️ Architecture
- **Main UI**: `app.py` (integrated, single entry point)
- **Conversation Logs**: Dual system (global + project-specific)
- **Project Management**: Full lifecycle support with automation
- **Auto Updates**: Enhanced validation, safe operation

### 🔑 Key Features
1. **Project Creation**: Type "プロジェクト作成" in chat
2. **Task Addition**: `タスク <description> <YYYY-MM-DD>`
3. **Conversation History**: Automatic recording and display
4. **Phase Management**: Automated project lifecycle progression
5. **Progress Monitoring**: Real-time dashboard and alerts

### 📁 Important File Locations
```
app.py                                    # Main application
core/auto_update_engine.py               # Enhanced validation
docs/conversation_system.md              # System documentation
data/conversations/{project_id}/         # Project-specific logs
data/projects/{project_id}.json          # Project data
```

### 🛠️ Recent Fixes Applied
- ✅ AutoUpdateEngine validation (prevents invalid task generation)
- ✅ Conversation recording system (dual logging)
- ✅ app.py integration (single entry point)
- ✅ Data cleanup (removed 22 corrupted tasks)
- ✅ Repository organization (removed redundant files)

### 🔍 Troubleshooting
- **UI Issues**: Ensure `streamlit run app.py` (not pages/00_chat.py)
- **Conversation Lost**: Check `data/conversations/{project_id}/` for logs
- **Invalid Tasks**: AutoUpdateEngine now validates before creation
- **Git Issues**: 27 commits pushed to main, should be up-to-date

### 📞 System Health Check
```bash
git status                    # Should show "working tree clean"
streamlit run app.py         # Should launch UI successfully
```