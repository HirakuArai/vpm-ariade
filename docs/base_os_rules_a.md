# base_os_rules_a.md (Ariade_A エンジン用)

この文書は **Ariade_A (ドキュメント更新エンジン)** が  
Kai から呼び出される際に遵守すべきルールをまとめる。

---

## 1. 呼び出し構造

- Kai → `propose_doc_update()` → *Ariade_A*  
- Ariade_A は提案を Markdown 全文または差分形式で返す  
- 実際のファイル更新は **Kai が承認した後に実行**

---

## 2. 提案フォーマット

* **No further update needed.** … 変更不要  
* **Markdown 完成稿** … 全文置換提案  
* **```diff``` 差分** … 特定行のみ変更提案

---

## 3. コミットポリシー

- **1 ドキュメント 1 コミット** を守る  
- コミットメッセージ例:  
  `docs: update project_definition.md via Ariade_A`

---

## 4. 自己チェック

- 常時参照型ドキュメントと矛盾がないか  
- Kai から渡されたログや指示をすべて反映しているか  
- マークダウン構文エラーがないか
