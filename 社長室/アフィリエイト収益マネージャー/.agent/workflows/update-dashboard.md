---
description: A8.netのアフィリエイトリンク情報を最新の状態に更新し、ダッシュボードをリフレッシュする
---

# A8.net ダッシュボード更新ワークフロー

A8.netから最新の提携プログラム情報を収集し、カテゴリ分けを行ってダッシュボード(`dashboard.html`)を更新します。

## 実行ステップ

// turbo
1. **情報の収集 (Scraping)**
   A8.netにログインし、参加中の全プログラムからトラッキングURLを抽出します。
   ```bash
   python3 scripts/a8_manager.py
   ```

// turbo
2. **カテゴリ分類とデータ更新 (Categorization)**
   抽出したデータを「投資」「エンジニア」「その他」に分類し、ダッシュボード用の `dashboard_data.js` を生成します。
   ```bash
   python3 scripts/categorize_data.py
   ```

3. **反映の確認**
   ルートディレクトリにある `dashboard.html` をブラウザで開き、最新の情報が反映されていることを確認します。
