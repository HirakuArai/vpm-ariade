---
doc_type: "architecture_overview"
required_capabilities:
  - "read_doc"
  - "append_to_log"       # 会話ログ保存
  - "git_push"            # 自動コミット／Push
  - "embed_logs"          # RAG 用ベクトル化（将来）
---

# アーキテクチャ概要 ― VPM‑Ariade PoC
> **最終更新日**: 2025‑05‑06

---
## 1. 本ドキュメントの目的
【本ドキュメントは Kai VPM システムの全体構成・フェーズ・運用フローを記述した補助ドキュメントです。
Kaiの設計的な判断や背景説明にはここを参照しますが、能力説明の根拠はあくまで DSL/OSルールが優先です。】

---
## 2. システム全体図（テキスト版）
```
User ─▶ Kai(UI) ─▶ OpenAI API
       │  ▲
       │  └── append_to_log → git add/commit/push → GitHub
       │                                         ▲
       │                                         │（Streamlit Cloud が自動デプロイ）
       └── get_system_prompt() が docs/** を読込
```
* **Kai** : ユーザーとのチャット UI。会話ログ保存・Git 操作も担当。
* **Ariade_A** : 会話ログを解析し、ドキュメント更新案を生成・コミット（将来拡張）。
* **Ariade_B** : Q&A／要約エンジン（将来拡張）。

---
## 3. フェーズ別ロードマップ（Kai 全体戦略）

| Phase | 目的 | 主な成果物・特徴 | 状態 |
|-------|------|------------------|------|
| **0. 準備** | ローカル環境構築・API連携 | `.env`, `app.py`, Streamlit 起動確認 | ✅ 完了 |
| **1. Git連携** | GitHub操作自動化・会話ログ記録 | `append_to_log()`, `try_git_commit()` | ✅ 完了 |
| **2. 会話UI PoC** | Kaiの初期UI＋会話保存・再現 | 会話履歴の復元、チャットUI | ✅ 完了 |
| **3. 自己診断ロジック構築** | AST ⇄ JSON ⇄ GPT 比較と整合性分類 | `run_kai_self_check()`・🟣/🔵/🟡/🔶分類 | ✅ 完了 |
| **4. UI整備** | ユーザー向け視認性・入力性強化 | 開発者モードUI、色・ラベル改善 | ⏳ 開始 |
| **5. 自動ループ構築** | 差分 → 優先度 → 提案 → 実装の循環 | `task_selector`, `capability_proposal` | 🔜 5月中予定 |
| **6. PoC完成** | 安定動作・成果評価・MVP判断 | 指名管理・バージョン復元・自律サイクル | 🗓 5月末目標 |


---
## 4. ディレクトリ構成（ルート直下）
| パス | 種別 | 役割 |
|------|------|------|
| **app.py** | 実行スクリプト | Kai の UI・会話処理・Git 自動 push |
| **docs/** | 常時参照型 | プロジェクト定義・ベース OS・本ファイル など |
| **conversations/** | 再構成型 | 会話ログ (conversation_YYYYMMDD.md) を自動保存 |
| **data/** | 設定・自己診断 | kai_capabilities.json, needed_capabilities_gpt.json 等 |
| **core/** | モジュール群 | Kai / Ariade A/B の各エンジン構成要素 |
| **logs/** | 実行ログ | Kai のログ出力先（自己診断 fingerprint 含む） |
| **.streamlit/** | 秘匿設定 | secrets.toml に API キーを格納 (Cloud 向け) |
| **requirements.txt** | 依存 | streamlit, openai==0.28.0, python‑dotenv |

---
## 5. 会話ログ → Git 自動連携フロー
1. ユーザーが入力すると `append_to_log()` が呼ばれ、`conversations/` に追記。
2. 同関数内で `try_git_commit()` を実行。
   - `git add <当日ログ>`
   - `git commit -m "Update log: conversation_YYYYMMDD.md"`
   - `git push https://<GITHUB_TOKEN>@github.com/...`
3. GitHub に push されると Streamlit Cloud が新イメージをビルドし、数十秒後に再起動。
4. その後のリクエストからは最新ログがシステムプロンプトに含まれる。

---
## 6. システムプロンプト生成ロジック
```python
texts = [
    read('docs/architecture_overview.md'),
    read('docs/base_os_rules.md'),
    read('docs/project_definition.md'),
    read('docs/project_status.md'),
]
return "\n\n".join(texts)
```
> 重要: **architecture_overview.md** 自身も毎回読み込まれるため、内容を更新したら Git push で即反映。

---
## 7. セキュリティ & 運用ルール
| 項目 | 方針 |
|------|------|
| APIキー管理 | `.streamlit/secrets.toml` (Cloud) / `.env` (ローカル) で管理。リポジトリには含めない。 |
| Git コミット | *1ドキュメント=1コミット* を徹底。Kai が自動で行う場合も同様。 |
| トークン節約 | 常時参照は最小限 (本ファイル+主要4ドキュメント)。詳細はオンデマンド読み込み。 |
| 誤更新防止 | ローカル作業前は `git pull origin main` を必須 (pre‑push hook でも警告)。 |
| ソース追跡 | `run_kai_self_check()` のログに fingerprint (md5 + mtime) を出力し、Streamlit Cloud 側で実行コードを確認可能とする。 |

---
## 8. 今後の拡張ポイント
1. **Ariade_A 自動更新フロー** : Function Calling で差分生成→ユーザー承認→コミット。
2. **RAG 連携** : 過去会話ログをベクトル DB へ投入し、高精度検索・要約。
3. **UI 強化** : サイドバーでドキュメント閲覧、ログ日付フィルタ、テーマ別色分けなど。
4. **複数ユーザー対応** : 認証・権限レイヤを追加、Slack / Teams連携も検討。

---
## 9. 用語集
| 用語 | 意味 |
|------|------|
| **Kai** | 本 UI / ブリッジ人格。Streaming UI + Git自動 push 担当。 |
| **Ariade_A** | ドキュメント更新エンジン (PoC) |
| **Ariade_B** | Q&A / 要約エンジン (PoC) |
| **常時参照型** | 毎回プロンプトに読み込む静的ドキュメント群 |
| **再構成型** | 会話ログなど、検索・要約して使うデータ群 |

---
> **備考** : 本ファイルを更新した場合は、必ず Git にコミット→Push して Cloud 側へ反映すること。Kai は新内容を直ちに常時参照に含める。
