#!/bin/bash
# MoneyForward自動取得クーロン用スクリプト

# PATHを設定（cron環境ではPATHが最小限のため、Homebrewなどのパスを追加）
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

# スクリプトのディレクトリへ移動
cd /Users/mamoru/ThisIsMyLife/.agent/skills/moneyforward-login

# 実行してログに出力
echo "=== Execution started at $(date) ===" >> cron.log
python3 portfolio_extractor.py >> cron.log 2>&1
echo "=== Execution finished ===" >> cron.log
