# UI再設計提案書
## 階層的ナビゲーション導入

作成日: 2025-06-22
提案者: Claude (AI Assistant)

---

## 🎯 設計方針

### 基本原則
1. **階層的情報アクセス**: プロジェクト → サブ機能の明確な流れ
2. **サイドバー中心設計**: 左カラムでの統合ナビゲーション
3. **専用ページ分離**: 各機能に特化したレイアウト
4. **視覚的明確性**: 選択状態の明示とコンテキスト表示

---

## 🏗️ 新しいUI構造

### 左サイドバー構成

```
Kai VPM
├── 💬 メインチャット
├── ➕ プロジェクト作成
├── ─────────────────
├── 📋 プロジェクトリスト
│   ├── 🏔️ 八ヶ岳登山計画 ●     ← 選択中
│   │   ├── 💬 チャット
│   │   ├── 📊 情報収集状況
│   │   ├── 🗺️ フェーズ進捗
│   │   └── 📜 会話履歴
│   ├── 🏢 新入社員研修
│   └── 💻 Webアプリ開発
└── ⚙️ システム設定
```

### メインエリア表示

#### パターン1: プロジェクト未選択
```
┌─ メインエリア ─────────────────┐
│ 🎯 Kai Virtual Project Manager │
│                                │
│ プロジェクトを選択してください    │
│ ← 左のプロジェクトリストから     │
│   選択してください               │
└──────────────────────────────┘
```

#### パターン2: プロジェクト選択済み（チャット）
```
┌─ メインエリア ─────────────────┐
│ 🏔️ 八ヶ岳登山計画 > 💬 チャット │
│                                │
│ [会話履歴]                      │
│ [質問カード]                    │
│ [入力欄]                        │
└──────────────────────────────┘
```

#### パターン3: 情報収集状況ページ
```
┌─ メインエリア ─────────────────┐
│ 🏔️ 八ヶ岳登山計画 > 📊 情報収集 │
│                                │
│ [プログレスサークル]            │
│ [フィールドカード一覧]          │
│ [未完了項目ハイライト]          │
└──────────────────────────────┘
```

---

## 🎨 実装方針

### 1. サイドバー改良

#### 階層的プロジェクトリスト
```python
# サイドバー構造
with st.sidebar:
    st.title("Kai VPM")
    
    # 基本機能
    if st.button("💬 メインチャット"):
        st.session_state["current_view"] = "main_chat"
    
    if st.button("➕ プロジェクト作成"):
        st.session_state["current_view"] = "create_project"
    
    st.divider()
    
    # プロジェクトリスト
    st.subheader("📋 プロジェクト")
    
    for project in projects:
        # プロジェクト選択
        is_selected = (project.id == selected_project_id)
        
        if st.button(
            f"{'●' if is_selected else '○'} {project.name}",
            key=f"proj_{project.id}"
        ):
            st.session_state["selected_project"] = project.id
        
        # サブメニュー（選択中のプロジェクトのみ）
        if is_selected:
            with st.container():
                st.write("　　├── 💬 チャット")
                st.write("　　├── 📊 情報収集")
                st.write("　　├── 🗺️ フェーズ進捗")
                st.write("　　└── 📜 会話履歴")
```

### 2. 専用ページ作成

#### pages/project_info.py
```python
# プロジェクト情報収集状況専用ページ
def render_project_info_page(project_id):
    st.header(f"📊 {project_name} - 情報収集状況")
    
    # フルサイズでの視覚化
    ProjectVisualization.render_schema_progress(schema)
    ProjectVisualization.render_field_cards(schema)
    
    # アクション
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 情報を更新"):
            # 更新処理
    with col2:
        if st.button("📝 手動入力"):
            # 手動入力モーダル
```

#### pages/project_phase.py
```python
# フェーズ進捗専用ページ
def render_phase_page(project_id):
    st.header(f"🗺️ {project_name} - フェーズ進捗")
    
    # 大きなフェーズ表示
    StatusIndicators.render_phase_progression(current_phase, progress)
    
    # 詳細情報
    render_phase_details()
    render_phase_actions()
```

### 3. 状態管理

#### セッション状態構造
```python
st.session_state = {
    "selected_project": "proj-20250618-075700-122",
    "current_view": "project_chat",  # main_chat, project_info, project_phase, etc.
    "sidebar_expanded": True,
    "project_context": {...}
}
```

---

## 🚀 実装ステップ

### Phase 1: サイドバー改良
- [ ] 階層的プロジェクトリスト実装
- [ ] プロジェクト選択状態の視覚化
- [ ] サブメニューナビゲーション

### Phase 2: 専用ページ分離
- [ ] プロジェクト情報収集ページ作成
- [ ] フェーズ進捗ページ作成
- [ ] 会話履歴ページ作成

### Phase 3: ルーティング統合
- [ ] ページ遷移システム実装
- [ ] 状態管理の統一
- [ ] ブレッドクラム表示

### Phase 4: UX最適化
- [ ] アニメーション効果追加
- [ ] キーボードショートカット
- [ ] 応答性改善

---

## 📊 期待される改善効果

### ユーザビリティ
- **ナビゲーション効率**: 3クリック以内でアクセス
- **情報発見性**: 階層的構造で直感的
- **専門機能活用**: 各機能に最適化されたレイアウト

### 開発効率
- **コンポーネント再利用**: 専用ページで再利用性向上
- **保守性**: 機能分離で保守が容易
- **拡張性**: 新機能追加が容易

### パフォーマンス
- **読み込み速度**: 必要な情報のみ表示
- **メモリ使用量**: ページ分離で軽量化
- **応答性**: 専用レイアウトで高速表示

---

## 🎯 次のアクション

この設計に同意いただけましたら、以下の順序で実装を進めます：

1. **サイドバー改良** (1-2時間)
2. **専用ページ作成** (2-3時間) 
3. **統合テスト** (1時間)

合計所要時間: 約4-6時間

---

*この提案について、追加の要望や修正点がございましたらお聞かせください。*