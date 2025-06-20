# 会話記録とプロジェクト情報更新システム

## 仕組みの概要

Kai VPMでは、ユーザーとの会話を自動的に記録し、その内容からプロジェクトの更新情報を抽出する二段階のシステムを使用しています。

## 1. 会話記録システム

### 1.1 グローバル会話ログ
- **場所**: `conversations/conversation_YYYYMMDD.json`
- **目的**: システム全体の会話履歴を日付別に保存
- **形式**: JSON形式で、role（user/assistant）、content、timestampを記録

### 1.2 プロジェクト固有会話ログ
- **場所**: `data/conversations/{project_id}/YYYYMMDD.jsonl`
- **目的**: 各プロジェクトに関連する会話のみを分離して保存
- **形式**: JSONL形式で、project_id付きでline-by-line記録

### 1.3 記録タイミング
```python
# ユーザー入力時
_append_log("user", user_input)
_append_project_log(current_project_id, "user", user_input)

# AI応答時
_append_log("assistant", assistant_reply)
_append_project_log(current_project_id, "assistant", assistant_reply)
```

## 2. プロジェクト情報更新システム

### 2.1 AutoUpdateEngine（現在は無効化）
- **目的**: 会話内容から自動的にプロジェクト情報を抽出・更新
- **問題**: 会話の断片を意味のないタスクとして登録してしまう
- **現状**: 一時的に無効化（信頼度閾値を0.8に引き上げ、厳格な検証を追加）

### 2.2 手動更新候補システム（現在使用中）
```python
# 会話から新情報を抽出
new_data = extract_new_data_from_chat(combined_content, project_id)

# 更新候補を生成
candidates = generate_update_candidates(project_id, new_data)

# バリデーション後、ユーザーに承認を求める
valid_candidates = [c for c in candidates if validate_update_candidate(c)]
```

### 2.3 更新候補の表示と承認
- UIで更新候補を表示
- ユーザーが承認・拒否を選択
- 承認された場合のみプロジェクトデータを更新

## 3. 現在の問題と対策

### 3.1 発生していた問題
- AutoUpdateEngineが「は以下の通りです。」「を追加してよろしいですか」などの会話断片をタスクとして誤認識
- 22件の無効なタスクがプロジェクトに追加されていた

### 3.2 実施した対策
1. **データクリーンアップ**: 無効なタスクを削除
2. **バリデーション強化**: `_is_valid_task_description()`メソッドを追加
3. **パターン厳格化**: 正規表現パターンをより具体的に修正
4. **信頼度閾値引き上げ**: 0.7 → 0.8に変更

### 3.3 追加のバリデーション
```python
def _is_valid_task_description(self, description: str) -> bool:
    # 最小長チェック（3文字以上）
    # 無効パターン除外（助詞のみ、記号のみ、質問文の一部など）
    # 意味のある内容チェック（動詞・名詞が含まれているか）
```

## 4. 改善計画

### 4.1 短期的改善
- [ ] AutoUpdateEngineの完全なテストとデバッグ
- [ ] より精密な自然言語処理の導入
- [ ] ユーザーフィードバックに基づく学習機能

### 4.2 長期的改善
- [ ] 機械学習による意図理解の向上
- [ ] コンテキスト理解の強化
- [ ] 多言語対応の会話解析

## 5. 使用方法

### 5.1 現在の推奨フロー
1. 通常通り会話を行う
2. 更新候補が表示された場合、内容を確認
3. 適切な候補のみ承認
4. 不適切な候補は拒否

### 5.2 デバッグ時の確認ポイント
- プロジェクト固有ログファイルの存在確認
- 更新候補のバリデーション結果
- AutoUpdateEngineのエラーログ