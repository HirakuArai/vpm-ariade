# Kai VPM - AI-First Virtual Project Manager

AI駆動型の仮想プロジェクトマネージャー。自然言語でプロジェクトを作成・管理できます。

## UI デザイン更新 (2025-07-02)

Streamlit UIを落ち着いたAIテイストのデザインに刷新しました。視覚的ノイズを削減し、グレー基調の配色にアクセントカラー（indigo-500）を組み合わせた、プロフェッショナルで見やすいインターフェースを実現。過度な絵文字を排除し、ミニマルなAIシンボルに置き換えることで、洗練された印象を与えるデザインになりました。Tailwind CSS標準のフォントサイズ階層を採用し、情報の階層構造を明確にしています。

## 主な機能

- 自然言語でのプロジェクト作成
- フェーズベースのプロジェクト管理
- AI による自動タスク生成と優先順位付け
- Git 統合による変更管理
- 会話履歴の自動保存

## 使用方法

```bash
streamlit run app.py
```

## 要件

- Python 3.10+
- OpenAI API キー
- Streamlit 1.28+

## セットアップ

1. 依存関係のインストール:
   ```bash
   pip install -r requirements.txt
   ```

2. OpenAI APIキーの設定:
   ```bash
   export OPENAI_API_KEY="your-api-key"
   ```

3. アプリケーションの起動:
   ```bash
   streamlit run app.py
   ```