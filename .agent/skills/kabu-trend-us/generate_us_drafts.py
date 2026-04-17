import subprocess
import json
import argparse
import os
import sys
import re
from datetime import datetime

def run_command_stream(command):
    print(f"Running: {command}")
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    while True:
        output = process.stdout.readline()
        if output == '' and process.poll() is not None:
            break
        if output:
            print(output.strip())
    rc = process.poll()
    if rc != 0:
        print(f"Error running command: {command}")
        return False
    return True

def run_command_capture(command):
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error running command: {command}")
        print(result.stderr)
        return None
    return result.stdout

def load_owned_tickers():
    tickers = []
    try:
        stock_file = "Money/stock.md"
        if os.path.exists(stock_file):
            with open(stock_file, "r") as f:
                lines = f.readlines()
                for line in lines[1:]: # Skip header
                    parts = line.split('\t')
                    if len(parts) >= 1:
                        symbol = parts[0].strip()
                        # US tickers are alphabetic (and usually 1-5 chars)
                        # Exclude Japanese numeric codes or new codes like 212A
                        if re.match(r'^[A-Z]+$', symbol):
                            tickers.append(symbol)
    except Exception as e:
        print(f"Error reading stock file: {e}")
    return tickers

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tickers", nargs="+", help="List of tickers")
    parser.add_argument("--skip-collect", action="store_true", help="Skip data collection and use latest file")
    args = parser.parse_args()
    
    # Determine tickers to use
    if args.tickers:
        target_tickers = args.tickers
    else:
        # Load from file default
        print("Loading tickers from Money/stock.md...")
        target_tickers = load_owned_tickers()
        if not target_tickers:
            print("No US tickers found in Money/stock.md, using default.")
            target_tickers = ["TSLA", "SOFI", "NVDA"]
            
    print(f"Target Tickers: {target_tickers}")
    
    # 1. Collect Data
    if not args.skip_collect:
        print("Collecting US Data...")
        if not run_command_stream("python3 collect_kabu_us.py"):
            print("Data collection failed.")
            return
    else:
        print("Skipping data collection (using latest file)...")
    
    # 2. Format
    print("Formatting Drafts...")
    cmd = f"python3 .agent/skills/kabu-trend-us/format_us_tweets.py --tickers {' '.join(target_tickers)}"
    output = run_command_capture(cmd)
    
    if not output:
        print("No output from formatter.")
        return
    
    try:
        data = json.loads(output)
    except json.JSONDecodeError:
        print("Failed to parse JSON output.")
        print(output)
        return
        
    if not data:
        print("No news found for tickers.")
        return
    
    # 3. Create Draft MD
    today_str = datetime.now().strftime('%Y%m%d')
    md_filename = f"ideas/posts/{today_str}_us_post.md"
    html_filename = f"ideas/reports/{today_str}_us_report.html"
    os.makedirs("ideas/posts", exist_ok=True)
    os.makedirs("ideas/reports", exist_ok=True)
    
    # Generate MD
    with open(md_filename, "w") as f:
        f.write(f"# US Stock Posts Draft ({today_str})\n\n")
        
        for item in data:
            ticker = item['ticker']
            text = item['text']
            sources = item['sources']
            
            f.write(f"## Tweet ({ticker})\n")
            f.write("```text\n")
            f.write(text)
            f.write("\n```\n\n")
            
            f.write("### Sources\n")
            for s in sources:
                f.write(f"- [{s['title']}]({s['url']}) ({s['source']})\n")
            
            f.write("\n---\n\n")
            
        f.write("# Execution\n")
        f.write("To post these tweets, run:\n")
        f.write(f"```bash\npython3 .agent/skills/kabu-trend-us/post_from_draft.py {md_filename}\n```\n")
        
    print(f"Draft generated: {md_filename}")

    # Generate HTML
    html_content = f"""
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>US Stock Report - {today_str}</title>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background-color: #f5f7fa; color: #333; margin: 0; padding: 20px; }}
            .container {{ max-width: 800px; margin: 0 auto; }}
            h1 {{ text-align: center; color: #2c3e50; margin-bottom: 30px; font-weight: 700; }}
            .card {{ background: white; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 24px; overflow: hidden; transition: transform 0.2s; }}
            .card:hover {{ transform: translateY(-2px); box-shadow: 0 8px 12px rgba(0,0,0,0.1); }}
            .card-header {{ background: #2c3e50; color: white; padding: 16px 20px; font-size: 1.25rem; font-weight: 600; display: flex; justify-content: space-between; align-items: center; }}
            .ticker-badge {{ background: rgba(255,255,255,0.2); padding: 4px 10px; border-radius: 20px; font-size: 0.9rem; }}
            .card-body {{ padding: 20px; }}
            .tweet-content {{ background: #f8f9fa; border-left: 4px solid #1da1f2; padding: 16px; margin-bottom: 20px; font-family: "Helvetica Neue", Arial, sans-serif; line-height: 1.6; white-space: pre-wrap; }}
            .sources-title {{ font-weight: 600; margin-bottom: 10px; color: #555; font-size: 0.95rem; text-transform: uppercase; letter-spacing: 0.5px; }}
            .source-list {{ list-style: none; padding: 0; margin: 0; }}
            .source-item {{ margin-bottom: 8px; font-size: 0.95rem; }}
            .source-item a {{ color: #3498db; text-decoration: none; }}
            .source-item a:hover {{ text-decoration: underline; }}
            .source-meta {{ color: #7f8c8d; font-size: 0.85rem; margin-left: 6px; }}
            .footer {{ text-align: center; margin-top: 40px; color: #7f8c8d; font-size: 0.9rem; }}
            .btn-post {{ display: inline-block; background: #1da1f2; color: white; padding: 10px 20px; border-radius: 24px; text-decoration: none; font-weight: bold; margin-top: 20px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🇺🇸 US Stock Investment Report</h1>
            <p style="text-align: center; color: #666; margin-bottom: 40px;">{datetime.now().strftime('%Y/%m/%d')}</p>
    """
    
    for item in data:
        html_content += f"""
            <div class="card">
                <div class="card-header">
                    <span>{item['ticker']}</span>
                    <span class="ticker-badge">US Stock</span>
                </div>
                <div class="card-body">
                    <div class="tweet-content">{item['text']}</div>
                    
                    <div class="sources-title">Sources</div>
                    <ul class="source-list">
        """
        for s in item['sources']:
            html_content += f"""
                        <li class="source-item">
                            <a href="{s['url']}" target="_blank">{s['title']}</a>
                            <span class="source-meta">({s['source']})</span>
                        </li>
            """
        html_content += """
                    </ul>
                </div>
            </div>
        """
        
    html_content += f"""
            <div class="footer">
                <p>Generated by Agentic AI • <a href="file://{os.path.abspath(md_filename)}">View Source Markdown</a></p>
            </div>
        </div>
    </body>
    </html>
    """
    
    with open(html_filename, "w") as f:
        f.write(html_content)
        
    print(f"Report generated: {html_filename}")

if __name__ == "__main__":
    main()
