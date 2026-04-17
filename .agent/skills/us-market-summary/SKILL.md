---
name: us-market-summary
description: 米国株サマリーカード生成（今日の指標トップニュース）
---

# 米国株朝メモ（US Market Summary Card）

毎朝の米国株の主要指標（S&P500, NASDAQ, 金, 原油）と、重要ニュース5つを1枚のカード状の美しいHTMLに要約して出力するスキルです。

## 実行結果
- `ideas/daily/YYYYMMDD-us-summary.html` （ブラウザに表示させるカード風レポート）

## フロー
1. Yahoo Finance API 等を利用し前日比と現在値を収集
2. Reuters/WSJ等または既存のニュース収集処理を利用してトップ5のUSニュースを抽出・日本語化
3. 高品質なHTML/CSSテンプレートにデータを埋め込んで出力

## 実行コマンド

### 1. 手動でのHTML単体生成
```bash
python3 generate_us_market_card.py
```

### 2. 全自動パイプライン（スクショ＆X投稿）
以下のスクリプトを実行することで、「HTML生成 → 画像化(Playwright) → x-poster-kabuによるX投稿」までを全自動で行います。Cron等の定期実行にはこちらを指定してください。

```bash
python3 .agent/skills/us-market-summary/auto_us_market_post.py
```
