# --- core/pages.py ---
"""
Dedicated Page Modules - 専用ページモジュール
各ページの専用レンダリング機能
"""

import streamlit as st
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from .navigation import PageType, navigator
from .dynamic_schema import get_project_schema
from .ui_components import ProjectVisualization, StatusIndicators
from .lifecycle_manager import ProjectLifecycleManager
from .models import ProjectPhase
import yaml

class ProjectInfoPage:
    """プロジェクト情報ページ"""
    
    @staticmethod
    def render(project_id: str):
        """プロジェクト情報ページの描画"""
        st.subheader("📋 プロジェクト情報収集状況")
        
        try:
            # プロジェクト基本情報
            project_data = ProjectInfoPage._get_project_data(project_id)
            schema = get_project_schema(project_id)
            
            # プロジェクト概要カード
            with st.container():
                st.markdown("### 🎯 プロジェクト概要")
                
                col1, col2, col3 = st.columns([2, 1, 1])
                
                with col1:
                    st.write(f"**名前**: {project_data.get('name', project_id)}")
                    st.write(f"**説明**: {project_data.get('description', '説明なし')}")
                    st.write(f"**ステータス**: {project_data.get('status', 'UNKNOWN')}")
                
                with col2:
                    # 完了率の表示
                    completion = schema.get_completion_percentage()
                    st.metric("情報収集完了率", f"{completion:.1f}%")
                
                with col3:
                    # フィールド統計
                    total_fields = len(schema.fields)
                    defined_fields = len([f for f in schema.fields.values() if f.value is not None])
                    st.metric("定義済みフィールド", f"{defined_fields}/{total_fields}")
            
            st.divider()
            
            # 動的スキーマ可視化
            st.markdown("### 📊 情報収集状況")
            viz = ProjectVisualization()
            
            # プログレス表示
            viz.render_schema_progress(schema)
            
            st.markdown("### 📝 フィールド詳細")
            
            # タブで情報を整理
            tab1, tab2, tab3, tab4 = st.tabs(["📊 確定情報", "⏳ 部分情報", "❓ 未定義情報", "🔄 再分析"])
            
            with tab1:
                ProjectInfoPage._render_field_status(schema, "confirmed")
            
            with tab2:
                ProjectInfoPage._render_field_status(schema, "partial")
                
            with tab3:
                ProjectInfoPage._render_field_status(schema, "undefined")
            
            with tab4:
                ProjectInfoPage._render_reanalysis_tab(project_id)
            
            # 推奨される次のアクション
            st.markdown("### 💡 推奨アクション")
            pending_questions = schema.get_pending_questions(max_questions=5)
            
            if pending_questions:
                st.info("💬 **次の会話で聞いてみましょう:**")
                for field_name, questions in pending_questions:
                    st.write(f"**{field_name}**: {questions[0]}")
            else:
                st.success("🎉 必要な情報がすべて収集されています！")
            
                
        except Exception as e:
            st.error(f"プロジェクト状況の読み込みに失敗しました: {e}")
    
    @staticmethod
    def _get_project_data(project_id: str) -> Dict:
        """プロジェクトデータの取得"""
        try:
            project_path = Path(f"data/projects/{project_id}.json")
            if project_path.exists():
                return json.loads(project_path.read_text(encoding="utf-8"))
            return {"name": project_id}
        except Exception:
            return {"name": project_id}
    
    @staticmethod
    def _render_field_status(schema, status_filter: str):
        """フィールド状態別の表示"""
        from .dynamic_schema import FieldStatus
        
        if status_filter == "confirmed":
            fields = [(name, field) for name, field in schema.fields.items() 
                     if field.status == FieldStatus.CONFIRMED]
            if not fields:
                st.info("確定した情報はまだありません")
                return
                
        elif status_filter == "partial":
            fields = [(name, field) for name, field in schema.fields.items() 
                     if field.status == FieldStatus.PARTIAL]
            if not fields:
                st.info("部分的な情報はありません")
                return
                
        elif status_filter == "undefined":
            fields = [(name, field) for name, field in schema.fields.items() 
                     if field.status == FieldStatus.UNDEFINED]
            if not fields:
                st.success("すべての情報が定義されています！")
                return
        
        for field_name, field in fields:
            with st.expander(f"📋 {field_name}", expanded=False):
                if field.value is not None:
                    st.write(f"**値**: {field.value}")
                
                if field.questions:
                    st.write(f"**関連質問**: {field.questions[0]}")
                
                # メタデータ
                col1, col2 = st.columns(2)
                with col1:
                    st.caption(f"優先度: {field.priority.value}")
                with col2:
                    st.caption(f"ステータス: {field.status.value}")
    
    @staticmethod
    def _render_reanalysis_tab(project_id: str):
        """再分析タブの描画"""
        try:
            from core.reanalysis_ui import render_reanalysis_interface
            render_reanalysis_interface(project_id)
        except Exception as e:
            st.error(f"再分析機能の読み込みに失敗しました: {e}")
    

class PhaseProgressPage:
    """フェーズ進捗ページ"""
    
    @staticmethod
    def render(project_id: str):
        """フェーズ進捗ページの描画"""
        st.subheader("📈 プロジェクトフェーズ進捗")
        
        try:
            lifecycle_manager = ProjectLifecycleManager()
            
            # 現在のフェーズと進捗
            current_phase = lifecycle_manager.get_current_phase(project_id)
            progress_info = lifecycle_manager.get_phase_progress(project_id)
            
            # フェーズ概要
            col1, col2, col3 = st.columns(3)
            
            with col1:
                phase_emoji = {
                    "INCEPTION": "💡",
                    "DEFINITION": "📋", 
                    "PLANNING": "📅",
                    "EXECUTION": "🚀",
                    "MONITORING": "📊",
                    "CLOSURE": "✅"
                }
                st.metric(
                    "現在フェーズ", 
                    f"{phase_emoji.get(current_phase.value, '📌')} {current_phase.value}"
                )
            
            with col2:
                completion = progress_info.get("completion_percentage", 0.0)
                st.metric("完了率", f"{completion:.1f}%")
            
            with col3:
                can_advance = progress_info.get("can_advance", False)
                status_text = "✅ 進行可能" if can_advance else "⏳ 準備中"
                st.metric("進行状況", status_text)
            
            st.divider()
            
            # フェーズ進行チャート
            st.markdown("### 📊 フェーズ進行チャート")
            PhaseProgressPage._render_phase_timeline(current_phase)
            
            st.divider()
            
            # 現在フェーズの詳細
            st.markdown(f"### 🎯 {current_phase.value} フェーズ詳細")
            PhaseProgressPage._render_current_phase_details(project_id, lifecycle_manager)
            
            # フェーズ進行コントロール
            st.markdown("### 🎮 フェーズ制御")
            PhaseProgressPage._render_phase_controls(project_id, lifecycle_manager, can_advance)
            
        except Exception as e:
            st.error(f"フェーズ情報の読み込みに失敗しました: {e}")
    
    
    @staticmethod
    def _render_phase_timeline(current_phase: ProjectPhase):
        """フェーズタイムライン表示"""
        phases = [
            ("💡", "INCEPTION", "プロジェクト発足"),
            ("📋", "DEFINITION", "要件定義"),
            ("📅", "PLANNING", "計画策定"),
            ("🚀", "EXECUTION", "実行"),
            ("📊", "MONITORING", "監視"),
            ("✅", "CLOSURE", "完了")
        ]
        
        current_index = None
        for i, (_, phase_name, _) in enumerate(phases):
            if phase_name == current_phase.value:
                current_index = i
                break
        
        if current_index is not None:
            progress = (current_index + 1) / len(phases)
            st.progress(progress, text=f"進捗: {current_index + 1}/{len(phases)} フェーズ")
        
        # フェーズカード表示
        cols = st.columns(len(phases))
        for i, (emoji, phase_name, description) in enumerate(phases):
            with cols[i]:
                if i == current_index:
                    st.markdown(f"""
                    <div style="
                        border: 2px solid #1f77b4;
                        border-radius: 8px;
                        padding: 10px;
                        text-align: center;
                        background-color: #e6f3ff;
                    ">
                        <h3>{emoji}</h3>
                        <strong>{phase_name}</strong><br>
                        <small>{description}</small>
                    </div>
                    """, unsafe_allow_html=True)
                elif i < current_index:
                    st.markdown(f"""
                    <div style="
                        border: 1px solid #90EE90;
                        border-radius: 8px;
                        padding: 10px;
                        text-align: center;
                        background-color: #f0fff0;
                        opacity: 0.7;
                    ">
                        <h3>{emoji}</h3>
                        <strong>{phase_name}</strong><br>
                        <small>{description}</small>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div style="
                        border: 1px solid #ddd;
                        border-radius: 8px;
                        padding: 10px;
                        text-align: center;
                        opacity: 0.5;
                    ">
                        <h3>{emoji}</h3>
                        <strong>{phase_name}</strong><br>
                        <small>{description}</small>
                    </div>
                    """, unsafe_allow_html=True)
    
    @staticmethod
    def _render_current_phase_details(project_id: str, lifecycle_manager):
        """現在フェーズの詳細表示"""
        current_phase = lifecycle_manager.get_current_phase(project_id)
        
        phase_descriptions = {
            ProjectPhase.INCEPTION: {
                "description": "プロジェクトのアイデアと基本的な方向性を決定",
                "key_activities": [
                    "プロジェクト概要の定義",
                    "ステークホルダーの特定",
                    "初期リスクの評価",
                    "プロジェクト価値の検証"
                ]
            },
            ProjectPhase.DEFINITION: {
                "description": "プロジェクトの詳細要件と範囲を定義",
                "key_activities": [
                    "詳細要件の収集",
                    "スコープの明確化",
                    "成功指標の設定",
                    "制約条件の整理"
                ]
            },
            ProjectPhase.PLANNING: {
                "description": "実行計画とリソース計画を策定",
                "key_activities": [
                    "作業分解構造の作成",
                    "スケジュール策定",
                    "リソース配分",
                    "リスク対策計画"
                ]
            },
            ProjectPhase.EXECUTION: {
                "description": "計画に基づいてプロジェクトを実行",
                "key_activities": [
                    "タスクの実行",
                    "進捗の追跡",
                    "品質管理",
                    "チーム管理"
                ]
            },
            ProjectPhase.MONITORING: {
                "description": "プロジェクトの進捗と品質を監視",
                "key_activities": [
                    "KPI監視",
                    "リスク監視",
                    "品質検証",
                    "ステークホルダー報告"
                ]
            },
            ProjectPhase.CLOSURE: {
                "description": "プロジェクトの完了と成果の引き渡し",
                "key_activities": [
                    "最終成果物の確認",
                    "プロジェクトの評価",
                    "教訓の整理",
                    "チームの解散"
                ]
            }
        }
        
        phase_info = phase_descriptions.get(current_phase)
        if phase_info:
            st.write(f"**概要**: {phase_info['description']}")
            
            st.write("**主要活動**:")
            for activity in phase_info["key_activities"]:
                st.write(f"• {activity}")
    
    @staticmethod
    def _render_phase_controls(project_id: str, lifecycle_manager, can_advance: bool):
        """フェーズ制御UI"""
        col1, col2 = st.columns(2)
        
        with col1:
            if can_advance:
                if st.button("⏭️ 次のフェーズへ進む", type="primary"):
                    try:
                        result = lifecycle_manager.advance_phase(project_id)
                        if result.get("success"):
                            st.success(f"✅ {result.get('new_phase')} フェーズに進みました！")
                            st.rerun()
                        else:
                            st.error(f"❌ フェーズ進行に失敗: {result.get('message')}")
                    except Exception as e:
                        st.error(f"❌ エラーが発生しました: {e}")
            else:
                st.button("⏭️ 次のフェーズへ進む", disabled=True)
                st.caption("進行条件が満たされていません")
        
        with col2:
            if st.button("🔄 フェーズ条件を再評価"):
                try:
                    progress_info = lifecycle_manager.get_phase_progress(project_id)
                    if progress_info.get("can_advance"):
                        st.success("✅ 次のフェーズに進む準備ができています！")
                    else:
                        missing = progress_info.get("missing_requirements", [])
                        if missing:
                            st.warning(f"⚠️ 不足要件: {', '.join(missing)}")
                        else:
                            st.info("ℹ️ まだ進行条件が満たされていません")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ 評価中にエラーが発生しました: {e}")

class ConversationHistoryPage:
    """会話履歴ページ"""
    
    @staticmethod
    def render(project_id: str):
        """会話履歴ページの描画"""
        st.subheader("💬 プロジェクト会話履歴")
        
        try:
            # 会話ログの取得
            conversations = ConversationHistoryPage._get_project_conversations(project_id)
            
            if not conversations:
                st.info("このプロジェクトの会話履歴はまだありません")
                return
            
            # 統計情報
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                total_messages = sum(len(conv["messages"]) for conv in conversations)
                st.metric("総メッセージ数", total_messages)
            
            with col2:
                # 総会話数（userメッセージの合計）
                total_conversations = sum(
                    len([msg for msg in conv["messages"] if msg.get("role") == "user"]) 
                    for conv in conversations
                )
                st.metric("総会話数", total_conversations)
            
            with col3:
                total_days = len(conversations)
                st.metric("会話日数", f"{total_days}日")
            
            with col4:
                if conversations:
                    latest_date = max(conv["date"] for conv in conversations)
                    st.metric("最新会話", latest_date)
            
            st.divider()
            
            # 日別会話履歴
            st.markdown("### 📅 日別会話履歴")
            
            # 日付でソート（新しい順）
            conversations.sort(key=lambda x: x["date"], reverse=True)
            
            for conversation in conversations:
                date_str = conversation["date"]
                messages = conversation["messages"]
                
                # 会話数を計算（userメッセージの数 = 会話セット数）
                conversation_count = len([msg for msg in messages if msg.get("role") == "user"])
                
                with st.expander(f"📅 {date_str} ({conversation_count}会話)", expanded=False):
                    for msg in messages:
                        timestamp = msg.get("timestamp", "")
                        role = msg.get("role", "unknown")
                        content = msg.get("content", "")
                        
                        if role == "user":
                            st.markdown(f"""
                            <div style="
                                background-color: #e6f3ff;
                                padding: 10px;
                                border-radius: 8px;
                                margin: 5px 0;
                                border-left: 4px solid #1f77b4;
                            ">
                                <strong>👤 ユーザー</strong> <small>{timestamp}</small><br>
                                {content}
                            </div>
                            """, unsafe_allow_html=True)
                        else:
                            st.markdown(f"""
                            <div style="
                                background-color: #f0f0f0;
                                padding: 10px;
                                border-radius: 8px;
                                margin: 5px 0;
                                border-left: 4px solid #666;
                            ">
                                <strong>🤖 AI</strong> <small>{timestamp}</small><br>
                                {content}
                            </div>
                            """, unsafe_allow_html=True)
            
        except Exception as e:
            st.error(f"会話履歴の読み込みに失敗しました: {e}")
    
    
    @staticmethod
    def _get_project_conversations(project_id: str) -> List[Dict]:
        """プロジェクト会話履歴の取得"""
        conversations = []
        
        try:
            conv_dir = Path(f"data/conversations/{project_id}")
            if not conv_dir.exists():
                return conversations
            
            # JSONL ファイルを日付順で処理
            for jsonl_file in sorted(conv_dir.glob("*.jsonl")):
                date_str = jsonl_file.stem  # ファイル名から日付を取得
                messages = []
                
                try:
                    with jsonl_file.open(encoding="utf-8") as f:
                        for line in f:
                            if line.strip():
                                msg = json.loads(line.strip())
                                messages.append(msg)
                    
                    if messages:
                        conversations.append({
                            "date": date_str,
                            "messages": messages
                        })
                        
                except Exception as e:
                    st.warning(f"ファイル {jsonl_file.name} の読み込みに失敗: {e}")
            
            return conversations
            
        except Exception as e:
            st.error(f"会話履歴ディレクトリの読み込みに失敗: {e}")
            return conversations


class ProjectDetailsPage:
    """プロジェクト詳細ページ"""
    
    @staticmethod
    def render(project_id: str):
        """プロジェクト詳細ページの描画"""
        st.subheader("📄 プロジェクト詳細ドキュメント")
        
        try:
            # プロジェクトデータの読み込み
            project_data = ProjectDetailsPage._load_project_data(project_id)
            
            if not project_data:
                st.error("プロジェクトデータが見つかりません")
                return
            
            # AIによるプロジェクト説明生成
            with st.spinner("🤖 AIがプロジェクト詳細を整理中..."):
                detailed_description = ProjectDetailsPage._generate_ai_description(project_id, project_data)
            
            # AI生成の説明を表示
            if detailed_description:
                st.markdown(detailed_description)
            else:
                st.error("AIによるプロジェクト説明の生成に失敗しました")
                
            # 生データ表示オプション
            with st.expander("🔍 生データを確認", expanded=False):
                st.json(project_data)
            
        except Exception as e:
            st.error(f"プロジェクト詳細の読み込みに失敗しました: {e}")
    
    @staticmethod
    def _generate_ai_description(project_id: str, project_data: Dict) -> str:
        """プロジェクト詳細のAI生成"""
        try:
            import openai
            
            # プロンプトの作成
            prompt = f"""
以下のプロジェクトデータJSONを基に、プロジェクトの詳細をわかりやすく説明してください。

説明には以下の要素を含めてください：
1. プロジェクトの概要と目的
2. 現在の状況と進捗
3. 主要なステークホルダー
4. 重要なマイルストーンと期限
5. リスクと課題
6. チーム構成と役割
7. 最新の更新内容

マークダウン形式で、見出しや箇条書きを使って読みやすく整理してください。
絵文字も適切に使用してください。

プロジェクトデータ:
{json.dumps(project_data, ensure_ascii=False, indent=2)}
"""
            
            # OpenAI APIを使用して説明を生成
            response = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "あなたはプロジェクトマネジメントの専門家で、複雑なプロジェクト情報をわかりやすく整理して説明することが得意です。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            st.error(f"AI説明の生成エラー: {e}")
            return None
    
    @staticmethod
    def _load_project_data(project_id: str) -> Optional[Dict]:
        """プロジェクトデータの読み込み"""
        try:
            project_path = Path(f"data/projects/{project_id}.json")
            if project_path.exists():
                with project_path.open(encoding="utf-8") as f:
                    return json.load(f)
            return None
        except Exception as e:
            st.error(f"プロジェクトファイルの読み込みエラー: {e}")
            return None
    


class ProjectChatPage:
    """プロジェクト会話専用ページ"""
    
    @staticmethod
    def render(project_id: str):
        """プロジェクト会話ページの描画"""
        st.subheader("💬 プロジェクトについて質問・相談")
        
        try:
            # プロジェクト名の取得
            project_data = ProjectChatPage._get_project_data(project_id)
            project_name = project_data.get("display_name", project_data.get("name", project_id))
            
            st.info(f"🎯 現在選択中のプロジェクト: **{project_name}**")
            
            # 会話履歴の表示
            st.markdown("### 📄 会話履歴")
            
            # プロジェクト会話履歴の取得
            history = ProjectChatPage._load_project_conversation_history(project_id)
            
            if history:
                # 会話履歴コンテナ
                with st.container():
                    # 最新20件まで表示
                    display_history = history[-20:] if len(history) > 20 else history
                    
                    for msg in display_history:
                        role = msg.get("role", "unknown")
                        content = msg.get("content", "")
                        
                        if role == "user":
                            with st.chat_message("user"):
                                st.markdown(content)
                        else:
                            with st.chat_message("assistant"):
                                st.markdown(content)
                    
                    # 会話数の表示
                    total_conversations = len([msg for msg in history if msg["role"] == "user"])
                    displayed_conversations = len([msg for msg in display_history if msg["role"] == "user"])
                    
                    if len(history) > 20:
                        st.caption(f"（全{total_conversations}会話中、最新{displayed_conversations}会話を表示）")
            else:
                st.info("📢 このプロジェクトでの会話履歴はまだありません")
            
            # 会話入力インターフェース
            st.markdown("### 💬 新しい質問")
            
            # サジェストボタン
            col1, col2, col3 = st.columns(3)
            
            suggested_input = None
            with col1:
                if st.button("📈 進捗を教えて", use_container_width=True):
                    suggested_input = "このプロジェクトの現在の進捗状況を教えてください。"
            
            with col2:
                if st.button("⚠️ リスクを確認", use_container_width=True):
                    suggested_input = "このプロジェクトの現在のリスクや課題を教えてください。"
            
            with col3:
                if st.button("📅 次のステップ", use_container_width=True):
                    suggested_input = "次にやるべきことは何ですか？"
            
            # チャット入力
            user_input = st.chat_input(
                f"プロジェクト「{project_name}」について質問してください...",
                key="project_chat_input"
            )
            
            # サジェストまたはユーザー入力の処理
            final_input = suggested_input if suggested_input else user_input
            
            if final_input:
                # ナビゲーション状態を更新
                if hasattr(st.session_state, 'navigation_state'):
                    st.session_state.navigation_state.selected_project_id = project_id
                st.session_state["current_project_id"] = project_id  # 後方互換性
                
                # 会話処理を実行
                with st.spinner("🤖 AIが回答を作成中..."):
                    try:
                        # 会話処理の実行
                        ProjectChatPage._process_chat_with_reload(project_id, final_input)
                    except Exception as e:
                        st.error(f"会話処理中にエラーが発生しました: {e}")
            
        except Exception as e:
            st.error(f"プロジェクト会話ページの表示エラー: {e}")
    
    @staticmethod
    def _get_project_data(project_id: str) -> Dict:
        """プロジェクトデータの取得"""
        try:
            project_path = Path(f"data/projects/{project_id}.json")
            if project_path.exists():
                with project_path.open(encoding="utf-8") as f:
                    return json.load(f)
            return {"name": project_id}
        except Exception:
            return {"name": project_id}
    
    @staticmethod
    def _load_project_conversation_history(project_id: str) -> List[Dict]:
        """プロジェクト固有の会話履歴を読み込み"""
        project_conv_dir = Path(f"data/conversations/{project_id}")
        history = []
        
        if project_conv_dir.exists():
            # 全ての会話ログファイルを取得して日付順にソート
            log_files = sorted([f for f in project_conv_dir.glob("*.jsonl")])
            
            # 最近の3日分のファイルのみを読み込み（パフォーマンス考慮）
            recent_files = log_files[-3:] if len(log_files) > 3 else log_files
            
            for log_file in recent_files:
                try:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            if line.strip():  # 空行をスキップ
                                entry = json.loads(line.strip())
                                history.append({
                                    "role": entry["role"],
                                    "content": entry["content"]
                                })
                except Exception as e:
                    print(f"Error loading project history from {log_file}: {e}")
        
        return history
    
    @staticmethod
    def _process_chat_with_reload(project_id: str, user_input: str):
        """会話処理と完了後のリロード"""
        try:
            # app.pyのprocess_chat_inputを呼び出す
            import sys
            import os
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            
            # セッション状態を確認してプロジェクトを設定
            st.session_state["current_project_id"] = project_id
            
            # process_chat_inputのインポートと実行
            from app import process_chat_input
            process_chat_input(user_input)
            
            # 会話完了後にリロード
            st.rerun()
            
        except Exception as e:
            st.error(f"会話処理エラー: {e}")
            import traceback
            st.error(traceback.format_exc())