---
name: kabu-trend-us
description: 米国株トレンド収集 (Bloomberg/WSJ/CNBC/Reuters/etc)
---

# 米国株トレンド収集 (US Stock Trend)

米国市場の主要ニュースサイトおよびデータソースからトレンド情報を収集し、`ideas/daily/YYYYMMDD-kabu-us.md` に保存する。

## データソース
- **Bloomberg / WSJ / CNBC / MarketWatch**: RSSフィード
- **Reuters / Finviz**: HTML解析またはカスタム取得
- **Finviz (Individual Tickers)**: 指定銘柄 (ASTS, CRCL, GOOGL, MRVL, SOFI, PFE, PLTR, NVDA) のニュース
- **Scorpion Capital**: 最新レポート (Short Research)
- **Yahoo Finance**: 市場データAPI (Market Overview)

## 実行手順

### 1. 収集・分析
`collect_kabu_us.py` を実行してデータを収集・分析する。
- 英語の興味キーワード（AI, Security, Earnings, Fed, Stock等）でフィルタリングを行う。
- `Money/stock.md` に記載された保有銘柄（USティッカー）を自動的に読み込み、Finvizからニュースを取得・優先表示（★★★）する。
- 指定された個別銘柄 (ASTS, CRCL, GOOGL, MRVL, SOFI, PFE, PLTR, NVDA) については Finviz から直近のニュースを取得する。
- Scorpion Capital から最新のショートレポートを取得する。
- Yahoo Financeからは主要指数（S&P500, Nasdaq, USDJPY等）の現在値も取得する。

### 2. 出力
`ideas/daily/YYYYMMDD-kabu-us.md` にMarkdown形式で出力する。

**フォーマット:**
- **マーケット概況**: Yahoo Financeからの主要指数データ
- **注目トピック**: 重要度が高い記事
- **媒体別ニュース**: 各ソースごとの記事一覧

## 使用方法

Bashツールで以下のコマンドを実行：

```bash
python3 collect_kabu_us.py
```

### 3. 自動投稿 (X Poster連携)

**1. 下書き生成:**
TSLA, SOFI, NVDAなどのニュースから投稿案をMarkdownファイルに生成します。
このファイルには元記事の出典も含まれます。

```bash
python3 .agent/skills/kabu-trend-us/generate_us_drafts.py
```
-> `ideas/posts/YYYYMMDD_us_post.md` が生成されます。

**2. 投稿実行:**
生成された下書きファイルを確認後、以下のコマンドでXに連続投稿します（5分間隔）。

```bash
python3 .agent/skills/kabu-trend-us/post_from_draft.py ideas/posts/YYYYMMDD_us_post.md
```


