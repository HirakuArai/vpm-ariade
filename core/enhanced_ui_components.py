# -*- coding: utf-8 -*-
"""
Enhanced UI Components - 拡張インタラクティブUIコンポーネント
リアルタイム更新、フィードバック、アニメーション機能付き
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
import pandas as pd
import time
import json

class InteractiveComponents:
    """インタラクティブUIコンポーネント"""
    
    @staticmethod
    def render_typing_indicator():
        """タイピングインジケータ"""
        typing_placeholder = st.empty()
        
        def show_typing():
            dots = ["⚫", "⚫⚫", "⚫⚫⚫"]
            for i in range(3):
                typing_placeholder.markdown(f"🤖 AI が入力中 {dots[i % 3]}")
                time.sleep(0.5)
            typing_placeholder.empty()
        
        return show_typing
    
    @staticmethod
    def render_progress_animation(progress: float, label: str = "処理中"):
        """アニメーション付きプログレスバー"""
        progress_bar = st.progress(0, text=f"{label} 0%")
        
        # スムーズなアニメーション
        current = 0
        step = 2
        while current < progress:
            current = min(current + step, progress)
            progress_bar.progress(current / 100, text=f"{label} {current:.1f}%")
            time.sleep(0.05)
        
        return progress_bar
    
    @staticmethod
    def render_real_time_metrics(metrics: Dict[str, Any], update_interval: int = 5):
        """リアルタイム更新メトリクス"""
        container = st.empty()
        
        def update_metrics():
            with container.container():
                cols = st.columns(len(metrics))
                for i, (key, value) in enumerate(metrics.items()):
                    with cols[i]:
                        # メトリクスの種類に応じてフォーマット
                        if isinstance(value, (int, float)):
                            delta = value * 0.1 if value > 0 else None  # 仮の増減値
                            st.metric(key, f"{value:.2f}" if isinstance(value, float) else str(value), 
                                    delta=delta)
                        else:
                            st.metric(key, str(value))
        
        return update_metrics
    
    @staticmethod
    def render_interactive_chart(data: pd.DataFrame, chart_type: str = "line"):
        """インタラクティブチャート"""
        if chart_type == "line":
            fig = px.line(data, x=data.columns[0], y=data.columns[1], 
                         title="プロジェクト進捗推移")
        elif chart_type == "bar":
            fig = px.bar(data, x=data.columns[0], y=data.columns[1],
                        title="タスク完了状況")
        elif chart_type == "pie":
            fig = px.pie(data, values=data.columns[1], names=data.columns[0],
                        title="フェーズ分布")
        else:
            fig = go.Figure()
        
        fig.update_layout(
            height=400,
            showlegend=True,
            hovermode='x unified'
        )
        
        return st.plotly_chart(fig, use_container_width=True, key=f"chart_{chart_type}")

class FeedbackComponents:
    """ユーザーフィードバックコンポーネント"""
    
    @staticmethod
    def render_rating_widget(label: str, key: str) -> Optional[int]:
        """5段階評価ウィジェット"""
        st.markdown(f"**{label}**")
        
        # 星評価のHTML/CSS
        rating_html = """
        <style>
        .star-rating {
            display: flex;
            align-items: center;
            gap: 5px;
            margin: 10px 0;
        }
        .star {
            font-size: 30px;
            color: #ddd;
            cursor: pointer;
            transition: color 0.2s;
        }
        .star:hover,
        .star.active {
            color: #ffc107;
        }
        </style>
        <div class="star-rating" id="rating-{key}">
            <span class="star" data-rating="1">⭐</span>
            <span class="star" data-rating="2">⭐</span>
            <span class="star" data-rating="3">⭐</span>
            <span class="star" data-rating="4">⭐</span>
            <span class="star" data-rating="5">⭐</span>
        </div>
        """
        
        st.markdown(rating_html, unsafe_allow_html=True)
        
        # 簡易版としてsliderを使用
        rating = st.slider("", min_value=1, max_value=5, value=3, key=f"rating_{key}")
        
        return rating
    
    @staticmethod
    def render_feedback_form(context: str = "一般"):
        """フィードバックフォーム"""
        with st.expander("📝 フィードバックを送信", expanded=False):
            st.markdown(f"**{context}についてのフィードバック**")
            
            # 評価
            rating = FeedbackComponents.render_rating_widget("満足度", context)
            
            # コメント
            comment = st.text_area("コメント（任意）", placeholder="改善点やご要望をお聞かせください...")
            
            # カテゴリ
            category = st.selectbox("カテゴリ", [
                "使いやすさ", "機能", "パフォーマンス", "バグ報告", "要望", "その他"
            ])
            
            # 送信ボタン
            if st.button("📤 フィードバック送信", key=f"feedback_submit_{context}"):
                feedback_data = {
                    "context": context,
                    "rating": rating,
                    "comment": comment,
                    "category": category,
                    "timestamp": datetime.now().isoformat()
                }
                
                # フィードバックを保存（実装例）
                FeedbackComponents._save_feedback(feedback_data)
                st.success("フィードバックを送信しました。ありがとうございます！")
                st.balloons()
    
    @staticmethod
    def _save_feedback(feedback_data: Dict[str, Any]):
        """フィードバックデータの保存"""
        feedback_file = "data/feedback.jsonl"
        
        try:
            from pathlib import Path
            Path("data").mkdir(exist_ok=True)
            
            with open(feedback_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(feedback_data, ensure_ascii=False) + "\n")
        except Exception as e:
            st.error(f"フィードバック保存エラー: {e}")

class NotificationComponents:
    """通知・アラートコンポーネント"""
    
    @staticmethod
    def render_toast_notification(message: str, notification_type: str = "info", duration: int = 3):
        """トースト通知"""
        # Streamlitの制限により、一時的な表示のみ実装
        
        colors = {
            "success": "#d4edda",
            "info": "#d1ecf1", 
            "warning": "#fff3cd",
            "error": "#f8d7da"
        }
        
        icons = {
            "success": "✅",
            "info": "ℹ️",
            "warning": "⚠️", 
            "error": "❌"
        }
        
        color = colors.get(notification_type, colors["info"])
        icon = icons.get(notification_type, icons["info"])
        
        notification_placeholder = st.empty()
        
        # 通知表示
        notification_placeholder.markdown(f"""
        <div style="
            background-color: {color};
            padding: 1rem;
            border-radius: 8px;
            border-left: 4px solid #007bff;
            margin: 1rem 0;
            animation: slideIn 0.3s ease-in;
        ">
            {icon} {message}
        </div>
        """, unsafe_allow_html=True)
        
        # 指定時間後に削除
        if duration > 0:
            time.sleep(duration)
            notification_placeholder.empty()
    
    @staticmethod
    def render_system_status():
        """システム状態インジケータ"""
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            # AI接続状態
            ai_status = "🟢 正常" if st.session_state.get("ai_intent_detector") else "🔴 切断"
            st.metric("AI", ai_status)
        
        with col2:
            # 会話履歴数
            history_count = len(st.session_state.get("history", []))
            st.metric("セッション履歴", f"{history_count}件")
        
        with col3:
            # 現在時刻
            current_time = datetime.now().strftime("%H:%M")
            st.metric("現在時刻", current_time)
        
        with col4:
            # システム稼働時間（セッション開始からの時間）
            if "session_start" not in st.session_state:
                st.session_state["session_start"] = datetime.now()
            
            uptime = datetime.now() - st.session_state["session_start"]
            uptime_str = f"{uptime.seconds // 60}分"
            st.metric("セッション時間", uptime_str)

class ResponsiveLayout:
    """レスポンシブレイアウトコンポーネント"""
    
    @staticmethod
    def get_screen_size() -> str:
        """画面サイズの推定（簡易版）"""
        # Streamlitでは直接取得できないため、推定ロジック
        return "desktop"  # デフォルト
    
    @staticmethod
    def render_adaptive_columns(items: List[Any], max_cols: int = 3):
        """アダプティブカラムレイアウト"""
        screen_size = ResponsiveLayout.get_screen_size()
        
        # 画面サイズに応じてカラム数を調整
        if screen_size == "mobile":
            cols_count = 1
        elif screen_size == "tablet":
            cols_count = min(2, max_cols)
        else:
            cols_count = max_cols
        
        # アイテムをカラムに分散
        if items:
            cols = st.columns(cols_count)
            for i, item in enumerate(items):
                with cols[i % cols_count]:
                    if callable(item):
                        item()
                    else:
                        st.write(item)
    
    @staticmethod
    def render_mobile_friendly_form(fields: Dict[str, Any]):
        """モバイルフレンドリーフォーム"""
        for field_name, field_config in fields.items():
            field_type = field_config.get("type", "text")
            label = field_config.get("label", field_name)
            
            # フィールドタイプに応じた入力ウィジェット
            if field_type == "text":
                st.text_input(label, key=field_name)
            elif field_type == "textarea":
                st.text_area(label, key=field_name, height=100)
            elif field_type == "select":
                options = field_config.get("options", [])
                st.selectbox(label, options, key=field_name)
            elif field_type == "multiselect":
                options = field_config.get("options", [])
                st.multiselect(label, options, key=field_name)
            elif field_type == "date":
                st.date_input(label, key=field_name)
            elif field_type == "number":
                st.number_input(label, key=field_name)

class ContextualHelp:
    """コンテキストヘルプコンポーネント"""
    
    @staticmethod
    def render_help_tooltip(content: str, trigger_text: str = "?"):
        """ヘルプツールチップ"""
        with st.popover(trigger_text):
            st.markdown(content)
    
    @staticmethod
    def render_guided_tour(steps: List[Dict[str, str]]):
        """ガイドツアー"""
        if "tour_step" not in st.session_state:
            st.session_state["tour_step"] = 0
        
        if st.session_state["tour_step"] < len(steps):
            current_step = steps[st.session_state["tour_step"]]
            
            with st.container():
                st.info(f"**ステップ {st.session_state['tour_step'] + 1}/{len(steps)}**: {current_step['title']}")
                st.markdown(current_step["content"])
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("⏭️ 次へ") and st.session_state["tour_step"] < len(steps) - 1:
                        st.session_state["tour_step"] += 1
                        st.rerun()
                
                with col2:
                    if st.button("❌ ツアー終了"):
                        st.session_state["tour_step"] = len(steps)
                        st.rerun()
    
    @staticmethod
    def render_contextual_suggestions(context: str, suggestions: List[str]):
        """コンテキスト別提案"""
        if suggestions:
            with st.expander("💡 おすすめの操作", expanded=False):
                st.markdown(f"**{context}でよく使われる機能:**")
                for suggestion in suggestions:
                    if st.button(f"▶️ {suggestion}", key=f"suggest_{suggestion}"):
                        st.info(f"実行中: {suggestion}")
                        # 実際の機能実行はここに実装