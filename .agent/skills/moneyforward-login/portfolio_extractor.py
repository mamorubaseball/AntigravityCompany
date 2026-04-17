import json
import re
import os
import time
import datetime
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

def parse_valuation(val_str):
    """
    Parses a MoneyForward valuation string (e.g. '1,234,567円', '1,234.56 USD')
    into an integer (JPY) or float (USD) if needed, but for totals we just clean it.
    Returns the integer JPY amount. If it's USD, MF usually puts the JPY equivalent below it.
    For simplicity, let's just extract digits.
    """
    # Extract digits and minus sign
    digits = re.sub(r'[^\d-]', '', val_str)
    try:
        return int(digits)
    except:
        return 0

def extract():
    today = datetime.datetime.now().strftime("%Y/%m/%d")
    
    # Check if already updated today to bypass scraping
    history_file = "portfolio_history.json"
    if os.path.exists(history_file) and os.path.exists("portfolio_summary.json"):
        with open(history_file, "r", encoding="utf-8") as f:
            history_data = json.load(f)
            if len(history_data) > 0 and history_data[-1].get("date") == today:
                print("Already updated today. Generating HTML & CSV from existing summary...")
                with open("portfolio_summary.json", "r", encoding="utf-8") as f_sum:
                    data = json.load(f_sum)
                generate_html_report(data, history_data)
                export_to_csv(history_data)
                return

    state_file = "mf_state.json"
    if not os.path.exists(state_file):
        print("Error: mf_state.json not found! Please login first.")
        return

    print("Launching browser...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(storage_state=state_file)
        page = context.new_page()

        # Step 1: Force SSO Loop to guarantee /pf/ session
        print("Initiating SSO check via sign_in...")
        page.goto("https://moneyforward.com/sign_in")
        page.wait_for_timeout(3000)
        
        if "account_selector" in page.url:
            print("Redirected to account_selector. Bypassing...")
            try:
                page.click("text=mamorubasebaii9045@gmail.com", timeout=5000)
                page.wait_for_timeout(3000)
            except Exception as e:
                print(f"Failed to click account: {e}")
        
        # Passkey promotion
        if "passkey_promotion" in page.url or page.locator("text=登録せず次へ").is_visible():
            print("Skipping passkey promotion...")
            try:
                page.click("text=登録せず次へ", timeout=3000)
            except Exception:
                pass
        
        try:
            page.wait_for_url("**/pf/*", timeout=15000)
            page.wait_for_load_state("networkidle")
        except Exception:
            print("Warning: Did not reach /pf/ cleanly. Current URL:", page.url)

        # Step 2: Reload Rakuten Bank and Rakuten Securities
        print("Looking for accounts to reload...")
        time.sleep(3)
        targets = ["楽天銀行", "楽天証券"]
        for target in targets:
            print(f"Looking for '{target}'...")
            el = page.locator(f"text='{target}'").first
            if el.count() > 0:
                print(f"Found '{target}'. Attempting to click update...")
                container = el.locator("xpath=ancestor::li[contains(@class,'account facilities-column')]").first
                if container.count() > 0:
                    btn = container.locator("a:has-text('更新')").last
                    if btn.count() > 0:
                        try:
                            # It's an a tag with text 更新. the .last prevents matching "編集" if it contains 更新
                            btn.click()
                            print(f"Successfully requested update for {target}")
                        except Exception as e:
                            print(f"Failed to click update for {target}: {e}")
                    else:
                        print(f"Update button not found inside container for {target}")
                else:
                    print("Container not found.")
            else:
                print(f"'{target}' text not found on page.")

        print("Waiting 60 seconds for updates to process...")
        time.sleep(60)

        # Step 3: Navigate to portfolio
        print("Navigating to portfolio page...")
        page.goto("https://moneyforward.com/bs/portfolio")
        page.wait_for_load_state("networkidle")
        time.sleep(3)

        # Step 4: Extract with BeautifulSoup
        print("Parsing portfolio HTML...")
        html = page.content()
        with open("debug_portfolio.html", "w", encoding="utf-8") as f:
            f.write(html)
        soup = BeautifulSoup(html, "html.parser")

        # Data structure
        data = {
            "totals": {
                "stock_spot_domestic": 0,
                "stock_spot_domestic_pl": 0,
                "stock_spot_us": 0,
                "stock_spot_us_pl": 0,
                "stock_margin": 0,
                "investment_trust": 0,
                "investment_trust_pl": 0
            },
            "holdings": {
                "stock_spot_domestic": [],
                "stock_spot_us": [],
                "stock_margin": [],
                "investment_trust": []
            }
        }

        # Helper to find table rows
        def extract_table_rows(title_query):
            header = soup.find('h1', class_='heading-normal', string=re.compile(title_query))
            if not header: return []
            
            # Find the next table
            table = header.find_next("table")
            if not table: return []
            
            # Extract header indexes
            headers = [th.get_text(strip=True).replace("\n", "") for th in table.find_all("th")]
            
            name_idx = 1
            for col in ["銘柄名", "名称", "種類・名称"]:
                if any(col in h for h in headers):
                    name_idx = next(i for i, h in enumerate(headers) if col in h)
                    break
                    
            code_idx = 0
            if any("銘柄コード" in h for h in headers):
                code_idx = next(i for i, h in enumerate(headers) if "銘柄コード" in h)
            
            val_idx = 5
            for col in ["評価額", "残高"]:
                if any(col in h for h in headers):
                    val_idx = next(i for i, h in enumerate(headers) if col in h)
                    break
            
            pl_idx = -1
            if any("評価損益" in h for h in headers):
                pl_idx = next(i for i, h in enumerate(headers) if "評価損益" in h)

            row_data = []
            for tr in table.find_all("tr"):
                if tr.find("th"): continue # skip sub-headers
                tds = tr.find_all("td")
                if len(tds) > val_idx:
                    code = tds[code_idx].get_text(strip=True) if len(tds) > code_idx else ""
                    name = tds[name_idx].get_text(strip=True) if len(tds) > name_idx else ""
                    # Handle multi-line texts (like span inside td)
                    for item in tds[val_idx].stripped_strings:
                        val_str = item
                        break # take first line
                    
                    pl = 0
                    if pl_idx != -1 and len(tds) > pl_idx:
                        pl_str = list(tds[pl_idx].stripped_strings)[0]
                        pl = parse_valuation(pl_str)
                        
                    row_data.append((code, name, parse_valuation(val_str), pl))
            return row_data

        # --- 株式（現物）---
        spot_rows = extract_table_rows("株式（現物）")
        for code, name, val, pl in spot_rows:
            # US stocks usually have alphabetical ticker or no 4-digit code
            if re.match(r'^[A-Za-z]+$', code) or (code == "" and re.match(r'^[A-Z0-9.\-\s]+$', name)):
                data["holdings"]["stock_spot_us"].append({"name": name, "valuation": val, "pl": pl})
                data["totals"]["stock_spot_us"] += val
                data["totals"]["stock_spot_us_pl"] += pl
            else:
                data["holdings"]["stock_spot_domestic"].append({"name": name, "valuation": val, "pl": pl})
                data["totals"]["stock_spot_domestic"] += val
                data["totals"]["stock_spot_domestic_pl"] += pl

        # --- 株式（信用）---
        margin_rows = extract_table_rows("株式（信用）")
        for code, name, val, pl in margin_rows:
            data["holdings"]["stock_margin"].append({"name": name, "valuation": val, "pl": pl})
            data["totals"]["stock_margin"] += val
            # PL for margin stocks is handled separately in margin_stocks_detail usually, 
            # but let's keep it here if MF shows it in summary table too.
            
        # --- 信用建玉 (Margin Open Positions) ---
        data["holdings"]["margin_stocks_detail"] = []
        mgn_sec = soup.find(id="portfolio_det_mgn")
        if mgn_sec:
            for table in mgn_sec.find_all("table"):
                headers = [th.get_text(strip=True).replace("\n", "") for th in table.find_all("th")]
                if "評価損益" in headers and "現在値" in headers:
                    name_idx = next(i for i, h in enumerate(headers) if "銘柄名" in h)
                    qty_idx = next(i for i, h in enumerate(headers) if "保有数" in h)
                    price_idx = next(i for i, h in enumerate(headers) if "現在値" in h)
                    pl_idx = next(i for i, h in enumerate(headers) if "評価損益" in h)
                    
                    for tr in table.find_all("tr"):
                        if tr.find("th"): continue
                        tds = tr.find_all("td")
                        if len(tds) > pl_idx:
                            name = tds[name_idx].get_text(strip=True)
                            qty_str = tds[qty_idx].get_text(strip=True)
                            price_str = list(tds[price_idx].stripped_strings)[0]
                            pl_td = tds[pl_idx]
                            pl_str = list(pl_td.stripped_strings)[0]
                            
                            qty = parse_valuation(qty_str)
                            price = parse_valuation(price_str)
                            pl = parse_valuation(pl_str)
                            
                            val = qty * price
                            data["holdings"]["margin_stocks_detail"].append({"name": name, "valuation": val, "pl": pl, "pl_str": pl_str})

        # --- 投資信託 ---
        trust_rows = extract_table_rows("投資信託")
        for code, name, val, pl in trust_rows:
            data["holdings"]["investment_trust"].append({"name": name, "valuation": val, "pl": pl})
            data["totals"]["investment_trust"] += val
            data["totals"]["investment_trust_pl"] += pl
            
        # --- 現金・預金 ---
        cash_rows = extract_table_rows("預金・現金")
        if "cash" not in data["totals"]:
            data["totals"]["cash"] = 0
            data["holdings"]["cash"] = []
        for code, name, val, pl in cash_rows:
            data["holdings"]["cash"].append({"name": name, "valuation": val})
            data["totals"]["cash"] += val
                
        # --- 暗号資産 (Crypto) - Fixed ---
        if "crypto" not in data["totals"]:
            data["totals"]["crypto"] = 0
            data["holdings"]["crypto"] = []
        
        data["holdings"]["crypto"].append({"name": "ビットコイン (固定)", "valuation": 100000})
        data["totals"]["crypto"] += 100000

        # Save to JSON summary
        out_file = "portfolio_summary.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
        print(json.dumps(data, ensure_ascii=False, indent=2))
        print(f"Successfully extracted and saved to {out_file}")

        # Update History Database
        history_file = "portfolio_history.json"
        history_data = []
        if os.path.exists(history_file):
            with open(history_file, "r", encoding="utf-8") as f:
                history_data = json.load(f)
                
        today = datetime.datetime.now().strftime("%Y/%m/%d")
        
        # Calculate commodities/domestic separation for history
        commodities = []
        real_domestic = []
        kw = ["ゴールド", "純金", "金", "銀", "プラチナ", "コモディティ"]
        for item in data["holdings"].get("stock_spot_domestic", []):
            if any(k in item["name"] for k in kw):
                commodities.append(item)
            else:
                real_domestic.append(item)
                
        total_commo = sum(item["valuation"] for item in commodities)
        total_dom = sum(item["valuation"] for item in real_domestic)
        total_us = data["totals"].get("stock_spot_us", 0)
        total_trust = data["totals"].get("investment_trust", 0)
        total_margin = data["totals"].get("stock_margin", 0)
        total_crypto = data["totals"].get("crypto", 0)
        total_cash = data["totals"].get("cash", 0)
        total_assets = total_us + total_trust + total_margin + total_commo + total_dom + total_crypto + total_cash
        
        def calc_pl_rate(val, pl):
            cost = val - pl
            if cost <= 0: return 0
            return (pl / cost) * 100

        pl_us = data["totals"].get("stock_spot_us_pl", 0)
        pl_trust = data["totals"].get("investment_trust_pl", 0)
        pl_commo = 0
        pl_dom = 0
        kw = ["ゴールド", "純金", "金", "銀", "プラチナ", "コモディティ"]
        for item in data["holdings"].get("stock_spot_domestic", []):
            item_pl = item.get("pl", 0)
            if any(k in item["name"] for k in kw):
                pl_commo += item_pl
            else:
                pl_dom += item_pl
        
        total_pl_sum = pl_us + pl_dom + pl_trust + pl_commo
        total_requested_val = total_us + total_dom + total_trust + total_commo
        
        new_entry = {
            "date": today,
            "total_assets": total_assets,
            "domestic": total_dom,
            "dom_pl": pl_dom,
            "dom_pl_rate": round(calc_pl_rate(total_dom, pl_dom), 1),
            "us": total_us,
            "us_pl": pl_us,
            "us_pl_rate": round(calc_pl_rate(total_us, pl_us), 1),
            "trust": total_trust,
            "trust_pl": pl_trust,
            "trust_pl_rate": round(calc_pl_rate(total_trust, pl_trust), 1),
            "cash": total_cash,
            "commodity": total_commo,
            "commo_pl": pl_commo,
            "commo_pl_rate": round(calc_pl_rate(total_commo, pl_commo), 1),
            "crypto": total_crypto,
            "margin": total_margin,
            "total_pl": total_pl_sum,
            "total_pl_rate": round(calc_pl_rate(total_requested_val, total_pl_sum), 1)
        }
        
        existing_idx = next((i for i, h in enumerate(history_data) if h["date"] == today), None)
        if existing_idx is not None:
            history_data[existing_idx] = new_entry
        else:
            history_data.append(new_entry)
            
        history_data.sort(key=lambda x: x["date"])
        with open(history_file, "w", encoding="utf-8") as f:
            json.dump(history_data, f, ensure_ascii=False, indent=2)

        generate_html_report(data, history_data)
        export_to_csv(history_data)
        
        browser.close()

def export_to_csv(history_data):
    import csv
    out_csv = "portfolio_history.csv"
    if not history_data:
        return
        
    # Get all unique keys from all entries to ensure we have all headers
    all_keys = []
    for entry in history_data:
        for k in entry.keys():
            if k not in all_keys:
                all_keys.append(k)
                
    # Define a preferred order if possible, but fallback to discovered keys
    preferred = ["date", "total_assets", "domestic", "dom_pl", "dom_pl_rate", "us", "us_pl", "us_pl_rate", 
                 "trust", "trust_pl", "trust_pl_rate", "cash", "commodity", "commo_pl", "commo_pl_rate", 
                 "crypto", "margin", "total_pl", "total_pl_rate"]
    
    fieldnames = [k for k in preferred if k in all_keys] + [k for k in all_keys if k not in preferred]
    
    with open(out_csv, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(history_data)
    print(f"CSV History exported at {out_csv}")

def generate_html_report(data, history_data):
    total_us = data["totals"]["stock_spot_us"]
    pl_us = data["totals"].get("stock_spot_us_pl", 0)
    
    total_trust = data["totals"]["investment_trust"]
    pl_trust = data["totals"].get("investment_trust_pl", 0)
    
    total_margin = data["totals"]["stock_margin"]
    total_crypto = data["totals"].get("crypto", 0)
    total_cash = data["totals"].get("cash", 0)
    
    commodities = []
    real_domestic = []
    pl_commo = 0
    pl_dom = 0
    # Identify commodities (Gold, Silver, Platinum, etc.)
    kw = ["ゴールド", "純金", "金", "銀", "プラチナ", "コモディティ"]
    for item in data["holdings"]["stock_spot_domestic"]:
        item_pl = item.get("pl", 0)
        if any(k in item["name"] for k in kw):
            commodities.append(item)
            pl_commo += item_pl
        else:
            real_domestic.append(item)
            pl_dom += item_pl
            
    total_commo = sum(item["valuation"] for item in commodities)
    total_dom = sum(item["valuation"] for item in real_domestic)
    
    total_pl_sum = pl_us + pl_dom + pl_trust + pl_commo
    
    # Calculate PL Percentages (PL / (Valuation - PL))
    def calc_pl_rate(val, pl):
        cost = val - pl
        if cost <= 0: return 0
        return (pl / cost) * 100
        
    rate_us = calc_pl_rate(total_us, pl_us)
    rate_dom = calc_pl_rate(total_dom, pl_dom)
    rate_trust = calc_pl_rate(total_trust, pl_trust)
    rate_commo = calc_pl_rate(total_commo, pl_commo)
    
    total_requested_val = total_us + total_dom + total_trust + total_commo
    total_requested_pl = total_pl_sum
    rate_total = calc_pl_rate(total_requested_val, total_requested_pl)
    
    total_assets = total_us + total_trust + total_margin + total_commo + total_dom + total_crypto + total_cash
    
    # --- Portfolio Targets ---
    targets = {}
    targets_file = "portfolio_targets.json"
    if os.path.exists(targets_file):
        with open(targets_file, "r", encoding="utf-8") as f:
            targets = json.load(f)
            
    # --- Growth Rate Calculations ---
    from datetime import datetime as dt, timedelta
    
    def get_past_entry(days_ago):
        target_date = (dt.now() - timedelta(days=days_ago)).strftime("%Y/%m/%d")
        # Find closest date that is <= target_date
        best_entry = None
        for entry in history_data:
            if entry["date"] <= target_date:
                if best_entry is None or entry["date"] > best_entry["date"]:
                    best_entry = entry
        return best_entry

    def get_ytd_entry():
        current_year = dt.now().year
        target_prefix = f"{current_year}/01/01"
        for entry in history_data:
            if entry["date"] >= target_prefix:
                return entry
        return history_data[0] if history_data else None

    def calc_growth(current, past_entry, key):
        if not past_entry or key not in past_entry: return 0
        past_val = past_entry[key]
        if past_val <= 0: return 0
        return (current / past_val - 1) * 100

    entry_1m = get_past_entry(30)
    entry_3m = get_past_entry(90)
    entry_ytd = get_ytd_entry()
    
    metrics = {
        "Total": {"val": total_assets, "1m": calc_growth(total_assets, entry_1m, "total_assets"), "3m": calc_growth(total_assets, entry_3m, "total_assets"), "ytd": calc_growth(total_assets, entry_ytd, "total_assets")},
        "US Stocks": {"val": total_us, "1m": calc_growth(total_us, entry_1m, "us"), "3m": calc_growth(total_us, entry_3m, "us"), "ytd": calc_growth(total_us, entry_ytd, "us")},
        "JP Stocks": {"val": total_dom, "1m": calc_growth(total_dom, entry_1m, "domestic"), "3m": calc_growth(total_dom, entry_3m, "domestic"), "ytd": calc_growth(total_dom, entry_ytd, "domestic")},
        "Trusts/ETF": {"val": total_trust, "1m": calc_growth(total_trust, entry_1m, "trust"), "3m": calc_growth(total_trust, entry_3m, "trust"), "ytd": calc_growth(total_trust, entry_ytd, "trust")},
        "Commodity": {"val": total_commo, "1m": calc_growth(total_commo, entry_1m, "commodity"), "3m": calc_growth(total_commo, entry_3m, "commodity"), "ytd": calc_growth(total_commo, entry_ytd, "commodity")}
    }

    # --- Target Progress ---
    target_progress = []
    if targets:
        mapping = {
            "投資信託": (total_trust, targets.get("target_trust_etf", 0)),
            "コモディティ": (total_commo, targets.get("target_commodity", 0)),
            "米国株": (total_us, targets.get("target_us_stock", 0)),
            "日本株(ETFを含む)": (total_dom, targets.get("target_jp_stock", 0)),
            "現金・預金": (total_cash, targets.get("target_cash", 0))
        }
        total_target_val = sum(v[1] for v in mapping.values())
        total_current_val = sum(v[0] for v in mapping.values())
        
        for label, (current, target) in mapping.items():
            pct = (current / target * 100) if target > 0 else 0
            gap = target - current
            target_progress.append({"label": label, "current": current, "target": target, "pct": min(pct, 100), "gap": gap})
            
        # Monthly Plan (Dec 2026 Target)
        remaining_months = max(1, (targets.get("target_year", 2026) * 12 + targets.get("target_month", 12)) - (dt.now().year * 12 + dt.now().month) + 1)
        total_gap = sum(p["gap"] for p in target_progress if p["gap"] > 0)
        monthly_investment = total_gap / remaining_months

    if total_assets == 0:
        print("Total assets is 0, skipping HTML report generation.")
        return
        
    r_us = (total_us / total_assets) * 100
    r_trust = (total_trust / total_assets) * 100
    r_dom = (total_dom / total_assets) * 100
    r_commo = (total_commo / total_assets) * 100
    r_margin = (total_margin / total_assets) * 100
    r_crypto = (total_crypto / total_assets) * 100
    r_cash = (total_cash / total_assets) * 100
    
    general_risks = []
    margin_risks = []
    
    # Margin Open Positions Swing Trade Assessment
    margin_details = data["holdings"].get("margin_stocks_detail", [])
    if margin_details:
        margin_risks.append("<li><h3 style='margin-top:0'>📉 個別銘柄スイング戦略評価</h3></li>")
        for s in margin_details:
            pl = s["pl"]
            val = s["valuation"]
            cost = val - pl if (val - pl) > 0 else 1
            pl_pct = (pl / cost) * 100
            n = s["name"]
            if pl_pct <= -5:
                margin_risks.append(f"<li class='text-red'>🚫 <b>{n}</b>: {s['pl_str']} ({pl_pct:.1f}%) <br>スイングトレードの目安（-5%〜-8%）を超えて損失が拡大しています。<b>直ちに損切り（ロスカット）を実行すべき水準です。</b>資金拘束と追証リスクを避けるため、未練を断ち切るのが賢明です。</li>")
            elif pl_pct < 0:
                margin_risks.append(f"<li class='text-yellow'>⚠️ <b>{n}</b>: {s['pl_str']} ({pl_pct:.1f}%) <br>含み損が発生しています。あらかじめ設定した損切りライン（例: -5%）に到達したら即座に切る準備をしてください。</li>")
            elif pl_pct > 10:
                margin_risks.append(f"<li class='text-green'>✨ <b>{n}</b>: +{s['pl']}円 (+{pl_pct:.1f}%) <br>素晴らしい含み益です！スイングの目標達成圏内です。半分を利確（分割利確）しつつ、残りで上値アウトを狙う戦略を推奨します。</li>")
            else:
                margin_risks.append(f"<li class='text-green'>✅ <b>{n}</b>: +{s['pl']}円 (+{pl_pct:.1f}%) <br>順調です。トレイリングストップ（買値を下回らないように逆指値）を置きながら利益を伸ばしましょう。</li>")

    # Margin Risk Assessment
    if r_margin > 30:
        margin_risks.append("<li class='text-red'>⚠️ 信用取引の割合が総資産の30%を超えています。急落時の追証リスクが極めて高い状態です。レバレッジ管理の徹底を推奨します。</li>")
    elif r_margin > 10:
        margin_risks.append("<li class='text-yellow'>⚠️ 信用取引を利用しています。建玉の維持率と金利コストに注意し、余裕をもった保証金を維持してください。</li>")
    elif total_margin > 0:
        margin_risks.append("<li class='text-green'>✅ 信用取引・保証金の割合は健全な範囲（10%以下）に収まっています。</li>")
    else:
        margin_risks.append("<li class='text-green'>✅ 現在、信用取引の利用はありません。</li>")

    # General Risk/Strategy Assessment
    if r_commo > 20:
        general_risks.append("<li class='text-yellow'>ℹ️ コモディティ（金・銀等）への偏りが20%を超えています。インフレヘッジとしては有効ですが、利回りを生まない資産のため機会損失に注意が必要です。</li>")
    else:
        general_risks.append("<li class='text-green'>✅ コモディティ比率は適切で、インフレへの備えとして機能しています。</li>")
        
    if r_dom + r_us + r_trust < 50:
        general_risks.append("<li class='text-yellow'>⚠️ 成長資産（現物株・インデックス投信）の割合が50%を下回っています。長期的な資産形成のペースが落ちる可能性があります。株式アロケーションの増加を検討してください。</li>")
        
    if r_cash < 5:
        general_risks.append("<li class='text-yellow'>⚠️ 現金比率が5%を下回っています。急な出費や暴落時の買い増し（押し目買い）資金として少し心許ない可能性があります。</li>")
    elif r_cash >= 5 and r_cash <= 20:
        general_risks.append("<li class='text-green'>✅ 現金比率は暴落時の待機資金として理想的な水準（5〜20%）に維持されています。</li>")
        
    if r_trust > 80:
        general_risks.append("<li class='text-green'>✅ インデックス投資信託の割合が高く、非常に堅実で長期目線のポートフォリオです。</li>")

    # Pre-calculate HTML snippets for the template
    metrics_rows_html = ""
    for k, v in metrics.items():
        color_1m = '#ef4444' if v['1m'] < 0 else '#10b981'
        color_3m = '#ef4444' if v['3m'] < 0 else '#10b981'
        color_ytd = '#ef4444' if v['ytd'] < 0 else '#10b981'
        metrics_rows_html += f"""
            <tr style='border-bottom: 1px solid rgba(255,255,255,0.05);'>
                <td style='padding: 12px 10px;'>{k}</td>
                <td style='text-align:right; padding: 12px 10px; color:#fff;'>{v['val']:,} 円</td>
                <td style='text-align:right; padding: 12px 10px; color:{color_1m}'>{v['1m']:+.1f}%</td>
                <td style='text-align:right; padding: 12px 10px; color:{color_3m}'>{v['3m']:+.1f}%</td>
                <td style='text-align:right; padding: 12px 10px; color:{color_ytd}'>{v['ytd']:+.1f}%</td>
            </tr>"""

    targets_html = ""
    if targets:
        for p in target_progress:
            targets_html += f'''
            <div style="margin-bottom: 20px;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                    <span>{p["label"]}</span>
                    <span style="color: #94a3b8;">{p["current"]:,} / {p["target"]:,} 円 ({p["pct"]:.1f}%)</span>
                </div>
                <div style="height: 12px; background: rgba(0,0,0,0.3); border-radius: 6px; overflow: hidden;">
                    <div style="width: {p["pct"]}%; height: 100%; background: linear-gradient(90deg, #3b82f6, #10b981); border-radius: 6px;"></div>
                </div>
                <div style="text-align: right; font-size: 0.8rem; color: #94a3b8; margin-top: 4px;">不足額: {max(0, p["gap"]):,} 円</div>
            </div>
            '''

    html = f'''<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <title>Portfolio Analysis Report</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{
            background: #0f172a; color: #f8fafc; font-family: 'Inter', 'Helvetica Neue', Arial, sans-serif;
            margin: 0; padding: 40px 20px; line-height: 1.6;
        }}
        .container {{ max-width: 900px; margin: 0 auto; }}
        h2 {{ color: #e2e8f0; font-weight: 600; margin-bottom: 20px; }}
        h1 {{ text-align: center; margin-bottom: 40px; font-size: 2.2rem; }}
        .card {{
            background: rgba(30, 41, 59, 0.7); backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);
            border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 16px; padding: 30px; margin-bottom: 30px;
            box-shadow: 0 4px 30px rgba(0, 0, 0, 0.1);
        }}
        .stat-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 15px; margin-bottom: 20px; }}
        .stat-box {{ background: rgba(0,0,0,0.2); padding: 15px; border-radius: 12px; text-align: center; border: 1px solid rgba(255,255,255,0.05); }}
        .stat-title {{ font-size: 0.85rem; color: #94a3b8; margin-bottom: 5px; }}
        .stat-val {{ font-size: 1.4rem; font-weight: 700; }}
        .val-us {{ color: #3b82f6; }}
        .val-dom {{ color: #ef4444; }}
        .val-trust {{ color: #10b981; }}
        .val-commo {{ color: #fbbf24; }}
        .val-margin {{ color: #ec4899; }}
        .val-crypto {{ color: #8b5cf6; }}
        .val-cash {{ color: #38bdf8; }}
        
        .progress-bar {{ display: flex; height: 30px; border-radius: 15px; overflow: hidden; margin: 30px 0; outline: 1px solid rgba(255,255,255,0.1); }}
        .bar {{ display: flex; justify-content: center; align-items: center; font-size: 0.75rem; font-weight: bold; color: #fff; text-shadow: 0 1px 2px rgba(0,0,0,0.5); }}
        
        ul.risks {{ list-style-type: none; padding: 0; }}
        ul.risks li {{ padding: 15px 20px; margin-bottom: 10px; background: rgba(0,0,0,0.3); border-radius: 8px; border-left: 4px solid; }}
        .text-red {{ border-color: #ef4444; }}
        .text-yellow {{ border-color: #fbbf24; }}
        .text-green {{ border-color: #10b981; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Portfolio Analysis Report</h1>
        
        <div class="card">
            <h2>資産アロケーション（割合・評価損益）</h2>
            <div class="stat-grid">
                <div class="stat-box"><div class="stat-title">米国株</div><div class="stat-val val-us">{total_us:,} 円<br><small>({r_us:.1f}%)</small></div><div style="font-size:0.9rem; margin-top:5px; color:{'#ef4444' if pl_us < 0 else '#10b981'}">{pl_us:+,} 円 ({rate_us:+.1f}%)</div></div>
                <div class="stat-box"><div class="stat-title">日本株</div><div class="stat-val val-dom">{total_dom:,} 円<br><small>({r_dom:.1f}%)</small></div><div style="font-size:0.9rem; margin-top:5px; color:{'#ef4444' if pl_dom < 0 else '#10b981'}">{pl_dom:+,} 円 ({rate_dom:+.1f}%)</div></div>
                <div class="stat-box"><div class="stat-title">投資信託</div><div class="stat-val val-trust">{total_trust:,} 円<br><small>({r_trust:.1f}%)</small></div><div style="font-size:0.9rem; margin-top:5px; color:{'#ef4444' if pl_trust < 0 else '#10b981'}">{pl_trust:+,} 円 ({rate_trust:+.1f}%)</div></div>
                <div class="stat-box"><div class="stat-title">コモディティ</div><div class="stat-val val-commo">{total_commo:,} 円<br><small>({r_commo:.1f}%)</small></div><div style="font-size:0.9rem; margin-top:5px; color:{'#ef4444' if pl_commo < 0 else '#10b981'}">{pl_commo:+,} 円 ({rate_commo:+.1f}%)</div></div>
                <div class="stat-box"><div class="stat-title">信用取引</div><div class="stat-val val-margin">{total_margin:,} 円<br><small>({r_margin:.1f}%)</small></div></div>
                <div class="stat-box"><div class="stat-title">暗号資産</div><div class="stat-val val-crypto">{total_crypto:,} 円<br><small>({r_crypto:.1f}%)</small></div></div>
                <div class="stat-box"><div class="stat-title">現金・預金</div><div class="stat-val val-cash">{total_cash:,} 円<br><small>({r_cash:.1f}%)</small></div></div>
            </div>
            
            <div style="position: relative; height:300px; width:100%; margin: 30px 0;">
                <canvas id="allocationPieChart"></canvas>
            </div>
            <div style="display: flex; justify-content: space-between; align-items: center; color: #94a3b8;">
                <div>上記4種 損益 合計: <b style="color:{'#ef4444' if total_pl_sum < 0 else '#10b981'}; font-size:1.1rem;">{total_pl_sum:+,} 円 ({rate_total:+.1f}%)</b></div>
                <div>総資産額 (概算): <b style="font-size:1.1rem; color:#fff;">{total_assets:,} 円</b></div>
            </div>
        </div>

        <div class="card">
            <h2>🌍 全体的なリスク・戦略レポート</h2>
            <ul class="risks">
                {"".join(general_risks)}
            </ul>
        </div>
        
        <div class="card">
            <h2>💹 信用取引・レバレッジ管理レポート</h2>
            <ul class="risks">
                {"".join(margin_risks)}
            </ul>
        </div>
        
        <div class="card">
            <h2>📈 資産推移グラフ</h2>
            <div style="position: relative; height:400px; width:100%; margin-bottom: 30px;">
                <canvas id="totalAssetsChart"></canvas>
            </div>
            <div style="position: relative; height:400px; width:100%;">
                <canvas id="allocationChart"></canvas>
            </div>
        </div>

        <div class="card">
            <h2>📊 パフォーマンス比較（成長率）</h2>
            <div style="position: relative; height:350px; width:100%; margin-bottom: 30px;">
                <canvas id="growthRateChart"></canvas>
            </div>
            <table style="width:100%; border-collapse: collapse; margin-top: 20px; font-size: 0.95rem;">
                <thead>
                    <tr style="border-bottom: 2px solid rgba(255,255,255,0.1); color: #94a3b8;">
                        <th style="text-align:left; padding: 10px;">アセット</th>
                        <th style="text-align:right; padding: 10px;">評価額</th>
                        <th style="text-align:right; padding: 10px;">1ヶ月</th>
                        <th style="text-align:right; padding: 10px;">3ヶ月</th>
                        <th style="text-align:right; padding: 10px;">年初来 (YTD)</th>
                    </tr>
                </thead>
                <tbody>
                    {metrics_rows_html}
                </tbody>
            </table>
        </div>

        <div class="card">
            <h2>🎯 2026年 年末目標 進捗管理</h2>
            {targets_html}
            
            <div style="margin-top: 30px; padding: 20px; background: rgba(59, 130, 246, 0.1); border-radius: 12px; border: 1px solid rgba(59, 130, 246, 0.2);">
                <h3 style="margin-top:0; color: #60a5fa;">💡 目標達成に向けた投資プラン</h3>
                <p>年末（残り{remaining_months}ヶ月）までに目標額を達成するには、月次で <b>平均 {int(monthly_investment):,} 円</b> の積立または資産成長が必要です。</p>
                <ul style="font-size: 0.9rem; color: #cbd5e1; padding-left: 20px;">
                    <li>投資信託を最優先（残り {target_progress[0]['gap']:,} 円）としつつ、守りのコモディティも並行して積み増し。</li>
                    <li>米国株・日本株は現在の損益率（1ヶ月成長率）を維持できれば、自然増による目標達成の可能性も高いです。</li>
                </ul>
            </div>
        </div>
        
    </div>

    <script>
        const rawHistory = {json.dumps(history_data)};
        
        const labels = rawHistory.map(d => d.date);
        const lineData = rawHistory.map(d => d.total_assets);
        const usData = rawHistory.map(d => d.us);
        const domData = rawHistory.map(d => d.domestic);
        const trustData = rawHistory.map(d => d.trust);
        const commoData = rawHistory.map(d => d.commodity);
        const marginData = rawHistory.map(d => d.margin);
        const cryptoData = rawHistory.map(d => d.crypto);
        const cashData = rawHistory.map(d => d.cash + d.margin);

        Chart.defaults.color = '#94a3b8';
        Chart.defaults.font.family = 'Inter';

        new Chart(document.getElementById('allocationPieChart'), {{
            type: 'doughnut',
            data: {{
                labels: ['米国株', '日本株', '投資信託', 'コモディティ', '信用取引', '暗号資産', '現金・預金'],
                datasets: [{{
                    data: [{r_us}, {r_dom}, {r_trust}, {r_commo}, {r_margin}, {r_crypto}, {r_cash}],
                    backgroundColor: ['#3b82f6', '#ef4444', '#10b981', '#fbbf24', '#ec4899', '#8b5cf6', '#38bdf8'],
                    borderWidth: 1,
                    borderColor: '#1e293b'
                }}]
            }},
            options: {{
                responsive: true, maintainAspectRatio: false,
                plugins: {{
                    legend: {{ position: 'right', labels: {{ padding: 20 }} }},
                    tooltip: {{
                        callbacks: {{ label: function(context) {{ return ' ' + context.label + ': ' + context.parsed.toFixed(1) + '%'; }} }}
                    }}
                }},
                cutout: '65%'
            }}
        }});
        
        new Chart(document.getElementById('totalAssetsChart'), {{
            type: 'line',
            data: {{
                labels: labels,
                datasets: [{{
                    label: '総資産額 (Total)',
                    data: lineData,
                    borderColor: '#38bdf8',
                    backgroundColor: 'rgba(56, 189, 248, 0.1)',
                    borderWidth: 2,
                    pointRadius: 2,
                    pointBackgroundColor: '#38bdf8',
                    fill: {{target: 'origin', above: 'rgba(56, 189, 248, 0.1)'}},
                    tension: 0.4
                }}]
            }},
            options: {{
                responsive: true, maintainAspectRatio: false,
                plugins: {{ legend: {{ display: false }}, tooltip: {{ mode: 'index', intersect: false }} }},
                scales: {{
                    y: {{ beginAtZero: true, grid: {{ color: 'rgba(255,255,255,0.05)' }} }},
                    x: {{ grid: {{ display: false }} }}
                }}
            }}
        }});
        
        const datasetsList = [
            {{ label: '米国株', data: usData, backgroundColor: '#3b82f6', lastVal: usData[usData.length-1] || 0 }},
            {{ label: '日本株', data: domData, backgroundColor: '#ef4444', lastVal: domData[domData.length-1] || 0 }},
            {{ label: '投資信託', data: trustData, backgroundColor: '#10b981', lastVal: trustData[trustData.length-1] || 0 }},
            {{ label: 'ｺﾓﾃﾞｨﾃｨ', data: commoData, backgroundColor: '#fbbf24', lastVal: commoData[commoData.length-1] || 0 }},
            {{ label: '現金・預金', data: cashData, backgroundColor: '#38bdf8', lastVal: cashData[cashData.length-1] || 0 }},
            {{ label: '暗号資産', data: cryptoData, backgroundColor: '#8b5cf6', lastVal: cryptoData[cryptoData.length-1] || 0 }}
        ];
        
        datasetsList.sort((a, b) => b.lastVal - a.lastVal);

        new Chart(document.getElementById('allocationChart'), {{
            type: 'bar',
            data: {{
                labels: labels,
                datasets: datasetsList
            }},
            options: {{
                responsive: true, maintainAspectRatio: false,
                plugins: {{ tooltip: {{ mode: 'index', intersect: false }} }},
                scales: {{
                    x: {{ stacked: true, grid: {{ display: false }} }},
                    y: {{ stacked: true, grid: {{ color: 'rgba(255,255,255,0.05)' }} }}
                }}
            }}
        }});
        
        new Chart(document.getElementById('growthRateChart'), {{
            type: 'bar',
            data: {{
                labels: ['米国株', '日本株', '投資信託', 'コモディティ', '総資産'],
                datasets: [{{
                    label: '月間成長率 (1 month %)',
                    data: [{metrics['US Stocks']['1m']}, {metrics['JP Stocks']['1m']}, {metrics['Trusts/ETF']['1m']}, {metrics['Commodity']['1m']}, {metrics['Total']['1m']}],
                    backgroundColor: ['#3b82f6', '#ef4444', '#10b981', '#fbbf24', '#38bdf8'],
                    borderRadius: 6
                }}]
            }},
            options: {{
                indexAxis: 'y',
                responsive: true, maintainAspectRatio: false,
                plugins: {{ legend: {{ display: false }} }},
                scales: {{
                    x: {{ grid: {{ color: 'rgba(255,255,255,0.05)' }}, ticks: {{ callback: value => value + '%' }} }},
                    y: {{ grid: {{ display: false }} }}
                }}
            }}
        }});
    </script>
</body>
</html>'''

    out_html = "portfolio_report.html"
    with open(out_html, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"HTML Report generated at {out_html}")

if __name__ == "__main__":
    extract()
