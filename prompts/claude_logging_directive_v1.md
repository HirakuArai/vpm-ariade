# Claude / Kai ログ修正実装ディレクティブ v1.0

> **目的** — 既存ログ出力ロジックを *AI ログ出力ガイドライン v1.0*（textdoc\_id: 686187b1ccd48191aceb7c3c9b5396fd）に完全準拠させるための実装指示。

---

## A. ファイル形式変更

### 1. JSON Lines (推奨)

* **出力拡張子**: `.jsonl`
* **フォーマット**: 1 行 1 オブジェクト (`\n` 区切り)
* **例**:

  ```jsonl
  {"ts":"…","agent":"kai", …}
  {"ts":"…","agent":"kai", …}
  ```
* **代替**: 配列 `[ {...}, {...} ]` で保存してもよいが、サイズ拡大時の追記性能を考慮し `.jsonl` をデフォルトとする。

### 2. ローテーション

* 1 ファイル 5 MB を超えたら `YYYYMMDD_HH` 単位でローテート。

---

## B. `kind` 列挙拡張

1. `project_detail` を既存 Enum に追加。
2. **スキーマ更新**: `schemas/log_entry.schema.json` に該当値を追記。
3. **バリデーション**: 未登録 `kind` が来た場合は警告ログを出しつつ `unknown` にフォールバック。

---

## C. 重複ログ排除

1. **ハッシュキー**: `sha256(task_id + response.choices[0].message.content)`。
2. **保存前チェック**: 同一ハッシュが過去 24h 内に存在する場合はスキップし、`dedup_skipped=true` をメタ情報として別ファイルに記録。

---

## D. トークンメトリクス検証

1. `prompt_tokens`, `completion_tokens` が **0** または前回と完全一致 → `metrics_anomaly=true` として警告出力。
2. 異常検出時は Slack Alert (channel: `#kai-logging-alerts`).

---

## E. 実装サンプル（擬似コード）

```python
from pathlib import Path
import json, hashlib, datetime

LOG_PATH = Path("logs/kai_chat.jsonl")
INDEX_PATH = Path("logs/dedup_index.json")  # {hash: ts}

# --- helper ---
ISO = lambda: datetime.datetime.utcnow().isoformat(timespec="milliseconds") + "Z"
SHA = lambda s: hashlib.sha256(s.encode()).hexdigest()

def append_log(entry: dict):
    # 1) kind enum check
    if entry["kind"] not in KIND_ENUM:
        entry["kind"] = "unknown"
    # 2) duplicate check
    h = SHA(entry["task_id"] + json.dumps(entry["response"], ensure_ascii=False))
    idx = INDEX_PATH.exists() and json.loads(INDEX_PATH.read_text()) or {}
    if h in idx and (datetime.datetime.utcnow() - datetime.datetime.fromisoformat(idx[h][:-1])).total_seconds() < 86400:
        warn("duplicate log skipped")
        return
    idx[h] = ISO(); INDEX_PATH.write_text(json.dumps(idx))
    # 3) write as JSONL
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False, separators=(',', ':')) + "\n")
```

---

## F. テストケース

| ケース          | 期待結果                         |
| ------------ | ---------------------------- |
| **正常ログ**     | ファイルに追記され、`jsonschema` 検証パス  |
| **重複ログ**     | 保存されず、`dedup_skipped` 記録     |
| **未登録 kind** | `kind":"unknown"` で保存、アラート発火 |

---

### 提出先

* **PR ブランチ名**: `feature/log-output-v1`
* **レビュアー**: @hiraku-arai

最終更新: 2025‑06‑30

---

## G. スキーマ確認とファイル名ルール (2025‑06‑30更新)

### 1. `schemas/log_entry.schema.json` との整合

* **`kind` 列挙**: `project_detail` が正式に追加済み → 追加実装は不要。
* **必須キー** & 型定義は Directive v1 で想定した内容と一致。
* **`additionalProperties:false`** のため、将来のフィールド追加時は **スキーマも同時更新** が必須。

### 2. ファイル名規約の確認

* **実例**: `logs/llm_calls/20250630_07.jsonl`
* **評価**: `YYYYMMDD_HH.jsonl` 形式で OK。
* **補足**: 新規ローテート時は UTC 基準の HH を使用し、5 MB 超過で強制的に次 `HH+1` ファイルへスイッチする実装を保持。

### 3. Claude への追加指示

```text
*** LOGGING UPDATE 2025‑06‑30 ***
- Ensure the output path follows logs/llm_calls/YYYYMMDD_HH.jsonl.
- Validate every entry against the updated log_entry.schema.json before appending.
- Reject (skip) entries with unknown keys when "additionalProperties" constraint fails, and raise a warning.
*** END UPDATE ***
```

> **備考:** 本更新により、Directive v1.0 はスキーマ／ファイル命名の両面で正式準拠となりました。
