---
name: kabu-trend-jp
description: 日本株トレンド収集 (Bloomberg/Reuters/WSJ/Kabutan)
---

# 日本株トレンド収集 (JP Stock Trend)

主要な経済ニュースサイト（日本版）から、Google News RSSを経由して最新の株式・市場トレンド情報を収集し、`ideas/daily/YYYYMMDD-kabu-jp.md` に保存する。

## データソース
- Bloomberg Japan (`site:bloomberg.co.jp`)
- Reuters Japan (`site:jp.reuters.com`)
- WSJ Japan (`site:jp.wsj.com`)
- Kabutan (`site:kabutan.jp`)

※公式サイトのRSSフィードが限定的であるため、Google News RSSのサイト指定フィルタを使用することで安定的に記事を収集する。

## 実行手順

### 1. 収集・分析
`collect_kabu_jp.py` を実行してデータを収集・分析する。
- `Money/stock.md` に記載された保有銘柄（JPコード）を自動的に読み込み、Kabutan等でニュースを検索・優先表示（★★★）する。
このスクリプトは `GEMINI.md` の興味領域設定と、株式市場固有のキーワード（円安、決算、IPOなど）に基づいて記事の重要度を判定する。

### 2. 出力
`ideas/daily/YYYYMMDD-kabu-jp.md` にMarkdown形式で出力する。

**フォーマット:**
- **注目トピック**: 重要度が高い（★2以上）記事をリストアップ
- **媒体別ニュース**: 各ソースごとの最新記事一覧

## 使用方法

Bashツールで以下のコマンドを実行：

```bash
python3 collect_kabu_jp.py
```
