"""
Self-checker module for project snapshots and capability analysis
"""

from .scan_capabilities import main as scan_capabilities

# Import from the project_diff module
from ..project_diff import compare_snapshots, check_project_changes

__all__ = ['scan_capabilities', 'compare_snapshots', 'check_project_changes']