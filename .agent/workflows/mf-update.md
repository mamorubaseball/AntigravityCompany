---
description: マネーフォワードのポートフォリオ情報を取得し、HTMLレポートを更新する
---

// turbo-all
1. セッション状態の確認とログイン（必要な場合）
マネーフォワードの認証情報を更新します。
```bash
cd /Users/mamoru/AntigravityCompany/.agent/skills/moneyforward-login
python3 login_mf.py
```

2. 資産データの取得とレポート生成
最新の資産状況をスクレイピングし、履歴データと統合したHTMLレポートを生成します。
```bash
python3 portfolio_extractor.py
```

3. レポートの確認
生成されたレポートをブラウザで開いて確認してください。
[portfolio_report.html](file:///Users/mamoru/AntigravityCompany/.agent/skills/moneyforward-login/portfolio_report.html)
