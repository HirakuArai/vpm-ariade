# core/capability_proposal.py

import os
import json
from openai import OpenAI

def generate_capability_patch(cap_id: str, spec: str, model="gpt-4.1"):
    """
    指定されたcap_idと仕様説明をもとに、Kaiのcapabilities定義パッチ（1件）をGPTに生成させる
    """
    prompt = f"""
あなたはAI Kaiの能力定義支援エージェントです。
以下の能力ID `{cap_id}` に対応する機能をKaiに追加したいと考えています。

# Kaiに求められている仕様
{spec}

Kaiにおける `capabilities.json` の1件は以下のような構造です：

```json
{{
  "id": "apply_patch",
  "name": "GPT修正提案を適用",
  "description": "KaiがGPTの修正提案を、元のソースコードに反映します。パッチの内容に従い、元の関数を置換します。",
  "requires_confirm": true,
  "enabled": true
}}
```

この形式に合わせて、Kaiに登録すべき能力定義を1件だけ出力してください。
"""

    client = OpenAI()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "あなたはKaiの能力定義支援を行うAIです。"},
            {"role": "user", "content": prompt}
        ]
    )

    # 応答がJSON形式前提。パースして返す
    content = response.choices[0].message.content
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        raise ValueError("GPTからの応答がJSON形式ではありませんでした:\n" + content)
