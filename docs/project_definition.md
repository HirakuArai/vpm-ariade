---
doc_type: "project_definition"
required_capabilities:
  - "read_doc"            # ドキュメント閲覧
  - "edit_file"           # ファイル修正提案
  - "propose_doc_update"  # Ariade_A 呼び出し
  - "manage_tasks"        # タスク一覧を扱う
---
# project_definition.md (PoC 最小構成・Kai 統合)

## 2. 全体目的
AI ベースの仮想 PM (Ariade) を PoC として構築し、  
ドキュメント更新フローと Q&A サポートが実用水準に乗るかを検証。  
**Kai** は唯一の表人格として UI・判断ハブを担い、2025年4月よりプロジェクトマネージャー（PM）として正式に位置付けられた。

## 4. 体制図
```mermaid
graph TD
  Owner["Owner (user)"]
  Kai["Kai<br/>(PM / UI / Bridge / Approval)"]
  AA["Ariade_A<br/><i>docs update engine</i>"]
  BB["Ariade_B<br/><i>Q&A / summarization engine</i>"]

  Owner --> Kai
  Kai --> AA
  Kai --> BB
```

## 9. 今後の機能展望
- Kai のプロジェクトマネージャー（PM）機能拡張（進捗管理・タスク割当など）
- Ariade_A/B との連携強化による自動化範囲の拡大
- ユーザー体験向上のためのUI/UX改善
