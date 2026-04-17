---
name: us-pts-watcher
description: 米国株の時間外取引（Pre Market / After Hours）価格をチェックし、保有銘柄の変動を監視するスキル
---

# US PTS Watcher

## 概要
保有している米国株（`Money/stock.md`記載）について、[Kabutan US](https://us.kabutan.jp/) から時間外取引（Pre Market / After Hours = US版PTS）の価格情報を取得し、レポートを生成します。

## 機能
- **データソース**: [Kabutan US 個別銘柄ページ](https://us.kabutan.jp/stocks/{TICKER})
- **監視対象**: `Money/stock.md` に記載されている全米国株（アルファベットのみのティッカー）
- **取得情報**:
    - 通常取引終値
    - PTS価格（After Hours または Pre Market）
    - PTSでの変動率
- **出力**:
    - Markdown: `ideas/daily/YYYYMMDD-us-pts-alert.md`
    - HTML: `ideas/daily/YYYYMMDD-us-pts-alert.html` (ダークモード、日本に合わせて **Red=Rise/Green=Fall** を採用)

## 実行方法
1. `python3 watch_us_pts.py` を実行
2. または、ワークフロー `/us-pts-watch` を使用

## ファイル構成
- `watch_us_pts.py`: メインスクリプト
- `ideas/daily/`: レポート出力先
