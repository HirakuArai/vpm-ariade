# --- core/ui_components.py ---
"""
Enhanced UI Components for Kai VPM
UI/UX改善のための視覚化コンポーネント
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from typing import Dict, List, Optional, Any
from datetime import datetime
import pandas as pd

from .dynamic_schema import DynamicProjectSchema, FieldStatus, FieldPriority
from .models import ProjectPhase

class ProjectVisualization:
    """プロジェクト視覚化コンポーネント"""
    
    @staticmethod
    def render_project_card(project_id: str, project_data: Dict) -> None:
        """プロジェクトカード表示"""
        with st.container():
            # カードのスタイル設定
            card_style = """
            <style>
            .project-card {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                padding: 1.5rem;
                border-radius: 10px;
                color: white;
                margin: 1rem 0;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            }
            .project-title {
                font-size: 1.2rem;
                font-weight: bold;
                margin-bottom: 0.5rem;
            }
            .project-meta {
                font-size: 0.9rem;
                opacity: 0.8;
            }
            </style>
            """
            st.markdown(card_style, unsafe_allow_html=True)
            
            # プロジェクト基本情報
            phase = project_data.get("phase", "INCEPTION")
            status = project_data.get("status", "DRAFT")
            completion = project_data.get("completion_percentage", 0.0)
            
            # カード内容
            card_content = f"""
            <div class="project-card">
                <div class="project-title">📋 {project_id}</div>
                <div class="project-meta">
                    🔄 {phase} | 📊 {status} | ⚡ {completion:.1f}% 完了
                </div>
                <div style="margin-top: 0.5rem;">
                    {project_data.get('overview', 'プロジェクト概要なし')[:100]}...
                </div>
            </div>
            """
            st.markdown(card_content, unsafe_allow_html=True)
    
    @staticmethod
    def render_schema_progress(schema: DynamicProjectSchema) -> None:
        """動的スキーマの進捗可視化"""
        st.subheader("📊 プロジェクト情報収集状況")
        
        # 完了状況統計
        total_fields = len(schema.fields)
        completed_fields = sum(1 for field in schema.fields.values() 
                             if field.status in [FieldStatus.DEFINED, FieldStatus.CONFIRMED])
        partial_fields = sum(1 for field in schema.fields.values() 
                           if field.status == FieldStatus.PARTIAL)
        
        completion_percentage = (completed_fields / total_fields * 100) if total_fields > 0 else 0
        
        # プログレスサークル
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            fig = go.Figure(go.Indicator(
                mode = "gauge+number+delta",
                value = completion_percentage,
                domain = {'x': [0, 1], 'y': [0, 1]},
                title = {'text': "完了率"},
                delta = {'reference': 80},
                gauge = {
                    'axis': {'range': [None, 100]},
                    'bar': {'color': "#1f77b4"},
                    'steps': [
                        {'range': [0, 50], 'color': "#ffcccb"},
                        {'range': [50, 80], 'color': "#fff8dc"},
                        {'range': [80, 100], 'color': "#90ee90"}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': 90
                    }
                }
            ))
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.metric("完了済み", completed_fields, delta=None)
            st.metric("部分完了", partial_fields, delta=None)
        
        with col3:
            st.metric("未完了", total_fields - completed_fields - partial_fields, delta=None)
            st.metric("総フィールド", total_fields, delta=None)
    
    @staticmethod
    def render_field_cards(schema: DynamicProjectSchema) -> None:
        """フィールド状況をカード形式で表示"""
        st.subheader("📋 詳細項目状況")
        
        # 優先度別にフィールドを整理
        priority_groups = {
            FieldPriority.REQUIRED: "🔴 必須項目",
            FieldPriority.RECOMMENDED: "🟡 推奨項目", 
            FieldPriority.OPTIONAL: "🟢 オプション項目"
        }
        
        for priority, title in priority_groups.items():
            fields = [field for field in schema.fields.values() if field.priority == priority]
            if not fields:
                continue
                
            st.markdown(f"### {title}")
            
            # フィールドをカード表示
            cols = st.columns(min(len(fields), 3))
            for i, field in enumerate(fields):
                with cols[i % 3]:
                    ProjectVisualization._render_single_field_card(field)
    
    @staticmethod
    def _render_single_field_card(field) -> None:
        """個別フィールドカード"""
        # ステータスアイコン
        status_icons = {
            FieldStatus.UNDEFINED: "⚪",
            FieldStatus.PARTIAL: "🟡",
            FieldStatus.DEFINED: "🟢",
            FieldStatus.CONFIRMED: "✅"
        }
        
        # カード背景色
        status_colors = {
            FieldStatus.UNDEFINED: "#f8f9fa",
            FieldStatus.PARTIAL: "#fff3cd", 
            FieldStatus.DEFINED: "#d4edda",
            FieldStatus.CONFIRMED: "#d1ecf1"
        }
        
        icon = status_icons.get(field.status, "⚪")
        color = status_colors.get(field.status, "#f8f9fa")
        
        # カード表示
        with st.container():
            st.markdown(f"""
            <div style="
                background-color: {color};
                padding: 1rem;
                border-radius: 8px;
                border-left: 4px solid #007bff;
                margin: 0.5rem 0;
            ">
                <div style="font-weight: bold; margin-bottom: 0.5rem;">
                    {icon} {field.name}
                </div>
                <div style="font-size: 0.9rem; color: #666;">
                    {field.questions[0][:50] if field.questions and field.questions[0] else 'フィールド情報'}...
                </div>
                {f'<div style="margin-top: 0.5rem; font-size: 0.8rem;"><strong>値:</strong> {field.value}</div>' if field.value else ''}
            </div>
            """, unsafe_allow_html=True)

class QuestionVisualization:
    """質問表示コンポーネント"""
    
    @staticmethod
    def render_question_cards(questions: List[Any]) -> Dict[str, Any]:
        """質問をカード形式で表示し、回答を収集"""
        if not questions:
            return {}
        
        st.subheader("❓ プロジェクトについて教えてください")
        
        responses = {}
        
        for i, question in enumerate(questions):
            with st.container():
                # 緊急度に応じたスタイル
                urgency_styles = {
                    "immediate": {"color": "#dc3545", "icon": "🔥"},
                    "soon": {"color": "#fd7e14", "icon": "📝"},
                    "eventual": {"color": "#6c757d", "icon": "💭"},
                    "optional": {"color": "#28a745", "icon": "💡"}
                }
                
                urgency = question.urgency.value if hasattr(question, 'urgency') else "soon"
                style = urgency_styles.get(urgency, urgency_styles["soon"])
                
                # 質問カード
                st.markdown(f"""
                <div style="
                    border: 2px solid {style['color']};
                    border-radius: 10px;
                    padding: 1.5rem;
                    margin: 1rem 0;
                    background: linear-gradient(45deg, {style['color']}08, transparent);
                ">
                    <div style="
                        font-size: 1.1rem;
                        font-weight: bold;
                        color: {style['color']};
                        margin-bottom: 1rem;
                    ">
                        {style['icon']} {question.text}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # 回答入力
                response_key = f"question_response_{i}"
                response = st.text_input(
                    "回答", 
                    key=response_key,
                    placeholder="こちらに回答を入力してください..."
                )
                
                if response:
                    responses[question.field_name] = {
                        "value": response,
                        "question_id": question.id,
                        "confidence": 0.8
                    }
        
        return responses

class InteractiveComponents:
    """インタラクティブコンポーネント"""
    
    @staticmethod
    def render_project_selector(projects: List[Dict]) -> Optional[str]:
        """改良されたプロジェクト選択UI"""
        if not projects:
            st.info("📝 プロジェクトがありません。新しいプロジェクトを作成してください。")
            return None
        
        st.subheader("💼 プロジェクト選択")
        
        # プロジェクトをカード形式で表示
        selected_project = None
        
        for project in projects:
            project_id = project.get("identifier", "unknown")
            
            # プロジェクトカードをクリック可能にする
            col1, col2 = st.columns([4, 1])
            
            with col1:
                ProjectVisualization.render_project_card(project_id, project)
            
            with col2:
                if st.button("選択", key=f"select_{project_id}"):
                    selected_project = project_id
        
        return selected_project
    
    @staticmethod
    def render_update_candidates(candidates: List[Dict]) -> Optional[List[Dict]]:
        """更新案を改良されたUIで表示"""
        if not candidates:
            return None
        
        st.subheader("✨ プロジェクト更新案")
        
        with st.container():
            st.markdown("""
            <div style="
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                padding: 1rem;
                border-radius: 10px;
                color: white;
                margin: 1rem 0;
            ">
                <h4>🔄 会話から新しい情報が検出されました</h4>
                <p>以下の更新を承認しますか？</p>
            </div>
            """, unsafe_allow_html=True)
            
            # 更新案を表形式で表示
            update_data = []
            for candidate in candidates:
                update_data.append({
                    "フィールド": candidate.get("field", ""),
                    "現在の値": candidate.get("old", "未設定"),
                    "新しい値": candidate.get("new", ""),
                    "信頼度": f"{candidate.get('confidence', 0.5):.0%}"
                })
            
            df = pd.DataFrame(update_data)
            st.dataframe(df, use_container_width=True)
            
            # アクションボタン
            col1, col2, col3 = st.columns([1, 1, 2])
            
            with col1:
                if st.button("✅ すべて承認", type="primary"):
                    return candidates
            
            with col2:
                if st.button("❌ キャンセル"):
                    return []
            
            with col3:
                st.info("承認すると、プロジェクト情報が自動更新されます")
        
        return None

class StatusIndicators:
    """ステータス表示コンポーネント"""
    
    @staticmethod
    def render_project_health(health_data: Dict) -> None:
        """プロジェクト健全性表示"""
        health_score = health_data.get("overall_score", 0.5)
        risk_level = health_data.get("risk_level", "medium")
        
        # 健全性スコア
        col1, col2, col3 = st.columns(3)
        
        with col1:
            fig = go.Figure(go.Indicator(
                mode = "gauge+number",
                value = health_score * 100,
                domain = {'x': [0, 1], 'y': [0, 1]},
                title = {'text': "健全性"},
                gauge = {
                    'axis': {'range': [None, 100]},
                    'bar': {'color': "#1f77b4"},
                    'steps': [
                        {'range': [0, 30], 'color': "#ff6b6b"},
                        {'range': [30, 70], 'color': "#ffd93d"},
                        {'range': [70, 100], 'color': "#6bcf7f"}
                    ]
                }
            ))
            fig.update_layout(height=200)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            risk_colors = {
                "low": "🟢 低",
                "medium": "🟡 中", 
                "high": "🔴 高"
            }
            st.metric("リスクレベル", risk_colors.get(risk_level, "🟡 中"))
        
        with col3:
            alerts_count = health_data.get("alerts_count", 0)
            st.metric("アラート数", alerts_count, delta=None)
    
    @staticmethod
    def render_phase_progression(current_phase: ProjectPhase, progress: Dict) -> None:
        """フェーズ進捗表示"""
        phases = ["INCEPTION", "DEFINITION", "PLANNING", "EXECUTION", "MONITORING", "CLOSURE"]
        
        # 現在のフェーズインデックス
        try:
            current_index = phases.index(current_phase.value)
        except (ValueError, AttributeError):
            current_index = 0
        
        # 進捗バー作成
        progress_data = []
        for i, phase in enumerate(phases):
            if i < current_index:
                status = "完了"
                color = "#28a745"
            elif i == current_index:
                status = "進行中"
                color = "#007bff"
            else:
                status = "未開始"
                color = "#6c757d"
            
            progress_data.append({
                "フェーズ": phase,
                "ステータス": status,
                "色": color
            })
        
        # 視覚的プログレスバー
        st.subheader("🗺️ プロジェクトフェーズ")
        
        progress_html = "<div style='display: flex; align-items: center; margin: 1rem 0;'>"
        
        for i, phase_data in enumerate(progress_data):
            color = phase_data["色"]
            is_current = (i == current_index)
            
            # フェーズサークル
            circle_style = f"""
            width: 30px; height: 30px; border-radius: 50%; 
            background-color: {color}; color: white; 
            display: flex; align-items: center; justify-content: center;
            font-weight: bold; margin: 0 10px;
            {'border: 3px solid #ffd700;' if is_current else ''}
            """
            
            progress_html += f"<div style='{circle_style}'>{i+1}</div>"
            
            # 接続線（最後以外）
            if i < len(progress_data) - 1:
                line_color = color if i < current_index else "#dee2e6"
                progress_html += f"<div style='flex: 1; height: 2px; background-color: {line_color};'></div>"
        
        progress_html += "</div>"
        
        # フェーズ名表示
        phase_names_html = "<div style='display: flex; justify-content: space-between; font-size: 0.8rem; margin-top: 0.5rem;'>"
        for phase_data in progress_data:
            phase_names_html += f"<span>{phase_data['フェーズ']}</span>"
        phase_names_html += "</div>"
        
        st.markdown(progress_html + phase_names_html, unsafe_allow_html=True)