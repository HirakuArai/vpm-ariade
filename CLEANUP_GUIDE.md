# 🧹 VPM-Ariade レジリエント・クリーンアップガイド

このガイドでは、中断・再開可能な段階的クリーンアップシステムの使い方を説明します。

## 🎯 概要

**レジリエント設計の特徴：**
- ✅ 各段階で自動バックアップ
- ✅ 中断後の完全復旧可能  
- ✅ 段階別ロールバック
- ✅ 実行前後の自動検証
- ✅ Git履歴完全保持

## 🚀 基本使用方法

### 1. **新規クリーンアップ開始**
```bash
python cleanup_manager.py start
```

### 2. **中断後の再開**
```bash
python cleanup_manager.py resume
```

### 3. **現在状況確認**
```bash
python cleanup_manager.py status
```

### 4. **完全ロールバック**
```bash
python cleanup_manager.py rollback
```

### 5. **特定段階のみ実行**
```bash
python cleanup_manager.py stage 3
```

## 📋 クリーンアップ段階

| 段階 | 処理内容 | 安全性 | 復旧方法 |
|-----|---------|-------|---------|
| **1** | 完全バックアップ作成 | 🟢 完全安全 | 自動 |
| **2** | アーカイブブランチ作成 | 🟢 完全安全 | `git branch -D` |
| **3** | 外部ツール移動 | 🟡 低リスク | `git checkout HEAD -- tools/` |
| **4** | ルートテスト移動 | 🟡 低リスク | `git checkout HEAD -- test_*.py` |
| **5** | 会話ログ移動 | 🟢 完全安全 | `git checkout HEAD -- conversations/` |
| **6** | 生成データ移動 | 🟢 完全安全 | `git checkout HEAD -- data/` |
| **7** | スクリプト移動 | 🟡 低リスク | `git checkout HEAD -- scripts/` |
| **8** | 無効ページ移動 | 🟡 低リスク | `git checkout HEAD -- disabled_pages/` |
| **9** | 重複文書整理 | 🟢 完全安全 | `git checkout HEAD -- docs/` |
| **10** | 最終検証 | 🟢 完全安全 | 自動 |

## 🛡️ 安全機能

### **自動バックアップ**
- Git tagで履歴ポイント作成
- 外部完全コピー作成
- 各段階後にコミット

### **段階別検証**
```bash
# 各段階で自動実行される検証
- git status          # Git状態確認
- python -c 'import app'  # アプリ起動確認
- streamlit run app.py --check-toml  # UI確認
- pytest tests/ -v    # テスト実行
```

### **ロールバック戦略**
```bash
# 段階別ロールバック
git checkout HEAD -- [対象ファイル]

# 完全ロールバック  
git reset --hard backup_YYYYMMDD_HHMMSS
```

## 💾 状態ファイル (`cleanup_state.json`)

```json
{
  "cleanup_session": {
    "session_id": "abc12345",
    "started_at": "2025-01-15T10:30:00",
    "current_stage": 5,
    "completed_stages": [1, 2, 3, 4],
    "failed_stages": []
  },
  "stages": [...]
}
```

## 🚨 緊急時対応

### **1. システムクラッシュ時**
```bash
# 状況確認
python cleanup_manager.py status

# 中断点から再開
python cleanup_manager.py resume
```

### **2. 段階失敗時**
```bash
# 該当段階のみロールバック
git checkout HEAD -- [問題ファイル]

# 特定段階から再実行
python cleanup_manager.py stage [段階番号]
```

### **3. 完全復旧が必要な場合**
```bash
# 全体ロールバック
python cleanup_manager.py rollback

# 外部バックアップから復旧
cp -r ../vpm_backup_YYYYMMDD_HHMMSS/* .
```

## 📊 実行例

### **正常実行例**
```bash
$ python cleanup_manager.py start
🚀 Started cleanup session: abc12345
📦 Creating backup: vpm_backup_20250115_103000
✅ Backup created at ../vpm_backup_20250115_103000
🚀 Executing stage 1: pre_cleanup_backup
✅ Stage 1 completed successfully
🚀 Executing stage 2: create_archive_branch
📁 Created: archive/tools
📁 Created: archive/tests
✅ Stage 2 completed successfully
...
🎉 Cleanup process completed successfully!
```

### **中断・再開例**
```bash
$ python cleanup_manager.py start
# ... 段階3まで実行後にCtrl+C

$ python cleanup_manager.py status
📊 Cleanup Status
Session ID: abc12345
Current Stage: 4
Completed: [1, 2, 3]
Failed: []

$ python cleanup_manager.py resume
🔄 Resuming cleanup session: abc12345
📋 Progress: 4/10
🚀 Executing stage 4: archive_root_tests
...
```

## ⚠️ 注意事項

1. **実行前準備**
   - 未コミット変更をコミット
   - 外部バックアップを推奨
   - 十分なディスク容量確保

2. **実行中**
   - 各段階で動作確認
   - 異常時は即座に中断
   - ログを定期確認

3. **実行後**
   - アプリ動作確認
   - アーカイブ内容確認
   - 不要バックアップ削除

## 🎯 期待される結果

**クリーンアップ前:** 約500ファイル
**クリーンアップ後:** 約100ファイル（80%削減）

**保持されるもの:**
- コア機能（app.py + core/）
- 現在の設定・データ
- 重要なドキュメント

**アーカイブされるもの:**
- 外部ツール・テスト
- 生成データ・ログ
- 実験的機能・重複文書