---
description: マネーフォワードに自動ログインするスキル
---

# マネーフォワード自動ログイン (moneyforward-login)

提供いただいたGmailアプリパスワードを利用して、IMAP経由で2段階認証の確認コードを自動取得し、マネーフォワード (https://moneyforward.com/login) に自動ログインを行うPlaywrightスクリプトです。

## セットアップ手順

1. このスクリプトはメールアドレスなどの機密情報を利用するため、直接スクリプト内には記述せず `.env` ファイルに保存します。
2. 以下のコマンドで設定ファイルを作成してください。

```bash
cd /Users/mamoru/ThisIsMyLife/.agent/skills/moneyforward-login
cp .env.example .env
```

3. 作成された `.env` ファイルを開き、あなたの**Gmailアドレス** と **マネーフォワードのログインパスワード** を入力してください。（アプリパスワードは設定済みです）

## 必要なパッケージのインストール
以下のコマンドで依存ライブラリをインストールします。
```bash
cd /Users/mamoru/ThisIsMyLife/.agent/skills/moneyforward-login
pip install playwright python-dotenv
playwright install chromium
```

## 実行方法 (ログイン / セッション更新)

設定が完了したら、以下のコマンドで手動ログインやセッションの更新ができます。

```bash
cd /Users/mamoru/ThisIsMyLife/.agent/skills/moneyforward-login
python3 login_mf.py
```

※ 初回ログインが完了すると `mf_state.json` が生成され、以降はブラウザのセッションが維持されるようになります。

## 実行方法 (ポートフォリオ情報の集計)

`mf_state.json` を利用し、楽天銀行・楽天証券の口座情報を自動で更新した上で、ポートフォリオ画面から保有資産（現物国内・現物米国・信用・投資信託）を抽出して `portfolio_summary.json` に出力します。

```bash
cd /Users/mamoru/ThisIsMyLife/.agent/skills/moneyforward-login
python3 portfolio_extractor.py
```
