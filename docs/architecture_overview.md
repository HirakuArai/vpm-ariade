---

doc_type: "architecture_overview"
required_capabilities:

* "read_doc"

---

# architecture_overview.md

【本ドキュメントは Kai VPM システムの**全体構成・フェーズ・運用フロー**を記述する補助ドキュメントです。Kai は設計判断や背景説明を行う際に本書を参照しますが、能力説明の根拠はあくまで base_os_rules.md と integrated_dsl.jsonl が優先されます。】

---

## 1. 全体アーキテクチャ概要

```mermaid
flowchart TD
  U[ユーザー] -->|Chat| ChatUI[Streamlit Kai Chat Core]
  ChatUI -->|差分要求| Checker[ Kai Self-Checker ]
  Checker -->|gap_report.json| Updater[ Kai Doc‑Updater ]
  Updater -->|proposed_dsl.json| Approval[ handle_approval ✋ ]
  Approval -->|merge| DSL[integrated_dsl.jsonl]
  Updater -->|docs更新| Git[ GitHub Repo ]
  Git --> Nightly[Nightly Reality Scan CI]
  Nightly -->|差分ゼロ?|
  ChatUI <-- Git
```

* **Kai Chat Core**: ユーザー対話、回答生成
* **Kai Self-Checker**: AST ↔ DSL ↔ Docs ギャップ検出
* **Kai Doc‑Updater**: GPT 提案 → 承認 → マージ
* **handle_approval**: 人間承認機能
* **Nightly Reality Scan**: GitHub Actions で差分ゼロ確認 & 自動PR

## 2. ディレクトリ構成

```
/ (repo root)
 ├─ app.py                         # Streamlit UI (Chat Core)
 ├─ core/                          # 機能ライブラリ
 │    ├─ self_checker.py          # 差分検出
 │    ├─ doc_updater.py           # GPT提案→適用
 │    └─ ...
 ├─ docs/                          # OSルール・目的・構成 等
 ├─ dsl/                           # integrated_dsl.jsonl + README
 ├─ data/                          # gap_report.json / proposed_dsl.json
 ├─ logs/                          # conversation_YYYYMMDD.md
 └─ .github/workflows/             # CI/Nightly Scan
```

## 3. 運用フロー

1. **チャット対話** → Kai が回答 (OSルール＋DSL)
2. **Self-Check要求**: ユーザー or Nightly → `dsl_gap_report.json` 出力
3. **Doc-Updater**: GPT が差分をもとに `proposed_dsl.json` 生成
4. **人間承認** (`handle_approval`) → OK なら自動 merge → Git Commit
5. **Nightly Reality Scan**: 差分ゼロか確認。差分ありなら PR を自動作成

## 4. フェーズロードマップ（PoC → MVP → 拡張）

| フェーズ         | 主要成果物                          | 状態                  |
| ------------ | ------------------------------ | ------------------- |
| **PoC**      | 最小チャットUI + OSルール + DSL 全文プロンプト | ✅ 完了 (2025‑05‑18)   |
| **MVP-1**    | Self-Checker + gap_report UI  | ⬜ 進行中 (～2025‑06‑01) |
| **MVP-2**    | Doc-Updater (GPT提案→承認→Merge)   | ⬜ 計画 (～2025‑06‑15)  |
| **MVP-3**    | Nightly Reality Scan CI 完全自動化  | ⬜ 計画 (～2025‑07‑01)  |
| **Extended** | ダッシュボード, RISKS 可視化, Hook API   | ⬜ 後続                |

## 5. 依存サービス・ライブラリ

* **OpenAI GPT‑4o/3.5** (LLM)
* **GitHub** (リポジトリ / Actions CI)
* **Streamlit Cloud** (UIホスティング)
* **Mermaid.js** (構成図)

## 6. 変更履歴

| 日付         | 変更                             | 変更者     |
| ---------- | ------------------------------ | ------- |
| 2025‑05‑18 | Ariade A/B 人格記述を完全撤廃。機能ロール図へ刷新 | Kai チーム |
