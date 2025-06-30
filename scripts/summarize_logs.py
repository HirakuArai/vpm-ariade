#!/usr/bin/env python3
"""
Log Summarization CLI for Kai VPM

Reads JSONL log files and generates HTML summary with statistics
and sample prompts grouped by request kind.
"""

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple
import json

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.log_schema import LogEntry, RequestKind, from_jsonl


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Summarize Kai VPM LLM call logs"
    )
    parser.add_argument(
        "--since",
        type=int,
        default=24,
        help="Hours to look back (default: 24)"
    )
    parser.add_argument(
        "--log-dir",
        type=Path,
        default=Path("logs/llm_calls"),
        help="Log directory path (default: logs/llm_calls)"
    )
    return parser.parse_args()


def load_recent_logs(log_dir: Path, since_hours: int) -> List[LogEntry]:
    """Load log entries from recent log files"""
    entries = []
    # Use timezone-aware cutoff time to match log entries (UTC)
    from datetime import timezone
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=since_hours)
    
    if not log_dir.exists():
        return entries
    
    # Find all JSONL files in log directory, excluding metadata files
    metadata_files = {"dedup_skipped.jsonl", "metrics_anomalies.jsonl", "dedup_index.json"}
    
    for log_file in sorted(log_dir.glob("*.jsonl")):
        # Skip metadata files that don't contain LogEntry format
        if log_file.name in metadata_files:
            continue
        # Skip if file is older than cutoff (based on filename)
        try:
            file_date_str = log_file.stem.split("-")[0]  # YYYYMMDD part
            file_date = datetime.strptime(file_date_str, "%Y%m%d")
            
            # Add one day to account for entries throughout the day
            # Make file_date timezone-aware for comparison
            file_date_tz = file_date.replace(tzinfo=timezone.utc)
            if file_date_tz + timedelta(days=1) < cutoff_time.replace(hour=0, minute=0, second=0, microsecond=0):
                continue
        except (ValueError, IndexError):
            # If we can't parse the date, include the file
            pass
        
        # Load entries from this file
        file_entries = from_jsonl(log_file)
        
        # Filter by timestamp
        for entry in file_entries:
            try:
                entry_time = datetime.fromisoformat(entry.ts.replace('Z', '+00:00'))
                if entry_time >= cutoff_time:
                    entries.append(entry)
            except (ValueError, AttributeError):
                # Include entries with unparseable timestamps
                entries.append(entry)
    
    return sorted(entries, key=lambda e: e.ts)


def summarize_by_kind(entries: List[LogEntry]) -> Dict[str, Dict]:
    """Summarize log entries grouped by request kind"""
    summary = defaultdict(lambda: {
        'total': 0,
        'success': 0,
        'errors': 0,
        'prompt_tokens': 0,
        'completion_tokens': 0,
        'error_types': defaultdict(int),
        'samples': []
    })
    
    for entry in entries:
        kind_summary = summary[entry.kind]
        kind_summary['total'] += 1
        
        if entry.error:
            kind_summary['errors'] += 1
            kind_summary['error_types'][entry.error] += 1
        else:
            kind_summary['success'] += 1
        
        kind_summary['prompt_tokens'] += entry.prompt_tokens
        kind_summary['completion_tokens'] += entry.completion_tokens
        
        # Collect samples (up to 3 per kind)
        if len(kind_summary['samples']) < 3:
            # Extract first user message as sample
            sample_text = "No user message"
            if entry.request and 'messages' in entry.request:
                for msg in entry.request['messages']:
                    if msg.get('role') == 'user':
                        sample_text = msg.get('content', 'Empty content')[:200]
                        if len(msg.get('content', '')) > 200:
                            sample_text += "..."
                        break
            
            # トークン警告フラグを追加
            high_token_warning = "⚠️ " if entry.prompt_tokens > 1000 else ""
            
            kind_summary['samples'].append({
                'ts': entry.ts,
                'task_id': entry.task_id,
                'agent': entry.agent,
                'text': sample_text,
                'tokens': f"{entry.prompt_tokens}/{entry.completion_tokens}",
                'warning': high_token_warning
            })
    
    return dict(summary)


def generate_html_report(
    summary: Dict[str, Dict], 
    since_hours: int,
    total_entries: int
) -> str:
    """Generate HTML report from summary data"""
    html_parts = []
    
    # HTML header
    html_parts.append("""<!DOCTYPE html>
<html>
<head>
    <title>Kai VPM LLM Call Summary</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            border-bottom: 2px solid #007bff;
            padding-bottom: 10px;
        }
        h2 {
            color: #555;
            margin-top: 30px;
        }
        .summary-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        .kind-card {
            border: 1px solid #ddd;
            border-radius: 6px;
            padding: 15px;
            background-color: #f8f9fa;
        }
        .kind-title {
            font-weight: bold;
            color: #007bff;
            margin-bottom: 10px;
            font-size: 1.1em;
        }
        .stats {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            margin-bottom: 15px;
        }
        .stat {
            font-size: 0.9em;
        }
        .stat-label {
            color: #666;
        }
        .stat-value {
            font-weight: bold;
            color: #333;
        }
        .success { color: #28a745; }
        .error { color: #dc3545; }
        .warning { color: #ff6b35; }
        .sample {
            background-color: white;
            border: 1px solid #e0e0e0;
            border-radius: 4px;
            padding: 10px;
            margin-bottom: 10px;
            font-size: 0.85em;
        }
        .sample-header {
            display: flex;
            justify-content: space-between;
            margin-bottom: 5px;
            color: #666;
            font-size: 0.9em;
        }
        .sample-text {
            color: #333;
            line-height: 1.4;
        }
        .error-list {
            margin-top: 10px;
            font-size: 0.85em;
            color: #dc3545;
        }
        .overview {
            background-color: #e7f3ff;
            border: 1px solid #b3d9ff;
            border-radius: 6px;
            padding: 15px;
            margin-bottom: 20px;
        }
        .overview-stat {
            display: inline-block;
            margin-right: 30px;
        }
    </style>
</head>
<body>
    <div class="container">
""")
    
    # Overview section
    total_tokens = sum(s['prompt_tokens'] + s['completion_tokens'] for s in summary.values())
    total_errors = sum(s['errors'] for s in summary.values())
    
    html_parts.append(f"""
        <h1>🪵 Kai VPM LLM Call Summary</h1>
        <div class="overview">
            <div class="overview-stat">
                <span class="stat-label">Period:</span>
                <span class="stat-value">Last {since_hours} hours</span>
            </div>
            <div class="overview-stat">
                <span class="stat-label">Total Calls:</span>
                <span class="stat-value">{total_entries}</span>
            </div>
            <div class="overview-stat">
                <span class="stat-label">Total Tokens:</span>
                <span class="stat-value">{total_tokens:,}</span>
            </div>
            <div class="overview-stat">
                <span class="stat-label">Errors:</span>
                <span class="stat-value error">{total_errors}</span>
            </div>
        </div>
""")
    
    # Summary by kind
    html_parts.append('<div class="summary-grid">')
    
    for kind, data in summary.items():
        success_rate = (data['success'] / data['total'] * 100) if data['total'] > 0 else 0
        
        html_parts.append(f"""
        <div class="kind-card">
            <div class="kind-title">{kind.upper().replace('_', ' ')}</div>
            <div class="stats">
                <div class="stat">
                    <span class="stat-label">Total Calls:</span>
                    <span class="stat-value">{data['total']}</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Success Rate:</span>
                    <span class="stat-value {'success' if success_rate > 90 else 'error'}">{success_rate:.1f}%</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Prompt Tokens:</span>
                    <span class="stat-value">{data['prompt_tokens']:,}</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Completion Tokens:</span>
                    <span class="stat-value">{data['completion_tokens']:,}</span>
                </div>
            </div>
""")
        
        # Error breakdown if any
        if data['error_types']:
            html_parts.append('<div class="error-list"><strong>Errors:</strong><br>')
            for error_type, count in data['error_types'].items():
                html_parts.append(f"{error_type}: {count}<br>")
            html_parts.append('</div>')
        
        # Sample prompts
        if data['samples']:
            html_parts.append('<div style="margin-top: 15px;"><strong>Sample Prompts:</strong></div>')
            for sample in data['samples']:
                html_parts.append(f"""
                <div class="sample">
                    <div class="sample-header">
                        <span>{sample.get('warning', '')}{sample['agent']} • {sample['ts']}</span>
                        <span>Tokens: {sample['tokens']}</span>
                    </div>
                    <div class="sample-text">{sample['text']}</div>
                </div>
""")
        
        html_parts.append('</div>')  # Close kind-card
    
    html_parts.append('</div>')  # Close summary-grid
    
    # HTML footer
    html_parts.append("""
    </div>
</body>
</html>
""")
    
    return ''.join(html_parts)


def main():
    """Main entry point"""
    args = parse_args()
    
    # Load recent logs
    entries = load_recent_logs(args.log_dir, args.since)
    
    if not entries:
        print(f"No log entries found in the last {args.since} hours", file=sys.stderr)
        # Still generate empty report
        summary = {}
    else:
        # Summarize by kind
        summary = summarize_by_kind(entries)
    
    # Generate HTML report
    html_report = generate_html_report(summary, args.since, len(entries))
    
    # Output to stdout
    print(html_report)


if __name__ == "__main__":
    main()