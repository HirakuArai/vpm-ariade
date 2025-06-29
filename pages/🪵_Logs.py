"""
🪵 Logs Page - Kai VPM LLM Call Log Viewer

Streamlit page for viewing and analyzing LLM call logs with
interactive HTML display and detailed JSON viewer.
"""

import streamlit as st
import subprocess
import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
import tempfile

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.log_schema import LogEntry, RequestKind, from_jsonl


def load_all_logs(log_dir: Path, since_hours: int) -> list[LogEntry]:
    """Load log entries from log directory"""
    entries = []
    # Use timezone-aware cutoff time to match log entries (UTC)
    from datetime import timezone
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=since_hours)
    
    if not log_dir.exists():
        return entries
    
    # Find all JSONL files
    for log_file in sorted(log_dir.glob("*.jsonl")):
        file_entries = from_jsonl(log_file)
        
        # Filter by timestamp
        for entry in file_entries:
            try:
                entry_time = datetime.fromisoformat(entry.ts.replace('Z', '+00:00'))
                if entry_time >= cutoff_time:
                    entries.append(entry)
            except (ValueError, AttributeError):
                entries.append(entry)
    
    return sorted(entries, key=lambda e: e.ts, reverse=True)


def run_summarize_script(since_hours: int) -> str:
    """Run the summarize_logs.py script and capture output"""
    script_path = Path(__file__).parent.parent / "scripts" / "summarize_logs.py"
    
    if not script_path.exists():
        # Try archive location
        script_path = Path(__file__).parent.parent / "archive" / "scripts" / "summarize_logs.py"
    
    if not script_path.exists():
        return "<p>Error: summarize_logs.py script not found</p>"
    
    try:
        # Run the script
        result = subprocess.run(
            [sys.executable, str(script_path), "--since", str(since_hours)],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        return f"<p>Error running summarize script: {e.stderr}</p>"
    except Exception as e:
        return f"<p>Error: {str(e)}</p>"


def format_json_for_display(obj: dict) -> str:
    """Format JSON object for pretty display"""
    return json.dumps(obj, indent=2, ensure_ascii=False, default=str)


def main():
    st.set_page_config(
        page_title="LLM Call Logs - Kai VPM",
        page_icon="🪵",
        layout="wide"
    )
    
    st.title("🪵 LLM Call Logs")
    st.markdown("View and analyze LLM API calls made by Kai VPM")
    
    # Sidebar controls
    with st.sidebar:
        st.header("Log Filters")
        
        since_hours = st.slider(
            "Hours to look back",
            min_value=1,
            max_value=168,  # 1 week
            value=24,
            step=1,
            help="Show logs from the last N hours"
        )
        
        show_details = st.checkbox(
            "Show detailed JSON viewer",
            value=True,
            help="Display expandable JSON for each log entry"
        )
        
        auto_refresh = st.checkbox(
            "Auto-refresh",
            value=False,
            help="Automatically refresh the page every 30 seconds"
        )
        
        if auto_refresh:
            st.markdown("*Auto-refreshing every 30 seconds*")
            st.empty()  # Placeholder for refresh logic
    
    # Main content area
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.header("Summary Report")
        
        # Generate and display HTML summary
        with st.spinner("Generating summary..."):
            html_content = run_summarize_script(since_hours)
        
        # Display HTML in an iframe-like component
        st.components.v1.html(html_content, height=600, scrolling=True)
    
    with col2:
        st.header("Quick Stats")
        
        # Load logs for additional stats
        log_dir = Path("logs/llm_calls")
        entries = load_all_logs(log_dir, since_hours)
        
        # Display quick stats
        st.metric("Total Calls", len(entries))
        
        if entries:
            # Calculate token totals
            total_prompt_tokens = sum(e.prompt_tokens for e in entries)
            total_completion_tokens = sum(e.completion_tokens for e in entries)
            
            st.metric("Total Tokens", f"{total_prompt_tokens + total_completion_tokens:,}")
            st.metric("Prompt/Completion", f"{total_prompt_tokens:,} / {total_completion_tokens:,}")
            
            # Error rate
            error_count = sum(1 for e in entries if e.error)
            error_rate = (error_count / len(entries)) * 100 if entries else 0
            
            st.metric("Error Rate", f"{error_rate:.1f}%", 
                     delta=f"{error_count} errors",
                     delta_color="inverse" if error_count > 0 else "off")
            
            # Most recent call
            st.markdown("### Most Recent Call")
            latest = entries[0]
            st.text(f"Time: {latest.ts}")
            st.text(f"Agent: {latest.agent}")
            st.text(f"Kind: {latest.kind}")
            st.text(f"Tokens: {latest.prompt_tokens}/{latest.completion_tokens}")
    
    # Detailed JSON viewer
    if show_details and entries:
        st.header("Detailed Log Entries")
        st.markdown(f"*Showing {len(entries)} entries from the last {since_hours} hours*")
        
        # Search/filter controls
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            filter_agent = st.selectbox(
                "Filter by Agent",
                options=["All", "kai", "claude"],
                index=0
            )
        
        with col2:
            filter_kind = st.selectbox(
                "Filter by Kind",
                options=["All"] + [k.value for k in RequestKind],
                index=0
            )
        
        with col3:
            filter_error = st.selectbox(
                "Filter by Status",
                options=["All", "Success", "Error"],
                index=0
            )
        
        with col4:
            search_text = st.text_input(
                "Search in prompts",
                placeholder="Enter search text..."
            )
        
        # Apply filters
        filtered_entries = entries
        
        if filter_agent != "All":
            filtered_entries = [e for e in filtered_entries if e.agent == filter_agent]
        
        if filter_kind != "All":
            filtered_entries = [e for e in filtered_entries if e.kind == filter_kind]
        
        if filter_error == "Success":
            filtered_entries = [e for e in filtered_entries if not e.error]
        elif filter_error == "Error":
            filtered_entries = [e for e in filtered_entries if e.error]
        
        if search_text:
            search_lower = search_text.lower()
            filtered_entries = [
                e for e in filtered_entries 
                if search_lower in json.dumps(e.request).lower()
            ]
        
        st.markdown(f"*Displaying {len(filtered_entries)} filtered entries*")
        
        # Display entries with expanders
        for i, entry in enumerate(filtered_entries[:50]):  # Limit to 50 for performance
            # Create summary title
            error_indicator = "❌ " if entry.error else "✅ "
            
            # Extract first user message for preview
            preview_text = "No user message"
            if entry.request and 'messages' in entry.request:
                for msg in entry.request.get('messages', []):
                    if msg.get('role') == 'user':
                        preview_text = msg.get('content', 'Empty content')[:100]
                        if len(msg.get('content', '')) > 100:
                            preview_text += "..."
                        break
            
            title = (
                f"{error_indicator}{entry.agent} • {entry.kind} • "
                f"{entry.prompt_tokens}/{entry.completion_tokens} tokens"
            )
            
            with st.expander(title):
                # Entry metadata
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown(f"**Timestamp:** {entry.ts}")
                    st.markdown(f"**Task ID:** `{entry.task_id}`")
                    st.markdown(f"**Model:** {entry.model}")
                
                with col2:
                    st.markdown(f"**Agent:** {entry.agent}")
                    st.markdown(f"**Kind:** {entry.kind}")
                    if entry.error:
                        st.markdown(f"**Error:** :red[{entry.error}]")
                
                # Preview text
                st.markdown("**Preview:**")
                st.text(preview_text)
                
                # Full JSON display
                st.markdown("**Full Log Entry:**")
                
                # Create tabs for request/response
                tab1, tab2, tab3 = st.tabs(["Request", "Response", "Full Entry"])
                
                with tab1:
                    st.json(entry.request)
                
                with tab2:
                    if entry.response:
                        st.json(entry.response)
                    else:
                        st.markdown("*No response (error occurred)*")
                
                with tab3:
                    st.json(entry.model_dump())
    
    # Auto-refresh logic
    if auto_refresh:
        import time
        time.sleep(30)
        st.rerun()


if __name__ == "__main__":
    main()