# --- core/reanalysis_ui.py ---
"""
Reanalysis UI Components - 再分析UI コンポーネント
会話再分析機能のStreamlitインターフェース
"""

import streamlit as st
import logging
from datetime import datetime
from typing import Optional

from .conversation_reanalyzer import create_reanalyzer

logger = logging.getLogger(__name__)

class ReanalysisUI:
    """再分析機能のUIコンポーネント"""
    
    def __init__(self):
        self.reanalyzer = create_reanalyzer()
    
    def render_reanalysis_interface(self, project_id: str):
        """再分析インターフェースの描画"""
        st.markdown("### 🔄 会話再分析機能")
        st.info("💡 Phase 2-4実装前の過去会話を再分析して、プロジェクト情報を更新できます")
        
        # 利用可能な日付の取得
        available_dates = self.reanalyzer.get_available_dates(project_id)
        
        if not available_dates:
            st.warning("⚠️ このプロジェクトには再分析可能な会話ログがありません")
            
            # 会話ログ移行機能の提供
            st.markdown("#### 📂 会話ログ移行")
            st.info("全体会話ログからプロジェクト固有ログを生成できます")
            
            if st.button("🔄 会話ログを移行", type="primary"):
                self._execute_conversation_migration(project_id)
            
            return
        
        # タブで機能を分離
        tab1, tab2, tab3 = st.tabs(["📅 日付指定再分析", "📊 一括再分析", "📋 再分析履歴"])
        
        with tab1:
            self._render_single_date_reanalysis(project_id, available_dates)
        
        with tab2:
            self._render_batch_reanalysis(project_id, available_dates)
        
        with tab3:
            self._render_reanalysis_history(project_id)
    
    def _render_single_date_reanalysis(self, project_id: str, available_dates: list):
        """単一日付の再分析UI"""
        st.markdown("#### 📅 特定日付の再分析")
        
        # 日付選択
        date_options = {}
        for date_str in available_dates:
            # YYYYMMDD -> YYYY年MM月DD日 形式に変換
            try:
                dt = datetime.strptime(date_str, "%Y%m%d")
                formatted_date = dt.strftime("%Y年%m月%d日")
                date_options[f"{formatted_date} ({date_str})"] = date_str
            except ValueError:
                date_options[date_str] = date_str
        
        if not date_options:
            st.warning("再分析可能な日付がありません")
            return
        
        selected_display = st.selectbox(
            "再分析する日付を選択してください",
            options=list(date_options.keys()),
            help="Phase 2-4実装前の会話ログを選択して再分析できます"
        )
        
        selected_date = date_options[selected_display]
        
        # 選択した日付の会話プレビュー
        if st.checkbox("📋 会話内容をプレビュー"):
            self._show_conversation_preview(project_id, selected_date)
        
        # 実行オプション
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔍 ドライラン実行", help="実際の更新は行わず、分析結果のみ確認"):
                self._execute_reanalysis(project_id, selected_date, dry_run=True)
        
        with col2:
            if st.button("▶️ 再分析実行", type="primary", help="実際にプロジェクト情報を更新"):
                # 確認ダイアログ
                if st.session_state.get("confirm_reanalysis", False):
                    self._execute_reanalysis(project_id, selected_date, dry_run=False)
                    st.session_state["confirm_reanalysis"] = False
                else:
                    st.session_state["confirm_reanalysis"] = True
                    st.warning("⚠️ プロジェクト情報が更新されます。もう一度クリックして実行してください。")
    
    def _render_batch_reanalysis(self, project_id: str, available_dates: list):
        """一括再分析UI"""
        st.markdown("#### 📊 複数日付の一括再分析")
        
        if len(available_dates) <= 1:
            st.info("一括再分析には2日以上の会話ログが必要です")
            return
        
        # 日付範囲選択
        st.write("**再分析する日付範囲を選択:**")
        
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.selectbox("開始日", available_dates, index=len(available_dates)-1)
        with col2:
            end_date = st.selectbox("終了日", available_dates, index=0)
        
        # 範囲内の日付をフィルタ
        if start_date and end_date:
            range_dates = [d for d in available_dates if start_date <= d <= end_date]
            st.info(f"📅 {len(range_dates)}日分の会話ログが対象です: {', '.join(range_dates)}")
            
            if st.button("🔄 一括再分析実行", type="primary"):
                if len(range_dates) > 0:
                    self._execute_batch_reanalysis(project_id, (start_date, end_date))
                else:
                    st.error("❌ 有効な日付範囲を選択してください")
    
    def _render_reanalysis_history(self, project_id: str):
        """再分析履歴の表示"""
        st.markdown("#### 📋 再分析履歴")
        
        history = self.reanalyzer.get_reanalysis_history(project_id)
        
        if not history:
            st.info("まだ再分析履歴がありません")
            return
        
        # 履歴テーブル
        st.write("**これまでの再分析実行履歴:**")
        
        for i, entry in enumerate(reversed(history)):  # 新しい順
            with st.expander(f"📅 {entry['date_analyzed']} - {entry['updated_fields']}件更新", expanded=False):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**分析対象日**: {entry['date_analyzed']}")
                    st.write(f"**更新フィールド数**: {entry['updated_fields']}")
                
                with col2:
                    st.write(f"**実行日時**: {entry['reanalyzed_at']}")
                    st.write(f"**分析エンジン**: {entry['analyzer_version']}")
    
    def _show_conversation_preview(self, project_id: str, date_str: str):
        """会話内容のプレビュー表示"""
        try:
            messages = self.reanalyzer.load_conversation_by_date(project_id, date_str)
            
            if not messages:
                st.warning("会話ログが見つかりません")
                return
            
            st.markdown(f"**{date_str} の会話内容 ({len(messages)}件)**")
            
            # 最初の数件のみ表示
            preview_count = min(6, len(messages))
            
            for i, msg in enumerate(messages[:preview_count]):
                role = "👤 ユーザー" if msg["role"] == "user" else "🤖 AI"
                content = msg["content"][:100] + "..." if len(msg["content"]) > 100 else msg["content"]
                
                st.markdown(f"**{role}**: {content}")
            
            if len(messages) > preview_count:
                st.caption(f"（{len(messages)}件中、最初の{preview_count}件を表示）")
        
        except Exception as e:
            st.error(f"プレビュー表示エラー: {e}")
    
    def _execute_reanalysis(self, project_id: str, date_str: str, dry_run: bool = False):
        """再分析の実行"""
        try:
            with st.spinner(f"{'ドライラン' if dry_run else '再分析'}実行中..."):
                result = self.reanalyzer.reanalyze_conversation(project_id, date_str, dry_run=dry_run)
            
            if result["success"]:
                if dry_run:
                    st.success(f"✅ ドライラン完了: {date_str}")
                    st.info(f"📊 分析対象メッセージ数: {result.get('analyzed_messages', 0)}")
                else:
                    st.success(f"✅ 再分析完了: {date_str}")
                    st.info(f"📈 更新されたフィールド数: {result['updated_fields']}")
                    st.info(f"📊 分析対象メッセージ数: {result.get('analyzed_messages', 0)}")
                
                # 抽出された情報の表示
                if result.get("extracted_info"):
                    with st.expander("🔍 抽出された情報", expanded=True):
                        st.markdown("### 抽出結果")
                        for info in result["extracted_info"]:
                            col1, col2, col3 = st.columns([2, 1, 1])
                            with col1:
                                st.write(f"**フィールド**: {info['field_name']}")
                                st.write(f"**値**: {info['value']}")
                            with col2:
                                st.write(f"**信頼度**: {info['confidence']:.1%}")
                            with col3:
                                st.write(f"**方法**: {info['extraction_method']}")
                            if info.get('original_text'):
                                st.caption(f"📑 元テキスト: {info['original_text']}")
                            st.divider()
                    
                    if result["conflicts"]:
                        st.warning(f"⚠️ {len(result['conflicts'])}件の競合が検出されました")
                        with st.expander("🔄 競合詳細", expanded=False):
                            for conflict in result["conflicts"]:
                                st.write(f"**フィールド**: {conflict.field_name}")
                                st.write(f"- 既存値: {conflict.existing_value} (信頼度: {conflict.confidence_existing:.1%})")
                                st.write(f"- 新しい値: {conflict.new_value} (信頼度: {conflict.confidence_new:.1%})")
                                st.write(f"- 競合タイプ: {conflict.conflict_type}")
                                st.divider()
                    
                    # 更新後は画面をリフレッシュ
                    if not dry_run and result['updated_fields'] > 0:
                        st.balloons()
                        st.info("🔄 ページを更新しています...")
                        st.rerun()
                else:
                    st.info("📄 抽出された情報はありませんでした")
            else:
                st.error(f"❌ {'ドライラン' if dry_run else '再分析'}に失敗: {result['message']}")
        
        except Exception as e:
            st.error(f"❌ 実行中にエラーが発生しました: {e}")
    
    def _execute_batch_reanalysis(self, project_id: str, date_range: tuple):
        """一括再分析の実行"""
        try:
            with st.spinner("一括再分析実行中..."):
                result = self.reanalyzer.batch_reanalyze_project(project_id, date_range)
            
            if result["success"]:
                st.success(f"✅ 一括再分析完了")
                st.info(f"📈 総更新フィールド数: {result['total_updated_fields']}")
                
                # 日別結果の表示
                success_count = sum(1 for r in result["results"] if r["result"]["success"])
                st.info(f"📊 {success_count}/{len(result['results'])} 日の再分析が成功しました")
                
                # 詳細結果
                with st.expander("📋 詳細結果", expanded=False):
                    for item in result["results"]:
                        date = item["date"]
                        res = item["result"]
                        status = "✅" if res["success"] else "❌"
                        updated = res.get("updated_fields", 0)
                        st.write(f"{status} {date}: {updated}件更新")
                
                if result['total_updated_fields'] > 0:
                    st.balloons()
                    st.info("🔄 ページを更新しています...")
                    st.rerun()
            else:
                st.error(f"❌ 一括再分析に失敗: {result['message']}")
        
        except Exception as e:
            st.error(f"❌ 一括再分析中にエラーが発生しました: {e}")
    
    def _execute_conversation_migration(self, project_id: str):
        """会話ログ移行の実行"""
        try:
            from core.conversation_migrator import create_migrator
            
            with st.spinner("会話ログを移行中..."):
                migrator = create_migrator()
                result = migrator.migrate_conversations_for_project(project_id)
            
            if result["success"]:
                migrated_dates = result.get("migrated_dates", [])
                st.success(f"✅ 移行完了: {len(migrated_dates)}日分の会話ログを移行しました")
                
                if migrated_dates:
                    st.info(f"📅 移行された日付: {', '.join(migrated_dates)}")
                    st.info("🔄 ページを更新して再分析機能をお試しください")
                    st.rerun()
                else:
                    st.warning("⚠️ このプロジェクト関連の会話ログが見つかりませんでした")
            else:
                st.error(f"❌ 移行に失敗: {result['message']}")
        
        except Exception as e:
            st.error(f"❌ 移行中にエラーが発生しました: {e}")

def render_reanalysis_interface(project_id: str):
    """再分析インターフェースの描画（関数版）"""
    ui = ReanalysisUI()
    ui.render_reanalysis_interface(project_id)