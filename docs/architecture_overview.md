+---
+doc_type: "architecture_overview"
+required_capabilities:
+  - "read_doc"
+  - "append_to_log"       # 会話ログ保存
+  - "git_push"            # 自動コミット／Push
+  - "embed_logs"          # RAG 用ベクトル化（将来）
+---

# アーキテクチャ概要 ― VPM‑Ariade PoC

> **最終更新日**: 2025‑04‑20

---
## 1. 本ドキュメントの目的
このファイルは **Kai (UI／ブリッジ人格)** が常に参照できる基礎情報として、PoC 環境の全体像・ディレクトリ構成・自動化フロー・運用ルールをまとめたものです。Kai は回答や提案を行う際に、本ドキュメントを常時プロンプトへ組み込みます。

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
## 3. ディレクトリ構成（ルート直下）
| パス | 種別 | 役割 |
|------|------|------|
| **app.py** | 実行スクリプト | Kai の UI・会話処理・Git 自動 push |
| **docs/** | 常時参照型 | プロジェクト定義・ベース OS・本ファイル など |
| **conversations/** | 再構成型 | 会話ログ (conversation_YYYYMMDD.md) を自動保存 |
| **.streamlit/secrets.toml** | 機密 | `OPENAI_API_KEY`, `GITHUB_TOKEN` を保持 (Cloud 上) |
| **requirements.txt** | 依存 | streamlit, openai==0.28.0, python‑dotenv |

---
## 4. 会話ログ → Git 自動連携フロー
1. ユーザーが入力すると `append_to_log()` が呼ばれ、`conversations/` に追記。
2. 同関数内で `try_git_commit()` を実行。
   - `git add <当日ログ>`
   - `git commit -m "Update log: conversation_YYYYMMDD.md"`
   - `git push https://<GITHUB_TOKEN>@github.com/...`
3. GitHub に push されると Streamlit Cloud が新イメージをビルドし、数十秒後に再起動。
4. その後のリクエストからは最新ログがシステムプロンプトに含まれる。

---
## 5. システムプロンプト生成ロジック
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
## 6. セキュリティ & 運用ルール
| 項目 | 方針 |
|------|------|
| APIキー管理 | `.streamlit/secrets.toml` (Cloud) / `.env` (ローカル) で管理。リポジトリには含めない。 |
| Git コミット | *1ドキュメント=1コミット* を徹底。Kai が自動で行う場合も同様。 |
| トークン節約 | 常時参照は最小限 (本ファイル+主要4ドキュメント)。詳細はオンデマンド読み込み。 |
| 誤更新防止 | ローカル作業前は `git pull origin main` を必須 (pre‑push hook でも警告)。 |

---
## 7. 今後の拡張ポイント
1. **Ariade_A 自動更新フロー** : Function Calling で差分生成→ユーザー承認→コミット。
2. **RAG 連携** : 過去会話ログをベクトル DB へ投入し、高精度検索・要約。
3. **UI 強化** : サイドバーでドキュメント閲覧、ログ日付フィルタ、テーマ別色分けなど。
4. **複数ユーザー対応** : 認証・権限レイヤを追加、Slack / Teams連携も検討。

---
## 8. 用語集
| 用語 | 意味 |
|------|------|
| **Kai** | 本 UI / ブリッジ人格。Streaming UI + Git自動 push 担当。 |
| **Ariade_A** | ドキュメント更新エンジン (PoC) |
| **Ariade_B** | Q&A / 要約エンジン (PoC) |
| **常時参照型** | 毎回プロンプトに読み込む静的ドキュメント群 |
| **再構成型** | 会話ログなど、検索・要約して使うデータ群 |

---

> **備考** : 本ファイルを更新した場合は、必ず Git にコミット→Push して Cloud 側へ反映すること。Kai は新内容を直ちに常時参照に含める。

