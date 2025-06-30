#!/usr/bin/env python3
"""
Prompt Linter for Kai VPM

JSON response validation tool that checks LLM call logs for:
1. Valid JSON parsing
2. Required field presence
3. Schema compliance
"""

import argparse
import sys
import json
import yaml
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional
from collections import defaultdict

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.log_schema import LogEntry, RequestKind, from_jsonl


# Required fields for AI response JSON
REQUIRED_FIELDS = {
    "intent", "action_type", "reasoning", "confidence", 
    "target_items", "response_content", "suggested_follow_ups"
}

VALID_INTENTS = {"project_management", "conversation", "clarification", "error"}
VALID_ACTION_TYPES = {
    "create_project", "create_task", "remove_task", "update_status", 
    "information_request", "general_discussion", "processing_error", "system_error"
}


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Lint Kai VPM LLM call logs for JSON response quality"
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
    parser.add_argument(
        "--format",
        choices=["yaml", "json"],
        default="yaml",
        help="Output format (default: yaml)"
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


def extract_json_from_response(response_text: str) -> Optional[Dict[str, Any]]:
    """Extract JSON from LLM response text"""
    if not response_text:
        return None
    
    # Try to find JSON block in markdown code fence
    lines = response_text.split('\n')
    json_lines = []
    in_json_block = False
    
    for line in lines:
        if line.strip() in ['```json', '```']:
            if in_json_block:
                break  # End of JSON block
            else:
                in_json_block = True  # Start of JSON block
                continue
        
        if in_json_block:
            json_lines.append(line)
    
    # If no markdown block found, try the entire response
    if not json_lines:
        json_text = response_text.strip()
    else:
        json_text = '\n'.join(json_lines).strip()
    
    # Try to parse JSON
    try:
        return json.loads(json_text)
    except json.JSONDecodeError:
        # Try to find JSON object in text
        start = json_text.find('{')
        end = json_text.rfind('}')
        
        if start != -1 and end != -1 and start < end:
            try:
                return json.loads(json_text[start:end+1])
            except json.JSONDecodeError:
                pass
        
        return None


def validate_json_structure(json_obj: Dict[str, Any]) -> List[str]:
    """Validate JSON structure against expected schema"""
    issues = []
    
    # Check required fields
    missing_fields = REQUIRED_FIELDS - set(json_obj.keys())
    if missing_fields:
        issues.append(f"Missing required fields: {', '.join(missing_fields)}")
    
    # Validate intent
    intent = json_obj.get("intent")
    if intent and intent not in VALID_INTENTS:
        issues.append(f"Invalid intent: '{intent}'. Expected one of: {', '.join(VALID_INTENTS)}")
    
    # Validate action_type
    action_type = json_obj.get("action_type")
    if action_type and action_type not in VALID_ACTION_TYPES:
        issues.append(f"Invalid action_type: '{action_type}'. Expected one of: {', '.join(VALID_ACTION_TYPES)}")
    
    # Validate confidence
    confidence = json_obj.get("confidence")
    if confidence is not None:
        try:
            conf_val = float(confidence)
            if not (0.0 <= conf_val <= 1.0):
                issues.append(f"Confidence out of range: {conf_val}. Expected 0.0-1.0")
        except (ValueError, TypeError):
            issues.append(f"Invalid confidence type: {type(confidence)}. Expected float")
    
    # Validate target_items
    target_items = json_obj.get("target_items")
    if target_items is not None and not isinstance(target_items, list):
        issues.append(f"target_items should be a list, got {type(target_items)}")
    
    # Validate suggested_follow_ups
    follow_ups = json_obj.get("suggested_follow_ups")
    if follow_ups is not None and not isinstance(follow_ups, list):
        issues.append(f"suggested_follow_ups should be a list, got {type(follow_ups)}")
    
    return issues


def lint_log_entries(entries: List[LogEntry]) -> Dict[str, Any]:
    """Lint log entries and return report"""
    report = {
        "summary": {
            "total_entries": len(entries),
            "successful_responses": 0,
            "json_parse_errors": 0,
            "schema_validation_errors": 0,
            "perfect_responses": 0
        },
        "issues": [],
        "error_breakdown": defaultdict(int),
        "samples": {
            "parse_errors": [],
            "validation_errors": [],
            "perfect_examples": []
        }
    }
    
    for entry in entries:
        # Skip entries with errors or no response
        if entry.error or not entry.response:
            continue
        
        # Extract response content
        response_content = ""
        if isinstance(entry.response, dict):
            # Look for response content in various possible locations
            choices = entry.response.get("choices", [])
            if choices and len(choices) > 0:
                message = choices[0].get("message", {})
                response_content = message.get("content", "")
        
        if not response_content:
            continue
        
        report["summary"]["successful_responses"] += 1
        
        # Try to parse JSON
        json_obj = extract_json_from_response(response_content)
        
        if json_obj is None:
            report["summary"]["json_parse_errors"] += 1
            report["error_breakdown"]["json_parse_error"] += 1
            
            # Sample parse error
            if len(report["samples"]["parse_errors"]) < 3:
                report["samples"]["parse_errors"].append({
                    "task_id": entry.task_id,
                    "timestamp": entry.ts,
                    "agent": entry.agent,
                    "response_preview": response_content[:200] + "..." if len(response_content) > 200 else response_content
                })
            continue
        
        # Validate JSON structure
        validation_issues = validate_json_structure(json_obj)
        
        if validation_issues:
            report["summary"]["schema_validation_errors"] += 1
            
            for issue in validation_issues:
                report["error_breakdown"][issue] += 1
                
                report["issues"].append({
                    "task_id": entry.task_id,
                    "timestamp": entry.ts,
                    "agent": entry.agent,
                    "issue": issue,
                    "json_preview": json.dumps(json_obj, ensure_ascii=False)[:200]
                })
            
            # Sample validation error
            if len(report["samples"]["validation_errors"]) < 3:
                report["samples"]["validation_errors"].append({
                    "task_id": entry.task_id,
                    "timestamp": entry.ts,
                    "agent": entry.agent,
                    "issues": validation_issues,
                    "json_obj": json_obj
                })
        else:
            report["summary"]["perfect_responses"] += 1
            
            # Sample perfect response
            if len(report["samples"]["perfect_examples"]) < 3:
                report["samples"]["perfect_examples"].append({
                    "task_id": entry.task_id,
                    "timestamp": entry.ts,
                    "agent": entry.agent,
                    "json_obj": json_obj
                })
    
    return report


def main():
    """Main entry point"""
    args = parse_args()
    
    # Load recent logs
    entries = load_recent_logs(args.log_dir, args.since)
    
    if not entries:
        report = {
            "summary": {"message": f"No log entries found in the last {args.since} hours"},
            "issues": [],
            "samples": {}
        }
    else:
        # Lint entries
        report = lint_log_entries(entries)
    
    # Add metadata
    report["metadata"] = {
        "generated_at": datetime.now().isoformat(),
        "period_hours": args.since,
        "log_directory": str(args.log_dir)
    }
    
    # Output report
    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:  # yaml
        print(yaml.dump(report, default_flow_style=False, allow_unicode=True))


if __name__ == "__main__":
    main()