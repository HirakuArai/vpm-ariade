#!/usr/bin/env python3
"""
Log Validation Script for AI Log Output Guidelines v1.0

Validates LLM call logs against the standard schema and common issues.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import List, Dict, Any
import jsonschema

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.log_schema import LogEntry, from_jsonl


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Validate Kai VPM LLM call logs against AI Log Output Guidelines v1.0"
    )
    parser.add_argument(
        "--log-dir",
        type=Path,
        default=Path("logs/llm_calls"),
        help="Log directory path (default: logs/llm_calls)"
    )
    parser.add_argument(
        "--schema",
        type=Path,
        default=Path("schemas/log_entry.schema.json"),
        help="JSON schema file path (default: schemas/log_entry.schema.json)"
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Enable strict validation (fail on any issue)"
    )
    parser.add_argument(
        "--output",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)"
    )
    return parser.parse_args()


def load_schema(schema_path: Path) -> Dict[str, Any]:
    """Load JSON schema"""
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_path}")
    
    with open(schema_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def validate_json_syntax(log_files: List[Path]) -> Dict[str, Any]:
    """Validate JSON syntax of log files"""
    results = {
        "passed": [],
        "failed": [],
        "total_files": len(log_files),
        "total_entries": 0,
        "syntax_errors": 0
    }
    
    for log_file in log_files:
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                line_num = 0
                file_entries = 0
                file_errors = []
                
                for line in f:
                    line_num += 1
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        json.loads(line)
                        file_entries += 1
                        results["total_entries"] += 1
                    except json.JSONDecodeError as e:
                        file_errors.append({
                            "line": line_num,
                            "error": str(e),
                            "content": line[:100] + "..." if len(line) > 100 else line
                        })
                        results["syntax_errors"] += 1
                
                if file_errors:
                    results["failed"].append({
                        "file": str(log_file),
                        "entries": file_entries,
                        "errors": file_errors
                    })
                else:
                    results["passed"].append({
                        "file": str(log_file),
                        "entries": file_entries
                    })
                    
        except Exception as e:
            results["failed"].append({
                "file": str(log_file),
                "entries": 0,
                "errors": [{"line": 0, "error": f"File error: {e}", "content": ""}]
            })
    
    return results


def validate_schema_compliance(log_files: List[Path], schema: Dict[str, Any]) -> Dict[str, Any]:
    """Validate log entries against JSON schema"""
    results = {
        "passed": 0,
        "failed": 0,
        "errors": [],
        "warnings": []
    }
    
    validator = jsonschema.Draft7Validator(schema)
    
    for log_file in log_files:
        try:
            entries = from_jsonl(log_file)
            for entry in entries:
                try:
                    # Convert LogEntry to dict for validation
                    entry_dict = entry.model_dump()
                    validator.validate(entry_dict)
                    results["passed"] += 1
                except jsonschema.ValidationError as e:
                    results["failed"] += 1
                    results["errors"].append({
                        "file": str(log_file),
                        "task_id": entry.task_id,
                        "error": e.message,
                        "path": list(e.absolute_path) if e.absolute_path else []
                    })
                except Exception as e:
                    results["failed"] += 1
                    results["errors"].append({
                        "file": str(log_file),
                        "task_id": getattr(entry, 'task_id', 'unknown'),
                        "error": f"Validation error: {e}",
                        "path": []
                    })
        except Exception as e:
            results["warnings"].append({
                "file": str(log_file),
                "message": f"Could not load entries: {e}"
            })
    
    return results


def check_common_issues(log_files: List[Path]) -> Dict[str, Any]:
    """Check for common issues mentioned in the guidelines"""
    results = {
        "code_fence_issues": 0,
        "comma_issues": 0,
        "null_case_issues": 0,
        "large_entries": 0,
        "total_checked": 0
    }
    
    for log_file in log_files:
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    results["total_checked"] += 1
                    
                    # Check for code fence artifacts
                    if "```json" in line or "```" in line:
                        results["code_fence_issues"] += 1
                    
                    # Check for Python-style None/True/False
                    if " None," in line or " True," in line or " False," in line:
                        results["null_case_issues"] += 1
                    
                    # Check for large entries (>32KB as per guidelines)
                    if len(line.encode('utf-8')) > 32 * 1024:
                        results["large_entries"] += 1
                    
                    # Basic comma check (simplified)
                    try:
                        parsed = json.loads(line)
                        # If it parses, commas are probably OK
                    except json.JSONDecodeError:
                        results["comma_issues"] += 1
                        
        except Exception:
            pass  # Skip files that can't be read
    
    return results


def main():
    """Main entry point"""
    args = parse_args()
    
    # Find log files
    if not args.log_dir.exists():
        print(f"Error: Log directory not found: {args.log_dir}", file=sys.stderr)
        sys.exit(1)
    
    log_files = list(args.log_dir.glob("*.jsonl"))
    if not log_files:
        print(f"Warning: No .jsonl files found in {args.log_dir}")
        sys.exit(0)
    
    # Load schema
    try:
        schema = load_schema(args.schema)
    except Exception as e:
        print(f"Error loading schema: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Run validations
    syntax_results = validate_json_syntax(log_files)
    schema_results = validate_schema_compliance(log_files, schema)
    issues_results = check_common_issues(log_files)
    
    # Generate report
    report = {
        "validation_summary": {
            "files_processed": len(log_files),
            "total_entries": syntax_results["total_entries"],
            "syntax_valid": len(syntax_results["passed"]),
            "syntax_errors": syntax_results["syntax_errors"],
            "schema_compliant": schema_results["passed"],
            "schema_violations": schema_results["failed"]
        },
        "syntax_validation": syntax_results,
        "schema_validation": schema_results,
        "common_issues": issues_results
    }
    
    # Output results
    if args.output == "json":
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        # Text output
        print("🪵 AI Log Output Guidelines v1.0 Validation Report")
        print("=" * 60)
        
        summary = report["validation_summary"]
        print(f"Files processed: {summary['files_processed']}")
        print(f"Total entries: {summary['total_entries']}")
        print(f"Syntax valid: {summary['syntax_valid']}/{len(log_files)} files")
        print(f"Schema compliant: {summary['schema_compliant']} entries")
        
        if summary["syntax_errors"] > 0:
            print(f"❌ Syntax errors: {summary['syntax_errors']}")
        
        if summary["schema_violations"] > 0:
            print(f"❌ Schema violations: {summary['schema_violations']}")
            
        # Common issues
        issues = report["common_issues"]
        if any(issues.values()):
            print("\n⚠️  Common Issues Detected:")
            if issues["code_fence_issues"] > 0:
                print(f"  - Code fence artifacts: {issues['code_fence_issues']} entries")
            if issues["null_case_issues"] > 0:
                print(f"  - Python None/True/False: {issues['null_case_issues']} entries")
            if issues["large_entries"] > 0:
                print(f"  - Large entries (>32KB): {issues['large_entries']} entries")
        
        # Detailed errors
        if schema_results["errors"] and len(schema_results["errors"]) <= 10:
            print("\n🔍 Schema Validation Errors:")
            for error in schema_results["errors"][:10]:
                print(f"  - Task {error['task_id']}: {error['error']}")
                if error['path']:
                    print(f"    Path: {'.'.join(map(str, error['path']))}")
    
    # Exit code
    if args.strict and (syntax_results["syntax_errors"] > 0 or schema_results["failed"] > 0):
        sys.exit(1)
    elif syntax_results["syntax_errors"] > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()