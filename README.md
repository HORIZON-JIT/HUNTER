# HUNTER

Claude Agent SDK を使ったマルチエージェント リサーチ・分析システム。

## アーキテクチャ

```
[ユーザー] → [ディレクター(オーケストレータ)]
                    ├── researcher   (Web情報収集)
                    ├── analyst      (分析・パターン発見)
                    └── writer       (レポート作成)
```

## セットアップ

```bash
pip install -e .
export ANTHROPIC_API_KEY="your-api-key"
```

## 使い方

```bash
hunter "AIエージェントの最新トレンド"
# または
python -m hunter "AIエージェントの最新トレンド"
```

レポートは `output/` ディレクトリに Markdown ファイルとして出力されます。
