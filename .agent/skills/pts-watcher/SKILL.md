---
name: pts-watcher
description: PTS（夜間取引）での急騰・急落銘柄を監視・通知
---

# PTS Watcher

株探（Kabutan）のPTSランキング（ナイトセッション）から、現在値が通常取引終値に対して **±5%以上** 変動している銘柄を抽出し、レポートを作成するスキル。

## 機能
- **データソース**: [株探 PTSランキング](https://kabutan.jp/warning/pts_night_price_increase)
- **監視対象**:
    - **保有銘柄のみ**: `Money/stock.md` に記載の全銘柄の個別ページを巡回し、PTS取引情報を取得。
- **フィルタリング**:
    - なし（全件表示）
- **出力**:
    - Directory: `投資メディア事業/daily_info/`
    - Markdown: `YYYYMMDD-pts-alert.md`
    - HTML: `YYYYMMDD-pts-alert.html` (ダークモード、Glassmorphismデザイン)
    - **クリーンアップ**: 実行時に最新2日分を除き古いレポートを自動削除
    - 変動率10%以上は太字で強調

## 実行方法

Bashツールで以下のコマンドを実行：

```bash
python3 watch_pts.py
```

## 出力例

| 変動率 | コード | 銘柄名 | 現在値 | 保有 |
|---|---|---|---|---|
| **+15.20%** | [1234](https://kabutan.jp/stock/?code=1234) | ABC Corp | 1,200 | ==★== |
| -6.50% | [5678](https://kabutan.jp/stock/?code=5678) | XYZ Inc | 500 | |
