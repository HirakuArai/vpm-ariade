# project_definition.md ( PoC 最小構成・Kai 統合 )

## 1. プロジェクト名
- **Ariade_PoC**

## 2. 全体目的
AI ベースの仮想 PM (Ariade) を PoC として構築し、  
ドキュメント更新フローと Q&A サポートが実用水準に乗るかを検証。  
**Kai** は唯一の表人格として UI と判断ハブを担う。

## 3. 範囲
1. ドキュメント更新提案 → 承認 → Git コミット  
2. Q&A / 要約 / リスク提案  
3. 会話ログの自動保存・トークン管理  
(大規模 DB 連携・多人数承認は MVP 以降)

## 4. 体制図
```mermaid
graph TD
  Owner["Owner (user)"]
  Kai["Kai<br/>(UI / Bridge / Approval)"]
  AA["Ariade_A<br/><i>docs update engine</i>"]
  BB["Ariade_B<br/><i>Q&A / summarization engine</i>"]

  Owner --> Kai
  Kai --> AA
  Kai --> BB

## 5. PoC スケジュール
| フェーズ        | 期限       | 目標                          |
|-----------------|-----------|-------------------------------|
| 開発環境整備    | 2025‑04‑10 | Streamlit Cloud + GitHub 連携 |
| Kai UI β       | 2025‑04‑20 | 会話ログ保存 & 提案承認フロー |
| PoC レビュー    | 2025‑05‑01 | MVP 移行要否を判断            |

## 6. 成功基準
1. Kai UI だけでドキュメント更新フローが完結  
2. 誤更新ゼロ、提案精度が実用レベル  
3. Git 履歴が明瞭で、ロールバック容易

## 7. リスク
- GPT の誤提案 ⇒ 承認フローで防止  
- ログの肥大化 ⇒ 要約 & トークン最適化  
- 機密情報流出 ⇒ st.secrets / .env で管理

## 8. 将来拡張
- 多人数アクセス制御  
- ベクトル DB / 外部ストレージ連携  
- UI 高度化 (タスクボード・進捗チャート etc.)
