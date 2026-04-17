import socket
import time
socket.setdefaulttimeout(10)
import urllib.request
import urllib.parse
import ssl
import re
import datetime
import os
import glob
import json

# Helper to make HTTP requests
def fetch_url(url):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    req = urllib.request.Request(url)
    req.add_header('User-Agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36')
    try:
        with urllib.request.urlopen(req, context=ctx) as response:
            return response.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

def load_owned_stocks():
    owned_codes = set()
    try:
        if os.path.exists("Money/stock.md"):
            with open("Money/stock.md", "r") as f:
                lines = f.readlines()
                for line in lines[1:]: # Skip header
                    parts = line.split('\t')
                    if len(parts) >= 1:
                        code = parts[0].strip()
                        # JP tickers start with digit
                        if re.match(r'^[0-9]', code):
                             owned_codes.add(code)
    except Exception as e:
        print(f"Error reading Money/stock.md: {e}")
    return owned_codes

def load_strategy_notes():
    notes = {}
    try:
        if os.path.exists("strategy_notes.json"):
            with open("strategy_notes.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data:
                    notes[item["ticker"]] = item
    except Exception as e:
        print(f"Error reading strategy_notes.json: {e}")
    return notes

def cleanup_old_reports(directory, days_to_keep=2):
    """
    Keep only the most recent 'days_to_keep' days of reports in the directory.
    Reports are assumed to start with YYYYMMDD.
    """
    print(f"Cleaning up old reports in {directory} (keeping last {days_to_keep} days)...")
    try:
        files = glob.glob(os.path.join(directory, "*-pts-alert.*"))
        if not files:
            return

        # Extract dates (first 8 chars)
        basenames = [os.path.basename(f) for f in files]
        dates = sorted(list(set(f[:8] for f in basenames if len(f) >= 8 and f[:8].isdigit())), reverse=True)
        
        if len(dates) <= days_to_keep:
            return

        keep_dates = set(dates[:days_to_keep])
        
        for f in files:
            date_prefix = os.path.basename(f)[:8]
            if date_prefix.isdigit() and date_prefix not in keep_dates:
                print(f"Deleting old report: {os.path.basename(f)}")
                os.remove(f)
    except Exception as e:
        print(f"Error during cleanup: {e}")

def main():
    print("Starting PTS Watcher (Owned Stocks Only)...")
    
    report_items = {}

    # Check Owned Stocks + Strategy Stocks
    owned_codes = load_owned_stocks()
    strategy_notes = load_strategy_notes()
    
    # Merge codes to watch
    all_codes = owned_codes.union(set(strategy_notes.keys()))
    
    print(f"Total stocks to watch (Owned + Strategy): {sorted(list(all_codes))}")
    
    print("Checking stocks for PTS moves...")
    def check_stock(code):
        strategy_info = strategy_notes.get(code)
        url = f"https://kabutan.jp/stock/?code={code}"
        html = fetch_url(url)
        if not html: return None
        
        try:
            # Extract Regular Price
            reg_match = re.search(r'<span class="kabuka">([0-9,.]+)円</span>', html)
            if not reg_match: return None
            reg_price = float(reg_match.group(1).replace(',', ''))
            
            # Extract PTS Price
            pts_match = re.search(r'<div class="kabuka1">PTS</div>[\s\n]*<div class="kabuka2">([0-9,.]+)円</div>', html, re.DOTALL)
            
            # Default to no info if missing
            pts_price = reg_price
            has_pts = False
            
            if pts_match: 
                pts_price = float(pts_match.group(1).replace(',', ''))
                has_pts = True
            
            # Extract Name
            name = code # Fallback
            title_match = re.search(r'<title>(.*?)【', html)
            if title_match:
                name = title_match.group(1).strip()
            
            # Calculate Change
            change_pct = 0.0
            direction = ""
            if reg_price > 0 and has_pts:
                change_pct = ((pts_price - reg_price) / reg_price) * 100
                direction = "rise" if change_pct > 0 else "fall"
            
            # ALWAYS add owned stock
            status_msg = f"{change_pct:+.2f}%" if has_pts else "No PTS Traded"
            print(f"Owned stock {code}: {status_msg}")
            
            return {
                "code": code,
                "name": name,
                "price": f"{pts_price:,.0f}" if has_pts else "-",
                "pct": change_pct,
                "direction": direction,
                "reg_price": f"{reg_price:,.0f}",
                "has_pts": has_pts,
                "is_owned": code in owned_codes,
                "strategy_note": strategy_info["strategy"] if strategy_info else ""
            }
                
        except Exception as e:
            print(f"Error checking {code}: {e}")
            return None

    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        results = executor.map(check_stock, all_codes)
        for res in results:
            if res:
                report_items[res['code']] = res

    # Convert to list
    final_list = list(report_items.values())

    # Sort by absolute change percent descending
    final_list.sort(key=lambda x: abs(x['pct']), reverse=True)

    # Generate Report
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    date_str = datetime.datetime.now().strftime('%Y%m%d')
    
    # NEW OUTPUT DIRECTORY
    output_dir = "投資メディア事業/daily_info"
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Markdown Report
    filename_md = os.path.join(output_dir, f"{date_str}-pts-alert.md")
    with open(filename_md, "w") as f:
        f.write(f"# PTS保有銘柄チェック: {today}\n\n")
        f.write("Kabutan PTS (ナイトセッション) 保有全銘柄リスト\n\n")
        
        if not final_list:
            f.write("該当なし (PTS取引なし、またはエラー)\n")
        else:
            f.write("| 区分 | 変動率 | コード | 銘柄名 | PTS価格 | 戦略メモ |\n")
            f.write("|---|---|---|---|---|---|\n")
            
            for item in final_list:
                status_icon = "💰" if item['is_owned'] else "🎯"
                
                if not item['has_pts']:
                    pct_display = "-"
                    price_display = "-"
                else:
                    pct_display = f"{item['pct']:+.2f}%"
                    price_display = item['price']
                    
                    if abs(item['pct']) >= 5.0:
                        pct_display = f"**{pct_display}**"
                
                code_link = f"[{item['code']}](https://kabutan.jp/stock/?code={item['code']})"
                f.write(f"| {status_icon} | {pct_display} | {code_link} | {item['name']} | {price_display} | {item['strategy_note']} |\n")

    print(f"Markdown Report saved to {filename_md}")

    # 2. HTML Report
    filename_html = os.path.join(output_dir, f"{date_str}-pts-alert.html")
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>PTS Watcher {today}</title>
        <style>
            body {{
                font-family: 'Helvetica Neue', Arial, sans-serif;
                background-color: #1a1a1a;
                color: #e0e0e0;
                margin: 0;
                padding: 20px;
                display: flex;
                justify-content: center;
            }}
            .container {{
                width: 100%;
                max-width: 800px;
                background: #252525;
                padding: 20px;
                border-radius: 12px;
                box-shadow: 0 4px 15px rgba(0,0,0,0.5);
            }}
            h1 {{
                text-align: center;
                color: #ffffff;
                margin-bottom: 20px;
                font-weight: 300;
            }}
            .subtitle {{
                text-align: center;
                color: #888;
                margin-bottom: 30px;
                font-size: 0.9em;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 10px;
            }}
            th, td {{
                padding: 15px;
                text-align: right;
                border-bottom: 1px solid #333;
            }}
            th {{
                text-align: center;
                color: #666;
                font-size: 0.8em;
                text-transform: uppercase;
                letter-spacing: 1px;
            }}
            td {{
                font-size: 1.1em;
            }}
            .name-cell {{
                text-align: left;
                font-weight: bold;
                color: #fff;
            }}
            .code-cell {{
                text-align: center;
                color: #888;
                font-size: 0.9em;
            }}
            .price-cell {{
                color: #ccc;
                font-family: 'Courier New', monospace;
            }}
            .reg-cell {{
                color: #666;
                font-size: 0.9em;
                font-family: 'Courier New', monospace;
            }}
            .rise {{
                color: #ff5252; 
                font-weight: bold;
            }}
            .fall {{
                color: #4caf50; 
                font-weight: bold;
            }}
            .no-change {{
                color: #888;
            }}
            tr:hover {{
                background-color: #2a2a2a;
            }}
            a {{
                color: inherit;
                text-decoration: none;
            }}
            a:hover {{
                text-decoration: underline;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>PTS Watcher</h1>
            <div class="subtitle">{today} - Owned Stocks Night Session</div>
            <table>
                <thead>
                    <tr>
                        <th width="10%">Code</th>
                        <th style="text-align:left;">Name</th>
                        <th width="20%">PTS Price</th>
                        <th width="20%">Regular</th>
                        <th width="15%">Change</th>
                    </tr>
                </thead>
                <tbody>
    """
    
    for item in final_list:
        if not item['has_pts']:
            change_class = "no-change"
            change_display = "-"
            price_display = "-"
        else:
            change_class = "no-change"
            if item['pct'] > 0: change_class = "rise"
            elif item['pct'] < 0: change_class = "fall"
            
            prefix = "+" if item['pct'] > 0 else ""
            change_display = f"{prefix}{item['pct']:.2f}%"
            price_display = item['price']
        
        status_icon = "💰" if item['is_owned'] else "🎯"
        strategy_label = f"<div style='font-size:0.8em; color:#fbbf24; margin-top:4px;'>{item['strategy_note']}</div>" if item['strategy_note'] else ""
        
        row_html = f"""
            <tr>
                <td class="code-cell">{status_icon} <a href="https://kabutan.jp/stock/?code={item['code']}" target="_blank">{item['code']}</a></td>
                <td class="name-cell">{item['name']}{strategy_label}</td>
                <td class="price-cell">{price_display}</td>
                <td class="reg-cell">{item['reg_price']}</td>
                <td class="{change_class}">{change_display}</td>
            </tr>
        """
        html_content += row_html
        
    html_content += """
                </tbody>
            </table>
        </div>
    </body>
    </html>
    """
    
    with open(filename_html, "w") as f:
        f.write(html_content)
        
    print(f"HTML Report saved to {filename_html}")
    
    # 3. Cleanup old reports
    cleanup_old_reports(output_dir, days_to_keep=2)

if __name__ == "__main__":
    main()
