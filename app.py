"""
Kai VPM v2 - Main Landing Page
AI Project Manager with Charter-driven Workflow
"""

import streamlit as st

# Set page config as the very first Streamlit command
st.set_page_config(
    page_title="Kai VPM v2 - AIプロジェクトマネージャー",
    page_icon="🌟",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Main landing page content
st.title("🌟 Kai VPM v2")
st.markdown("## AIプロジェクトマネージャー")

st.markdown("""
**Kai VPM v2**へようこそ - あなたのアイデアを構造化された実行可能なプロジェクト計画に変換するインテリジェントなプロジェクト管理システムです。

### 🚀 はじめに

サイドバーを使用してプロジェクトワークフローを進めてください：

1. **📝 新規プロジェクト** - ガイド付きの質問を通じてプロジェクトチャーターを作成
2. **✏️ チャーター確認** - チャーターの詳細を確認・編集  
3. **🧠 分析とWBS** - AI による分析と作業分解構造の生成

### ✨ 主要機能

- **チャーター駆動アプローチ**: すべてのプロジェクトが明確なチャーターから始まります
- **AI ペルソナ分析**: インテリジェントな優先順位付けとリスク評価
- **作業分解構造**: 依存関係を持つ自動タスク生成
- **インタラクティブ編集**: すべてのプロジェクト要素に対応したリッチデータエディター
- **エクスポート・保存**: 外部利用のための完全なプロジェクトデータエクスポート

### 🔄 ワークフロー概要

```
チャーター作成 → 確認・編集 → AI分析 → WBS生成 → エクスポート
```

### 🎯 メリット

- **構造化された計画**: すべてのプロジェクトが明確な範囲と目標を持つことを保証
- **リスク認識**: AIがプロセスの早い段階で潜在的な問題を特定
- **タスク組織化**: 適切な依存関係を持つ現実的なタイムラインを生成
- **コラボレーション**: すべてのプロジェクト要素の簡単な確認と編集

---

**始める準備はできましたか？** サイドバーメニューからページを選択してプロジェクトの旅を始めましょう！
""")

# Show system status
with st.expander("🔧 システム状態", expanded=False):
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("コアモジュール", "✅ 稼働中")
        st.caption("persona_core, planning_core")
    
    with col2:
        st.metric("データストレージ", "✅ 準備完了")
        st.caption("charters/, results/")
    
    with col3:
        st.metric("UIフレームワーク", "✅ マルチページ")
        st.caption("Native Streamlit routing")

# Footer
st.markdown("---")
st.markdown("*Kai VPM v2 - 冪等性・自己進化型AIプロジェクトマネージャー*")