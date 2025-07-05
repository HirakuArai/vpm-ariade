"""
Memory Chat β - Memory Layer Phase 2 Stage B
メモリレイヤーの読み書き機能検証ページ
"""

import streamlit as st
import json
import os
import sys
import logging
from datetime import datetime
from pathlib import Path

# ロガーの設定
logger = logging.getLogger(__name__)

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# ページ設定（最初に実行する必要がある）
st.set_page_config(
    page_title="Memory Chat β", 
    page_icon="🧠",
    layout="wide"
)

# Memory Layer モジュールのインポート
try:
    from core.memory_bridge import memory_bridge, log_event, load_current_memory, get_context_for_ai
    from config import is_memory_enabled, is_memory_read_enabled
    from core.ai_project_manager import create_ai_project_manager
    from core.v2.openai_config import get_openai_model, create_chat_completion
    from core.llm_logger import render_llm_stats_for_memory_chat, get_recent_llm_calls, format_messages_for_display
    from core.github_sync import sync_memory_with_feedback, on_session_end_hook, setup_session_end_hook, manual_memory_sync
except ImportError as e:
    st.error(f"モジュールのインポートに失敗しました: {e}")
    st.stop()

# OpenAI API キーの取得
def get_openai_api_key():
    key = os.getenv("OPENAI_API_KEY")
    if key:
        return key
    try:
        return st.secrets["OPENAI_API_KEY"]
    except Exception:
        pass
    return None

# Memory Chat β ヘッダー
st.title("🧠 Memory Chat β")
st.caption("Memory Layer Phase 2 - Stage B検証ページ")

# フィーチャーフラグの一時的上書き（このページ内でのみ有効）
# セッション状態で一時的にメモリ機能を有効化
if "memory_beta_enabled" not in st.session_state:
    st.session_state["memory_beta_enabled"] = True

# フィーチャーフラグ状態表示
col1, col2, col3 = st.columns(3)
with col1:
    memory_enabled = is_memory_enabled() or st.session_state.get("memory_beta_enabled", False)
    st.metric("Memory Layer", "有効" if memory_enabled else "無効", 
              delta="β版で強制有効" if st.session_state.get("memory_beta_enabled") else None)

with col2:
    read_enabled = is_memory_read_enabled() or st.session_state.get("memory_beta_enabled", False)
    st.metric("Memory Read", "有効" if read_enabled else "無効",
              delta="β版で強制有効" if st.session_state.get("memory_beta_enabled") else None)

with col3:
    api_key = get_openai_api_key()
    st.metric("OpenAI API", "接続済み" if api_key else "未設定")

# メモリが無効の場合の警告（本来の設定）
if not is_memory_enabled():
    st.info("💡 本ページではメモリ機能をβ版として一時的に有効化しています。本番環境では`MEMORY_LAYER_ENABLED=True`で有効化してください。")

# APIキーがない場合は停止
if not api_key:
    st.error("❌ OpenAI API キーが設定されていません。")
    st.stop()

# Memory Bridge の強制有効化（β版専用）
def enable_memory_for_beta():
    """Memory Layer機能をβ版として一時的に有効化"""
    # 元の設定を保存
    if "original_memory_enabled" not in st.session_state:
        st.session_state["original_memory_enabled"] = is_memory_enabled()
        st.session_state["original_read_enabled"] = is_memory_read_enabled()
    
    # Memory Bridgeの設定を一時的に上書き
    memory_bridge.config["enabled"] = True
    memory_bridge.config["read_enabled"] = True
    
    return True

# β版でメモリ有効化
enable_memory_for_beta()

# セッション終了時のGitHub同期フック設定（仕様書準拠）
try:
    if 'memory_sync_hook_registered' not in st.session_state:
        st.session_state['memory_sync_hook_registered'] = True
        setup_session_end_hook()  # atexitベースのフック設定
        logger.info("Memory sync hook registered for Memory Chat β")
except Exception as e:
    logger.warning(f"Failed to register session end hook: {e}")

# 現在のメモリ状態を表示
st.subheader("📊 現在のメモリ状態 (Lv2)")

try:
    current_memory = load_current_memory()
    
    # メモリの概要表示
    col1, col2, col3 = st.columns(3)
    
    with col1:
        active_projects = current_memory.get("current_memory", {}).get("active_projects", [])
        st.metric("アクティブプロジェクト", len(active_projects))
    
    with col2:
        events = current_memory.get("events", [])
        st.metric("直近イベント", len(events))
    
    with col3:
        last_updated = current_memory.get("last_updated", "未更新")
        if last_updated != "未更新":
            last_updated = last_updated[:19].replace('T', ' ')  # YYYY-MM-DD HH:MM:SS
        st.metric("最終更新", last_updated)
    
    # 詳細メモリ表示（展開可能）
    with st.expander("🔍 詳細メモリ内容", expanded=False):
        st.json(current_memory)
    
    # メモリコンテキスト（AI用）
    with st.expander("🤖 AI用コンテキスト", expanded=False):
        context = get_context_for_ai(max_events=10)
        if context:
            st.markdown(context)
        else:
            st.write("まだコンテキストがありません")

except Exception as e:
    st.error(f"メモリの読み込みに失敗しました: {e}")
    current_memory = None

# チャット履歴の初期化
if "memory_chat_history" not in st.session_state:
    st.session_state["memory_chat_history"] = []

# チャット履歴の表示
st.subheader("💬 Memory Chat")

if st.session_state["memory_chat_history"]:
    for msg in st.session_state["memory_chat_history"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

# チャット入力
user_input = st.chat_input("メッセージを入力してください（メモリ機能で文脈を記憶します）...")

if user_input:
    # ユーザーメッセージを履歴に追加
    st.session_state["memory_chat_history"].append({"role": "user", "content": user_input})
    
    # ユーザーメッセージを表示
    with st.chat_message("user"):
        st.markdown(user_input)
    
    # メモリにイベントをログ
    try:
        log_event("user_message", f"Memory Chat: {user_input}", importance="medium")
    except Exception as e:
        st.warning(f"メモリログに失敗: {e}")
    
    # AIレスポンスの生成
    with st.chat_message("assistant"):
        with st.spinner("メモリを参照して回答を生成中..."):
            try:
                # メモリコンテキストを取得
                memory_context = get_context_for_ai(max_events=10)
                
                # AI Project Manager を初期化
                if "ai_project_manager" not in st.session_state:
                    st.session_state["ai_project_manager"] = create_ai_project_manager(api_key)
                
                ai_pm = st.session_state["ai_project_manager"]
                
                # メモリコンテキスト付きでプロンプトを構築
                system_prompt = f"""あなたはKai VPMの個人秘書Ariadeです。ユーザーとの会話履歴と重要な情報を記憶して、一貫性のある回答を提供してください。

【記憶している情報】
{memory_context if memory_context else "まだ記憶している情報はありません"}

以下の点を重視してください：
1. 過去の会話内容を参考にして文脈に沿った回答をする
2. プロジェクトの進捗や状況を把握している場合は具体的に言及する
3. ユーザーの好みや過去の要求を考慮する
4. 自然で親しみやすい日本語で応答する
"""

                # OpenAI APIを使用してレスポンス生成
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_input}
                ]
                
                # GPT-4.1を使用（CLAUDE.mdの要求に従う）
                response = create_chat_completion(
                    model=get_openai_model(),
                    messages=messages,
                    max_tokens=1000,
                    temperature=0.7
                )
                
                assistant_reply = response.choices[0].message.content
                
                # レスポンスを表示
                st.markdown(assistant_reply)
                
                # アシスタントメッセージを履歴に追加
                st.session_state["memory_chat_history"].append({
                    "role": "assistant", 
                    "content": assistant_reply
                })
                
                # メモリにアシスタントレスポンスをログ
                try:
                    log_event("system", f"Memory Chat回答: {assistant_reply[:100]}...", importance="medium")
                except Exception as e:
                    st.warning(f"回答のメモリログに失敗: {e}")
                    
            except Exception as e:
                error_msg = f"AI回答の生成に失敗しました: {e}"
                st.error(error_msg)
                
                # エラーもメモリにログ
                try:
                    log_event("error", f"Memory Chat error: {str(e)}", importance="high")
                except Exception:
                    pass
    
    # メモリ更新後の状態を再表示
    st.rerun()

# デバッグ・管理機能
st.subheader("🔧 デバッグ・管理")

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("🔄 メモリ状態を更新", help="最新のメモリ状態を再読み込み"):
        st.rerun()

with col2:
    if st.button("🗑️ チャット履歴をクリア", help="このページのチャット履歴のみクリア"):
        st.session_state["memory_chat_history"] = []
        st.success("チャット履歴をクリアしました")
        st.rerun()

with col3:
    if st.button("📝 テストイベント追加", help="テスト用のイベントをメモリに追加"):
        try:
            log_event("system", f"Memory Chat βテスト - {datetime.now().strftime('%H:%M:%S')}", importance="low")
            st.success("テストイベントを追加しました")
            st.rerun()
        except Exception as e:
            st.error(f"テストイベントの追加に失敗: {e}")

# Stage B 実装状況の表示
st.subheader("📋 Stage B 実装状況")

implementation_status = {
    "✅ Memory Chat ページ作成": True,
    "✅ フィーチャーフラグ一時的有効化": True,
    "✅ メモリコンテキストの読み取り": True,
    "✅ AI プロンプトへのメモリ注入": True,
    "✅ 会話イベントのメモリログ": True,
    "⏳ GitHub自動同期": False,  # 後で実装
    "⏳ 本格的なテスト": False   # 後で実行
}

for item, status in implementation_status.items():
    if status:
        st.write(item)
    else:
        st.write(item)

# サイドバーに統計とツール表示
with st.sidebar:
    st.subheader("📊 LLM使用統計")
    
    try:
        llm_stats = render_llm_stats_for_memory_chat()
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("本日のコール数", llm_stats["calls_today"])
            st.metric("総トークン数", f"{llm_stats['total_tokens']:,}")
        
        with col2:
            st.metric("推定コスト", llm_stats["estimated_cost"])
            st.metric("平均レスポンス", llm_stats["avg_latency"])
    
    except Exception as e:
        st.error(f"LLM統計の取得に失敗: {e}")
    
    # LLM Call Logs詳細表示（仕様書準拠）
    st.divider()
    st.subheader("📋 LLM Call Logs")
    
    try:
        recent_calls = get_recent_llm_calls(limit=5)
        
        if recent_calls:
            for i, call in enumerate(recent_calls):
                with st.expander(f"📞 Call {i+1}: {call['model']} ({call['prompt_tokens']}+{call['completion_tokens']} tokens)", expanded=False):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**時刻**: {call['timestamp'][:19].replace('T', ' ')}")
                        st.write(f"**レスポンス時間**: {call['latency_ms']:.1f}ms")
                        st.write(f"**タスクID**: {call['task_id']}")
                    
                    with col2:
                        st.write(f"**モデル**: {call['model']}")
                        st.write(f"**トークン**: {call['prompt_tokens']} + {call['completion_tokens']}")
                    
                    st.write("**プロンプト（messages）**:")
                    st.markdown(format_messages_for_display(call['messages']))
                    
                    st.write("**レスポンス**:")
                    response_text = call['response']
                    if len(response_text) > 300:
                        st.markdown(f"{response_text[:300]}...")
                        if st.button(f"全文表示 {i+1}", key=f"full_response_{i}"):
                            st.markdown(response_text)
                    else:
                        st.markdown(response_text)
        else:
            st.write("まだLLM呼び出しログがありません")
            
    except Exception as e:
        st.error(f"LLM Call Logs表示エラー: {e}")
    
    st.divider()
    st.subheader("🔄 GitHub同期")
    
    if st.button("📤 メモリをGitHubに同期", help="現在のメモリ状態をGitHubに同期"):
        try:
            with st.spinner("GitHub同期中..."):
                success, message = manual_memory_sync()
                if success:
                    st.success(message)
                else:
                    st.error(message)
        except Exception as e:
            st.error(f"同期エラー: {e}")
    
    st.caption("💡 セッション終了時に自動同期")

# フッター
st.divider()
st.caption("Memory Chat β - Memory Layer Phase 2 Stage B | フィーチャーフラグにより本番環境では無効")