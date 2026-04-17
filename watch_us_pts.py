import socket
import time
socket.setdefaulttimeout(10)
import urllib.request
import urllib.parse
import ssl
import re
import datetime
import os
import json

# Helper to make HTTP requests
def fetch_url(url):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    req = urllib.request.Request(url)
    req.add_header('User-Agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36')
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=10) as response:
            return response.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

def load_owned_us_stocks():
    owned_codes = set()
    try:
        if os.path.exists("Money/stock.md"):
            with open("Money/stock.md", "r") as f:
                lines = f.readlines()
                for line in lines[1:]: # Skip header
                    parts = line.split('\t')
                    if len(parts) >= 1:
                        code = parts[0].strip()
                        # US tickers are alphabet
                        if re.match(r'^[A-Z]+$', code):
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

def main():
    # Check Owned US Stocks + Strategy Stocks
    owned_codes = load_owned_us_stocks()
    strategy_notes = load_strategy_notes()
    
    # Merge codes to watch (only alphabetic ones for US)
    us_strategy_codes = {k for k in strategy_notes.keys() if k.isalpha()}
    all_codes = owned_codes.union(us_strategy_codes)
    
    # Fallback if empty
    if not all_codes:
        all_codes = {"SOFI", "NVDA", "TSLA", "AAPL"}
        
    print(f"Total US stocks to watch (Owned + Strategy): {sorted(list(all_codes))}")
    
    report_items = {}
    
    def check_stock(code):
        strategy_info = strategy_notes.get(code)
        url = f"https://us.kabutan.jp/stocks/{code}"
        html = fetch_url(url)
        if not html: return None
        
        try:
            # Name
            name = code
            name_match = re.search(r'<div class="pl-1 mx-1 font-bold overflow-hidden whitespace-nowrap truncate w-full">(.*?)</div>', html)
            if name_match:
                name = name_match.group(1).strip()
            
            # Regular Price
            reg_price_match = re.search(r'<div class="flex-1 text-right text-3xl mr-1">\$([0-9.,]+)</div>', html)
            reg_price = "-"
            if reg_price_match:
                reg_price = reg_price_match.group(1)
                
            # Extended Hours Price (After Hours / Pre Market)
            ext_price = "-"
            ext_change = "-"
            ext_pct = 0.0
            ext_label = "-"
            
            # Check for extended hours block
            ext_block_match = re.search(r'(<div class="bg-light-lavender.*?<div class="flex text-sm w-full">.*?)</div>\s*</div>', html, re.DOTALL)
            
            if ext_block_match:
                block_html = ext_block_match.group(1)
                
                # Determine label
                if "アフターマーケット" in block_html or "fa-moon" in block_html:
                    ext_label = "PTS (After)"
                elif "プレマーケット" in block_html or "fa-sun" in block_html:
                    ext_label = "PTS (Pre)"
                else:
                    ext_label = "PTS"

                # Price
                price_match = re.search(r'<div class="mr-1 flex-1 text-right">\s*\$([0-9.,]+)\s*</div>', block_html, re.DOTALL)
                if price_match:
                    ext_price = price_match.group(1).strip()
                
                # Change Pct
                pct_match = re.search(r'\(\s*<span class=[\'"][^"\']+[\'"]>([+\-0-9.,]+)</span>%\s*\)', block_html, re.DOTALL)
                if pct_match:
                    ext_pct = float(pct_match.group(1).replace('+', ''))
                    ext_change = f"{ext_pct:+.2f}%"
            
            print(f"{code}: Reg={reg_price} | {ext_label}={ext_price} ({ext_change})")
            
            return {
                "code": code,
                "name": name,
                "reg_price": reg_price,
                "ext_price": ext_price,
                "ext_change": ext_change,
                "ext_pct": ext_pct,
                "ext_label": ext_label,
                "is_owned": code in owned_codes,
                "strategy_note": strategy_info["strategy"] if strategy_info else ""
            }
            
        except Exception as e:
            print(f"Error parsing {code}: {e}")
            return None

    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        results = executor.map(check_stock, all_codes)
        for res in results:
            if res:
                report_items[res['code']] = res
            
    # Generate Reports
    final_list = list(report_items.values())
    # Sort by absolute change pct
    final_list.sort(key=lambda x: abs(x['ext_pct']) if isinstance(x['ext_pct'], float) else 0, reverse=True)
    
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    date_str = datetime.datetime.now().strftime('%Y%m%d')
    os.makedirs("ideas/daily", exist_ok=True)
    
    # Markdown
    filename_md = f"ideas/daily/{date_str}-us-pts-alert.md"
    with open(filename_md, "w") as f:
        f.write(f"# 米国株PTSチェック: {today}\n\n")
        f.write("Kabutan US PTS (After/Pre Market) 保有全銘柄リスト\n\n")
        
        f.write("| 区分 | Code | Name | PTS Price | Change | 戦略メモ |\n")
        f.write("|---|---|---|---|---|---|\n")
        
        for item in final_list:
            status_icon = "💰" if item['is_owned'] else "🎯"
            code_link = f"[{item['code']}](https://us.kabutan.jp/stocks/{item['code']})"
            
            pct_display = item['ext_change']
            if abs(item['ext_pct']) >= 5.0:
                 pct_display = f"**{pct_display}**"
            
            f.write(f"| {status_icon} | {code_link} | {item['name']} | {item['ext_price']} | {pct_display} | {item['strategy_note']} |\n")

    print(f"Markdown Report saved to {filename_md}")
    
    # HTML
    filename_html = f"ideas/daily/{date_str}-us-pts-alert.html"
    html_content = f"""
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>US PTS Watcher {today}</title>
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
            .badge {{
                display: inline-block;
                padding: 2px 6px;
                border-radius: 4px;
                font-size: 0.7em;
                background-color: #333;
                color: #aaa;
                margin-left: 5px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>US PTS Watcher</h1>
            <div class="subtitle">{today} - Owned Stocks</div>
            <table>
                <thead>
                    <tr>
                        <th width="5%"></th>
                        <th width="10%">Code</th>
                        <th style="text-align:left;">Name</th>
                        <th width="20%">PTS Price</th>
                        <th width="15%">Change</th>
                        <th width="20%">Regular</th>
                    </tr>
                </thead>
                <tbody>
    """
    
    for item in final_list:
        change_class = "no-change"
        if item['ext_pct'] > 0: change_class = "rise"
        elif item['ext_pct'] < 0: change_class = "fall"
        
        status_icon = "💰" if item['is_owned'] else "🎯"
        strategy_label = f"<div style='font-size:0.8em; color:#fbbf24; margin-top:4px;'>{item['strategy_note']}</div>" if item['strategy_note'] else ""
        
        row_html = f"""
            <tr>
                <td class="code-cell">{status_icon}</td>
                <td class="code-cell"><a href="https://us.kabutan.jp/stocks/{item['code']}" target="_blank">{item['code']}</a></td>
                <td class="name-cell">
                    {item['name']} <span class="badge">{item['ext_label']}</span>
                    {strategy_label}
                </td>
                <td class="price-cell">${item['ext_price']}</td>
                <td class="{change_class}">{item['ext_change']}</td>
                <td class="reg-cell">${item['reg_price']}</td>
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

if __name__ == "__main__":
    main()
