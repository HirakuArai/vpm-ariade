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
        
        # ナビゲーション状態を明示的に保持
        if hasattr(st.session_state, 'navigation_state'):
            st.session_state.navigation_state.current_page = PageType.PROJECT_DETAILS
            st.session_state.navigation_state.selected_project_id = project_id
        
        # プロジェクト詳細ページ専用の保護フラグ
        st.session_state._in_project_details = True
        
        try:
            # プロジェクトデータの読み込み
            project_data = ProjectDetailsPage._load_project_data(project_id)
            
            if not project_data:
                st.error("プロジェクトデータが見つかりません")
                return
            
            # AI説明をキャッシュから取得または生成
            cache_key = f"project_detail_ai_{project_id}"
            if cache_key not in st.session_state:
                # AIによるプロジェクト説明生成
                with st.spinner("🤖 AIがプロジェクト詳細を整理中..."):
                    # ナビゲーション状態を一時的に固定
                    original_page = st.session_state.navigation_state.current_page
                    original_project = st.session_state.navigation_state.selected_project_id
                    
                    detailed_description = ProjectDetailsPage._generate_ai_description(project_id, project_data)
                    st.session_state[cache_key] = detailed_description
                    
                    # ナビゲーション状態を強制的に復元
                    st.session_state.navigation_state.current_page = PageType.PROJECT_DETAILS
                    st.session_state.navigation_state.selected_project_id = project_id
            else:
                detailed_description = st.session_state[cache_key]
            
            # ページ表示前に最終ナビゲーション状態チェック
            if hasattr(st.session_state, 'navigation_state'):
                st.session_state.navigation_state.current_page = PageType.PROJECT_DETAILS
                st.session_state.navigation_state.selected_project_id = project_id
            
            # AI生成の説明を表示
            if detailed_description:
                st.markdown(detailed_description)
            else:
                st.error("AIによるプロジェクト説明の生成に失敗しました")
                
            # 生データ表示オプション
            with st.expander("🔍 生データを確認", expanded=False):
                st.json(project_data)
            
            # AI説明の再生成ボタン
            col1, col2, col3 = st.columns([1, 1, 3])
            with col1:
                if st.button("🔄 AI説明を再生成", key=f"regenerate_ai_{project_id}"):
                    # キャッシュをクリア
                    cache_key = f"project_detail_ai_{project_id}"
                    if cache_key in st.session_state:
                        del st.session_state[cache_key]
                    # ナビゲーション状態を保持しながらリロード
                    st.session_state.navigation_state.current_page = PageType.PROJECT_DETAILS
                    st.session_state.navigation_state.selected_project_id = project_id
                    st.rerun()
            
        except Exception as e:
            st.error(f"プロジェクト詳細の読み込みに失敗しました: {e}")
    
    @staticmethod
    def _generate_ai_description(project_id: str, project_data: Dict) -> str:
        """プロジェクト詳細のAI生成"""
        try:
            import openai
            from core.v2.openai_config import get_openai_model
            from core.prompt_logger import log_call
            from core.log_schema import RequestKind
            
            # ナビゲーション状態を保持（AI処理中の状態変更を防ぐ）
            if hasattr(st.session_state, 'navigation_state'):
                st.session_state.navigation_state.current_page = PageType.PROJECT_DETAILS
                st.session_state.navigation_state.selected_project_id = project_id
            
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
            
            # Streamlit特有の状態変更を防ぐため、Gitコミットを一時的に無効化
            import os
            old_git_disabled = os.environ.get("DISABLE_GIT_COMMITS", "")
            os.environ["DISABLE_GIT_COMMITS"] = "1"
            
            try:
                # LLMロギングを使用してAPIを呼び出し
                with log_call("kai", RequestKind.PROJECT_DETAIL) as log:
                    request_data = {
                        "model": get_openai_model(),
                        "messages": [
                            {"role": "system", "content": "あなたはプロジェクトマネジメントの専門家で、複雑なプロジェクト情報をわかりやすく整理して説明することが得意です。"},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.7,
                        "max_tokens": 2000
                    }
                
                    log['log_request'](request_data)
                    
                    # OpenAI APIを使用して説明を生成
                    response = openai.chat.completions.create(**request_data)
                    
                    # レスポンスをログに記録
                    response_data = {
                        "choices": [
                            {
                                "message": {
                                    "role": response.choices[0].message.role,
                                    "content": response.choices[0].message.content
                                }
                            }
                        ],
                        "usage": {
                            "prompt_tokens": response.usage.prompt_tokens,
                            "completion_tokens": response.usage.completion_tokens,
                            "total_tokens": response.usage.total_tokens
                        }
                    }
                    log['log_response'](response_data, response.usage.prompt_tokens, response.usage.completion_tokens)
                    
                    # ナビゲーション状態を再度確認（AI処理後も維持）
                    if hasattr(st.session_state, 'navigation_state'):
                        st.session_state.navigation_state.current_page = PageType.PROJECT_DETAILS
                        st.session_state.navigation_state.selected_project_id = project_id
                    
                    return response.choices[0].message.content
            
            finally:
                # Git設定を復元
                if old_git_disabled:
                    os.environ["DISABLE_GIT_COMMITS"] = old_git_disabled
                else:
                    os.environ.pop("DISABLE_GIT_COMMITS", None)
                
                # プロジェクト詳細生成完了後、保留されていたLLMログをGitHubに反映
                try:
                    from core.git_ops import commit_and_push_llm_logs
                    if commit_and_push_llm_logs():
                        print("✅ プロジェクト詳細生成後のLLMログをGitHubに反映しました", flush=True)
                except Exception as e:
                    print(f"⚠️ プロジェクト詳細生成後のLLMログ反映に失敗: {e}", flush=True)
            
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
            # セッション固有のIDを確保
            if "nav_session_id" not in st.session_state:
                import random
                st.session_state.nav_session_id = str(random.randint(100000, 999999))
            
            with col1:
                if st.button("📈 進捗を教えて", use_container_width=True, key=f"progress_btn_{project_id}_{st.session_state.nav_session_id}"):
                    suggested_input = "このプロジェクトの現在の進捗状況を教えてください。"
            
            with col2:
                if st.button("⚠️ リスクを確認", use_container_width=True, key=f"risk_btn_{project_id}_{st.session_state.nav_session_id}"):
                    suggested_input = "このプロジェクトの現在のリスクや課題を教えてください。"
            
            with col3:
                if st.button("📅 次のステップ", use_container_width=True, key=f"next_step_btn_{project_id}_{st.session_state.nav_session_id}"):
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
        """会話処理（リロードは chat_handler_ai 内で処理される）"""
        try:
            # app.pyのprocess_chat_inputを呼び出す
            import sys
            import os
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            
            # セッション状態を確認してプロジェクトを設定
            st.session_state["current_project_id"] = project_id
            
            # 現在のページ状態を保持（PROJECT_CHATページにいることを明示）
            if hasattr(st.session_state, 'navigation_state'):
                st.session_state.navigation_state.current_page = PageType.PROJECT_CHAT
                st.session_state.navigation_state.selected_project_id = project_id
            
            # AI-First chat_handlerのインポートと実行（循環インポート回避）
            from .chat_handler_ai import process_chat_input_ai
            process_chat_input_ai(user_input, project_id)
            
            # プロジェクト会話の場合は明示的にページ更新を実行
            st.rerun()
            
        except Exception as e:
            st.error(f"会話処理エラー: {e}")
            import traceback
            st.error(traceback.format_exc())