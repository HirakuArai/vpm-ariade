"""
Memory Chat β - Memory Layer Phase 2 Stage B
メモリレイヤーの読み書き機能検証ページ
"""

import streamlit as st
import json
import os
import sys
import logging
from datetime import datetime, timezone
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
    from core.memory_bridge import memory_bridge, log_event, load_current_memory, get_context_for_ai, update_memory_with_llm
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
            last_updated = last_updated[:19].replace('T', ' ') + " UTC"  # YYYY-MM-DD HH:MM:SS UTC
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
                # デバッグ出力を一時的に無効化（会話表示の問題を修正）
                # st.write("🔍 Debug: LLMコール実行中...")
                # st.write(f"  - Model: {get_openai_model()}")
                # st.write(f"  - Messages: {len(messages)}件")
                
                response = create_chat_completion(
                    model=get_openai_model(),
                    messages=messages,
                    max_tokens=8000,
                    temperature=0.7
                )
                
                # st.write("✅ Debug: LLMコール完了")
                
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
                
                # 記憶をLLMで更新（N+1パッチ生成）
                try:
                    with st.spinner("記憶を更新中..."):
                        # st.write("🔍 Debug: Memory Update LLMコール実行中...")
                        
                        memory_patch = update_memory_with_llm(
                            user_message=user_input,
                            assistant_response=assistant_reply,
                            memory_context=memory_context
                        )
                        if memory_patch:
                            logger.info(f"Memory updated with patch: {memory_patch[:100]}...")
                            
                            # 記憶更新後に即座にGitHub同期を実行（仕様書準拠）
                            try:
                                with st.spinner("GitHub同期中..."):
                                    sync_success, sync_message = manual_memory_sync()
                                    if sync_success:
                                        logger.info("Memory synced to GitHub after conversation")
                                    else:
                                        logger.warning(f"Memory sync failed: {sync_message}")
                            except Exception as sync_error:
                                logger.error(f"GitHub同期エラー: {sync_error}")
                        else:
                            logger.warning("Memory update returned no patch")
                except Exception as e:
                    logger.error(f"記憶の更新に失敗: {e}")
                    # エラーが発生してもユーザー体験を損なわないよう、警告は表示しない
                    
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
    
    # LLM Call Logs詳細表示（仕様書準拠・kind別表示）
    st.divider()
    st.subheader("📋 LLM Call Logs")
    
    try:
        # 最新のログを取得して読み込み（直接ファイルを読んでkind情報を含める）
        from pathlib import Path
        import json
        from datetime import datetime
        
        log_file = Path("logs/llm") / f"{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.jsonl"
        recent_entries = []
        
        if log_file.exists():
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # 最新10件を取得
            for line in reversed(lines[-10:]):
                if line.strip():
                    try:
                        entry = json.loads(line.strip())
                        recent_entries.append(entry)
                    except json.JSONDecodeError:
                        continue
        
        if recent_entries:
            # kind別にグループ化
            chat_calls = []
            memory_updates = []
            
            for entry in recent_entries:
                if entry.get("kind") == "memory_update":
                    memory_updates.append(entry)
                else:
                    chat_calls.append(entry)
            
            # 会話応答の表示
            if chat_calls:
                st.markdown("### 💬 会話応答 (ui_chat)")
                for i, entry in enumerate(chat_calls[:3]):  # 最新3件
                    icon = "🟢" if not entry.get("error") else "🔴"
                    with st.expander(f"{icon} {entry.get('model', 'unknown')} | {entry.get('ts', '')[:19].replace('T', ' ')} UTC", expanded=False):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write(f"**Tokens**: {entry.get('prompt_tokens', 0)} + {entry.get('completion_tokens', 0)}")
                            st.write(f"**Latency**: {entry.get('request', {}).get('latency_ms', 0):.1f}ms")
                        
                        with col2:
                            st.write(f"**Task ID**: {entry.get('task_id', 'N/A')}")
                            st.write(f"**Subkind**: {entry.get('subkind', 'N/A')}")
                        
                        # メッセージ表示
                        messages = entry.get("request", {}).get("messages", [])
                        if messages:
                            st.write("**プロンプト**:")
                            st.markdown(format_messages_for_display(messages))
                        
                        # レスポンス表示
                        response_content = entry.get("response", {}).get("content", "")
                        if response_content:
                            st.write("**レスポンス**:")
                            if len(response_content) > 200:
                                st.markdown(f"{response_content[:200]}...")
                            else:
                                st.markdown(response_content)
            
            # 記憶更新の表示
            if memory_updates:
                st.markdown("### 🧠 記憶更新 (memory_update)")
                for i, entry in enumerate(memory_updates[:2]):  # 最新2件
                    icon = "🟣" if not entry.get("error") else "🔴"
                    with st.expander(f"{icon} N+1パッチ生成 | {entry.get('ts', '')[:19].replace('T', ' ')} UTC", expanded=False):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write(f"**Tokens**: {entry.get('prompt_tokens', 0)} + {entry.get('completion_tokens', 0)}")
                            st.write(f"**Latency**: {entry.get('request', {}).get('latency_ms', 0):.1f}ms")
                        
                        with col2:
                            st.write(f"**Task ID**: {entry.get('task_id', 'N/A')}")
                            st.write(f"**Subkind**: {entry.get('subkind', 'N/A')}")
                        
                        # 記憶パッチ表示
                        response_content = entry.get("response", {}).get("content", "")
                        if response_content:
                            st.write("**生成された記憶パッチ**:")
                            try:
                                patch_json = json.loads(response_content)
                                st.json(patch_json)
                            except:
                                st.markdown(f"```json\n{response_content[:300]}...\n```")
            
            # 統計サマリー
            st.markdown("### 📊 サマリー")
            total_calls = len(recent_entries)
            memory_update_count = len(memory_updates)
            chat_count = len(chat_calls)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("総コール数", total_calls)
            with col2:
                st.metric("会話応答", chat_count)
            with col3:
                st.metric("記憶更新", memory_update_count)
            
        else:
            st.write("まだLLM呼び出しログがありません")
            
        # セッション状態のフォールバックログ表示
        if 'llm_call_logs' in st.session_state and st.session_state['llm_call_logs']:
            st.markdown("### ⚠️ セッション状態のログ（ファイル保存失敗時のフォールバック）")
            for i, log in enumerate(st.session_state['llm_call_logs']):
                st.write(f"{i+1}. {log['timestamp']} - {log['model']} ({log['kind']}) - {log['tokens']} tokens")
                if log.get('error'):
                    st.error(f"   エラー: {log['error']}")
            
    except Exception as e:
        st.error(f"LLM Call Logs表示エラー: {e}")
    
    st.divider()
    st.subheader("🔍 LLM Call Logs デバッグ")
    
    # LLMログファイル確認
    from pathlib import Path
    from datetime import datetime
    
    log_dir = Path("logs/llm")
    today_file = log_dir / f"{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.jsonl"
    
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**ログディレクトリ**: {log_dir}")
        st.write(f"**ディレクトリ存在**: {log_dir.exists()}")
        if log_dir.exists():
            files = list(log_dir.glob("*.jsonl"))
            st.write(f"**ファイル数**: {len(files)}")
            for f in files:
                st.write(f"  - {f.name} ({f.stat().st_size} bytes)")
    
    with col2:
        st.write(f"**今日のファイル**: {today_file.name}")
        st.write(f"**ファイル存在**: {today_file.exists()}")
        if today_file.exists():
            st.write(f"**ファイルサイズ**: {today_file.stat().st_size} bytes")
            # 最新行を表示
            try:
                with open(today_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                st.write(f"**エントリ数**: {len(lines)}行")
                if lines:
                    import json
                    last_entry = json.loads(lines[-1])
                    st.write(f"**最新エントリ**: {last_entry.get('ts')} - {last_entry.get('kind')}")
            except Exception as e:
                st.error(f"ファイル読み込みエラー: {e}")
    
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