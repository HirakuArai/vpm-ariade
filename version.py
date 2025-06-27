# -*- coding: utf-8 -*-
"""
Version Management for Kai VPM
アプリケーションバージョン管理
"""

__version__ = "2.2.2"
__version_name__ = "AI-First Era"
__build_date__ = "2025-06-28"

def get_version_info():
    """バージョン情報を取得"""
    return {
        "version": __version__,
        "name": __version_name__,
        "build_date": __build_date__,
        "display": f"v{__version__}"
    }