#!/usr/bin/env python3
"""
Filter prompts catalog to extract only actual LLM prompt candidates
used in core functionality (excluding archive, tests, scripts).
"""

import csv
import re
from pathlib import Path
from typing import List, Dict


def load_prompts_catalog(catalog_path: Path) -> List[Dict[str, str]]:
    """Load the prompts catalog CSV file."""
    prompts = []
    
    try:
        with open(catalog_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                prompts.append(row)
    except Exception as e:
        print(f"Error loading catalog: {e}")
        return []
    
    return prompts


def apply_step1_filter(prompts: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    Step-1 Filter:
    - Exclude rows with filepath containing /archive/, /tests/, /scripts/
    - Exclude rows where symbol doesn't contain 'prompt' or 'system_prompt' (case insensitive)
    """
    filtered = []
    excluded_paths = ['/archive/', '/tests/', '/scripts/']
    
    for prompt in prompts:
        filepath = prompt.get('filepath', '')
        symbol = prompt.get('symbol', '')
        
        # Check if filepath contains excluded directories
        if any(excluded_path in filepath for excluded_path in excluded_paths):
            continue
        
        # Check if symbol contains 'prompt' or 'system_prompt' (case insensitive)
        symbol_lower = symbol.lower()
        if 'prompt' not in symbol_lower and 'system_prompt' not in symbol_lower:
            continue
        
        filtered.append(prompt)
    
    return filtered


def apply_step2_filter(prompts: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    Step-2 Filter (Optional):
    - Include only rows with filepath containing core/ or libs/
    """
    filtered = []
    included_paths = ['core/', 'libs/']
    
    for prompt in prompts:
        filepath = prompt.get('filepath', '')
        
        # Check if filepath contains included directories
        if any(included_path in filepath for included_path in included_paths):
            filtered.append(prompt)
    
    return filtered


def save_filtered_catalog(prompts: List[Dict[str, str]], output_path: Path):
    """Save filtered catalog to CSV with original headers."""
    try:
        with open(output_path, 'w', encoding='utf-8', newline='') as f:
            if prompts:
                fieldnames = ['filepath', 'line_no', 'symbol', 'preview']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(prompts)
    except Exception as e:
        print(f"Error saving filtered catalog: {e}")


def self_check(prompts: List[Dict[str, str]], output_path: Path) -> bool:
    """
    Self-check:
    - Filtered rows should be < 200
    - CSV header should be correct
    """
    # Check row count
    if len(prompts) >= 200:
        print(f"⚠️  Warning: Filtered prompts count ({len(prompts)}) exceeds 200 rows")
        return False
    
    # Check if output file exists and has correct header
    if not output_path.exists():
        print("❌ Self-check: NG - Output file not found")
        return False
    
    try:
        with open(output_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader)
            expected_header = ['filepath', 'line_no', 'symbol', 'preview']
            if header != expected_header:
                print(f"❌ Self-check: NG - Header mismatch. Expected: {expected_header}, Got: {header}")
                return False
    except Exception as e:
        print(f"❌ Self-check: NG - Error reading output file: {e}")
        return False
    
    print("✅ Self-check: OK")
    return True


def main():
    """Main filtering logic."""
    # Get current directory (scripts/)
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent
    
    input_path = repo_root / "prompts_catalog.csv"
    output_path = repo_root / "prompts_catalog_filtered.csv"
    
    # Load prompts catalog
    print("Loading prompts catalog...")
    prompts = load_prompts_catalog(input_path)
    print(f"Loaded {len(prompts)} total prompts")
    
    if not prompts:
        print("❌ No prompts loaded, exiting")
        return False
    
    # Apply Step-1 filter
    print("Applying Step-1 filter...")
    step1_prompts = apply_step1_filter(prompts)
    print(f"After Step-1: {len(step1_prompts)} prompts")
    
    # Apply Step-2 filter (optional)
    print("Applying Step-2 filter...")
    step2_prompts = apply_step2_filter(step1_prompts)
    print(f"After Step-2: {len(step2_prompts)} prompts")
    
    # Use Step-2 results
    final_prompts = step2_prompts
    
    # Save filtered catalog
    print("Saving filtered catalog...")
    save_filtered_catalog(final_prompts, output_path)
    
    # Output final count
    print(f"Filtered prompts: {len(final_prompts)} rows")
    
    # Self-check
    success = self_check(final_prompts, output_path)
    
    return success


if __name__ == "__main__":
    success = main()
    if not success:
        exit(1)