#!/usr/bin/env python3
"""
Purge stale draft files from data/drafts/ directory
Usage: python scripts/purge_drafts.py --ttl 24h
"""

import argparse
import time
from pathlib import Path
from datetime import datetime, timedelta


def parse_ttl(ttl_str: str) -> int:
    """
    Parse TTL string like '24h', '7d', '2w' into hours
    
    Args:
        ttl_str: Time to live string (e.g., '24h', '7d', '2w')
        
    Returns:
        TTL in hours
    """
    if ttl_str.endswith('h'):
        return int(ttl_str[:-1])
    elif ttl_str.endswith('d'):
        return int(ttl_str[:-1]) * 24
    elif ttl_str.endswith('w'):
        return int(ttl_str[:-1]) * 24 * 7
    else:
        # Default to hours if no unit specified
        return int(ttl_str)


def purge_drafts(ttl_hours: int, dry_run: bool = False) -> int:
    """
    Purge draft files older than TTL
    
    Args:
        ttl_hours: Time to live in hours
        dry_run: If True, only show what would be deleted
        
    Returns:
        Number of files purged
    """
    drafts_dir = Path("data/drafts")
    
    if not drafts_dir.exists():
        print("No drafts directory found.")
        return 0
    
    cutoff_time = time.time() - (ttl_hours * 3600)
    purged_count = 0
    
    print(f"Purging drafts older than {ttl_hours} hours...")
    print(f"Cutoff time: {datetime.fromtimestamp(cutoff_time)}")
    
    for draft_file in drafts_dir.glob("draft_*.json"):
        try:
            file_mtime = draft_file.stat().st_mtime
            file_age_hours = (time.time() - file_mtime) / 3600
            
            if file_mtime < cutoff_time:
                if dry_run:
                    print(f"Would delete: {draft_file.name} (age: {file_age_hours:.1f}h)")
                else:
                    print(f"Deleting: {draft_file.name} (age: {file_age_hours:.1f}h)")
                    draft_file.unlink()
                purged_count += 1
            else:
                print(f"Keeping: {draft_file.name} (age: {file_age_hours:.1f}h)")
                
        except Exception as e:
            print(f"Error processing {draft_file}: {e}")
    
    return purged_count


def main():
    parser = argparse.ArgumentParser(description="Purge stale draft files")
    parser.add_argument(
        "--ttl", 
        default="24h", 
        help="Time to live (e.g., '24h', '7d', '2w')"
    )
    parser.add_argument(
        "--dry-run", 
        action="store_true",
        help="Show what would be deleted without actually deleting"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force deletion without confirmation"
    )
    
    args = parser.parse_args()
    
    ttl_hours = parse_ttl(args.ttl)
    
    print(f"Draft purge utility")
    print(f"TTL: {ttl_hours} hours")
    print(f"Dry run: {args.dry_run}")
    print("-" * 40)
    
    if not args.force and not args.dry_run:
        response = input("Continue with deletion? (y/N): ")
        if response.lower() != 'y':
            print("Aborted.")
            return
    
    purged_count = purge_drafts(ttl_hours, args.dry_run)
    
    if args.dry_run:
        print(f"\nWould purge {purged_count} draft files.")
    else:
        print(f"\nPurged {purged_count} draft files.")


if __name__ == "__main__":
    main()