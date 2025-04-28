# project_status.md

最終更新日: 2025-04-29  
バージョン: 1.4（自己認識PoC完了＋本番環境動作安定）

## ■ 全体概要・進捗率：70%程度
- Kaiの自己認識PoCフェーズ（kai_capabilities.json参照による自己紹介機能）を完了
- capabilities_registry.pyを実装し、Kaiの能力定義をコードレベルで管理開始
- feat/decorator-annotationsブランチ開発→mainブランチマージ完了
- Streamlit Cloud本番環境への反映・動作確認完了
- 今後の「自己更新提案機能」「環境移行」フェーズに向けた設計準備着手

---

## ■ タスク一覧（更新版）

| タスクID | 内容                                                 | 状況       |
|----------|------------------------------------------------------|------------|
| T001     | Function Calling による文脈判断の拡張                | 未着手     |
| T002     | 大規模ログ整形・RAGテスト                           | 一時停止中 |
| T004     | セキュリティ要件整理                                | 未着手     |
| T005     | Kaiの自己改修機構整備（Step 3〜6）                   | ✅完了     |
| T006     | UI整備プロトタイプ化（提案UI改善）                   | 進行中     |
| T007     | Kai自己認識機能（capabilities_registry導入＋自己紹介安定化） | ✅完了     |
| T008     | 正規リスト回答モード実装（capabilities.json完全準拠） | 未着手     |
| T009     | discover_capabilities機能設計（自己更新提案）         | 未着手     |

---

## ■ 進行中の改善・検討ポイント

- Kaiの自己認識モード強化（capabilities.jsonベースの厳密回答モード開発予定）
- Streamlit Cloud無料プランの制約（複数Privateアプリ不可）対応：main本番運用中
- Hugging Face Spaces移行を前提としたパス設計・Secrets管理の整理開始

---

## ■ 直近の改善提案・反映内容（履歴）

- capabilities_registry.py導入と最小デコレータ設計確立
- try_git_commit関数にkai_capabilityデコレータ適用
- project_status.mdに進捗記録フェーズを整理統合

---

## ■ 今後のマイルストン（暫定更新版）

| 日付        | 目標                                      |
|-------------|-------------------------------------------|
| 2025-05-01  | 正規リスト回答モード（T008）プロトタイプ完成  |
| 2025-05-05  | discover_capabilities構想ドラフト完成       |
| 2025-05-10  | Hugging Face Spaces移行方針正式決定         |

---

## ■ コメント

- Kai の自己認識PoC完了により、本格的な「自己更新提案」フェーズへ移行準備完了。
- 今後はStreamlit Cloud本番運用を続けながら、Spaces移行も視野にシステム構成を整理する。
- 小さな積み上げを重視し、PoCフェーズから安定運用フェーズへの移行をスムーズに進める。
