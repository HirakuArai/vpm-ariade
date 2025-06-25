# --- core/navigation.py ---
"""
Hierarchical Navigation System - 階層ナビゲーション管理
サイドバーの階層ナビゲーションとページ状態管理
"""

from enum import Enum
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import streamlit as st
from pathlib import Path

from .project_prompt import get_available_project_ids

class PageType(Enum):
    """ページタイプの定義"""
    HOME = "home"
    PROJECT_INFO = "project_info"
    PROJECT_DETAILS = "project_details"
    PROJECT_CHAT = "project_chat"
    PHASE_PROGRESS = "phase_progress"
    CONVERSATION_HISTORY = "conversation_history"
    SCHEDULE_MANAGEMENT = "schedule_management"
    PROGRESS_DASHBOARD = "progress_dashboard"
    SYSTEM_MONITOR = "system_monitor"

@dataclass
class NavigationState:
    """ナビゲーション状態"""
    current_page: PageType
    selected_project_id: Optional[str] = None
    project_sub_page: Optional[str] = None

class HierarchicalNavigator:
    """階層ナビゲーション管理"""
    
    def __init__(self):
        """初期化"""
        self.page_config = {
            PageType.HOME: {
                "title": "🏠 ホーム",
                "description": "メイン会話ページ",
                "requires_project": False
            },
            PageType.PROJECT_INFO: {
                "title": "📋 プロジェクト情報",
                "description": "情報収集状況と詳細",
                "requires_project": True
            },
            PageType.PROJECT_DETAILS: {
                "title": "📄 プロジェクト詳細",
                "description": "プロジェクトの詳細ドキュメント",
                "requires_project": True
            },
            PageType.PROJECT_CHAT: {
                "title": "💬 プロジェクト会話",
                "description": "プロジェクトについて質問・相談",
                "requires_project": True
            },
            PageType.PHASE_PROGRESS: {
                "title": "📈 フェーズ進捗",
                "description": "プロジェクトフェーズ管理",
                "requires_project": True
            },
            PageType.CONVERSATION_HISTORY: {
                "title": "💬 会話履歴",
                "description": "プロジェクト会話ログ",
                "requires_project": True
            },
            PageType.SCHEDULE_MANAGEMENT: {
                "title": "📅 スケジュール管理",
                "description": "タスクとスケジュール",
                "requires_project": False
            },
            PageType.PROGRESS_DASHBOARD: {
                "title": "📊 進捗ダッシュボード",
                "description": "全体進捗とメトリクス",
                "requires_project": False
            },
            PageType.SYSTEM_MONITOR: {
                "title": "🖥️ システム監視",
                "description": "システム状態監視",
                "requires_project": False
            }
        }
    
    def initialize_session_state(self):
        """セッション状態の初期化"""
        if "navigation_state" not in st.session_state:
            st.session_state.navigation_state = NavigationState(
                current_page=PageType.HOME,
                selected_project_id=None,
                project_sub_page=None
            )
        
        # Backward compatibility
        if "current_project_id" not in st.session_state:
            st.session_state.current_project_id = None
    
    def render_sidebar_navigation(self) -> NavigationState:
        """サイドバーナビゲーションの描画"""
        self.initialize_session_state()
        
        with st.sidebar:
            st.title("🌟 Kai VPM")
            
            # メインナビゲーション
            st.subheader("📂 メインメニュー")
            
            # ホームページ
            if st.button("🏠 ホーム", use_container_width=True, 
                        type="primary" if st.session_state.navigation_state.current_page == PageType.HOME else "secondary"):
                st.session_state.navigation_state.current_page = PageType.HOME
                st.session_state.navigation_state.selected_project_id = None
            
            # グローバルページ（プロジェクト非依存）
            global_pages = [
                PageType.PROGRESS_DASHBOARD,
                PageType.SCHEDULE_MANAGEMENT,
                PageType.SYSTEM_MONITOR
            ]
            
            for page_type in global_pages:
                config = self.page_config[page_type]
                button_type = "primary" if st.session_state.navigation_state.current_page == page_type else "secondary"
                
                if st.button(config["title"], use_container_width=True, type=button_type):
                    st.session_state.navigation_state.current_page = page_type
                    st.session_state.navigation_state.selected_project_id = None
            
            st.divider()
            
            # プロジェクトリスト
            st.subheader("📁 プロジェクト")
            
            available_projects = get_available_project_ids()
            
            if not available_projects:
                st.info("💡 プロジェクトがありません\n\nメッセージ入力で「プロジェクト作成」と送信してください")
            else:
                # プロジェクト選択
                for project_id in available_projects:
                    project_data = self._get_project_summary(project_id)
                    project_name = project_data.get("name", project_id)
                    
                    # プロジェクト選択ボタン
                    is_selected = st.session_state.navigation_state.selected_project_id == project_id
                    button_style = "primary" if is_selected else "secondary"
                    
                    if st.button(f"📋 {project_name}", use_container_width=True, type=button_style):
                        st.session_state.navigation_state.selected_project_id = project_id
                        st.session_state.current_project_id = project_id  # Backward compatibility
                        
                        # デフォルトでプロジェクト情報ページを表示
                        st.session_state.navigation_state.current_page = PageType.PROJECT_INFO
                    
                    # プロジェクトが選択されている場合、サブメニューを表示
                    if is_selected:
                        st.markdown("  ")  # 少しスペース
                        
                        project_pages = [
                            PageType.PROJECT_INFO,
                            PageType.PROJECT_DETAILS,
                            PageType.PROJECT_CHAT,
                            PageType.PHASE_PROGRESS,
                            PageType.CONVERSATION_HISTORY
                        ]
                        
                        for page_type in project_pages:
                            config = self.page_config[page_type]
                            is_current_page = st.session_state.navigation_state.current_page == page_type
                            
                            # インデントされたサブメニューボタン
                            col1, col2 = st.columns([0.1, 0.9])
                            with col2:
                                button_type = "primary" if is_current_page else "secondary"
                                if st.button(config["title"], use_container_width=True, 
                                           type=button_type, key=f"sub_{page_type.value}_{project_id}"):
                                    st.session_state.navigation_state.current_page = page_type
        
        return st.session_state.navigation_state
    
    def _get_project_summary(self, project_id: str) -> Dict:
        """プロジェクト概要の取得"""
        try:
            import json
            project_path = Path(f"data/projects/{project_id}.json")
            if project_path.exists():
                data = json.loads(project_path.read_text(encoding="utf-8"))
                # Get display name with fallback to overview, then project_id
                display_name = data.get("display_name", "")
                overview = data.get("overview", "")
                name = display_name if display_name else (overview if overview else project_id)
                data["name"] = name
                return data
            return {"name": project_id}
        except Exception:
            return {"name": project_id}
    
    def get_current_page_config(self) -> Dict:
        """現在のページ設定を取得"""
        current_page = st.session_state.navigation_state.current_page
        return self.page_config.get(current_page, {})
    
    def validate_navigation_state(self) -> bool:
        """ナビゲーション状態の妥当性チェック"""
        current_page = st.session_state.navigation_state.current_page
        config = self.page_config.get(current_page, {})
        
        # プロジェクト依存ページでプロジェクトが選択されていない場合
        if config.get("requires_project", False):
            if not st.session_state.navigation_state.selected_project_id:
                # ホームページにリダイレクト
                st.session_state.navigation_state.current_page = PageType.HOME
                st.session_state.navigation_state.selected_project_id = None
                return False
        
        return True
    
    def render_page_header(self):
        """ページヘッダーの描画"""
        config = self.get_current_page_config()
        current_page = st.session_state.navigation_state.current_page
        
        if current_page == PageType.HOME:
            st.title("💬 Kai VPM - AI Project Manager")
            
            # 選択されたプロジェクトがある場合、プロジェクト情報を表示
            selected_project = st.session_state.navigation_state.selected_project_id
            if selected_project:
                project_data = self._get_project_summary(selected_project)
                project_name = project_data.get("name", selected_project)
                st.info(f"📋 **選択中プロジェクト**: {project_name}")
        else:
            # 他のページのヘッダー
            st.title(config.get("title", "ページ"))
            
            selected_project = st.session_state.navigation_state.selected_project_id
            if selected_project and config.get("requires_project", False):
                project_data = self._get_project_summary(selected_project)
                project_name = project_data.get("name", selected_project)
                st.caption(f"📋 プロジェクト: {project_name}")
            
            # ページ説明
            description = config.get("description")
            if description:
                st.caption(description)
    
    def get_navigation_breadcrumb(self) -> List[str]:
        """パンくずリストの生成"""
        breadcrumb = ["ホーム"]
        
        current_page = st.session_state.navigation_state.current_page
        selected_project = st.session_state.navigation_state.selected_project_id
        
        if selected_project:
            project_data = self._get_project_summary(selected_project)
            project_name = project_data.get("name", selected_project)
            breadcrumb.append(f"プロジェクト: {project_name}")
        
        if current_page != PageType.HOME:
            config = self.page_config.get(current_page, {})
            page_title = config.get("title", "ページ").split(" ", 1)[-1]  # アイコンを除去
            breadcrumb.append(page_title)
        
        return breadcrumb

# グローバルナビゲーターインスタンス
navigator = HierarchicalNavigator()