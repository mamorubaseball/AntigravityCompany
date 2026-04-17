import urllib.request
import urllib.parse
import urllib.error
import xml.etree.ElementTree as ET
import datetime
import os
import ssl
import re

# Helper to make HTTP requests
def fetch_url(url):
    # Fix for SSL certificate verification issues on some systems
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    req = urllib.request.Request(url)
    req.add_header('User-Agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36')
    try:
        with urllib.request.urlopen(req, context=ctx) as response:
            return response.read()
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

# Interest Analysis (Reused from collect_trend_std.py)
def get_interprets_from_gemini():
    interests = ["AI", "Security", "OSS", "SaaS", "Career", "JavaScript", "TypeScript"] # Defaults
    try:
        if os.path.exists("GEMINI.md"):
            with open("GEMINI.md", "r") as f:
                content = f.read()
                lines = content.split('\n')
                in_interests = False
                extracted = []
                for line in lines:
                    if "## Interests" in line:
                        in_interests = True
                        continue
                    if in_interests and line.startswith("##"):
                        break
                    if in_interests and line.strip().startswith("- "):
                        keyword = line.strip()[2:].split('(')[0].split('/')[0].strip()
                        extracted.append(keyword)
                if extracted:
                    interests = extracted
    except Exception as e:
        print(f"Error reading GEMINI.md: {e}")
    return interests

INTERESTS = get_interprets_from_gemini()
INTERESTS.extend(["株", "市場", "投資", "銘柄", "決算", "IPO", "日経平均", "為替", "円安", "円高"]) # Add stock specific keywords

def check_interest(text):
    text_lower = text.lower()
    score = 0
    
    # Direct matches
    for keyword in INTERESTS:
        if keyword.lower() in text_lower:
            score += 2
            
    # Key terms
    high_value_terms = [
        "security", "ai", "gpt", "llm", "semi", "earnings", "profit", "loss", 
        "dividend", "buyback", "split", "merger", "acquisition", "takeover",
        "bull", "bear", "rally", "crash", "correction", "inflation", "cpi", "fomc", "boj"
    ]
    for term in high_value_terms:
         if term in text_lower:
             score += 1

    if score >= 4: return "★★★"
    if score >= 2: return "★★"
    return "★"

def fetch_google_news_rss(query, source_name):
    # Google News RSS URL format
    # hl=ja&gl=JP&ceid=JP:ja sets language and region to Japan
    base_url = "https://news.google.com/rss/search?q={}&hl=ja&gl=JP&ceid=JP:ja"
    encoded_query = urllib.parse.quote(query)
    url = base_url.format(encoded_query)
    
    print(f"Fetching {source_name} from Google News...")
    xml_data = fetch_url(url)
    if not xml_data: return []
    
    entries = []
    try:
        root = ET.fromstring(xml_data)
        # RSS 2.0: <channel><item>...</item></channel>
        for item in root.findall(".//channel/item"):
            title = item.find("title").text
            # Remove the source name suffix often added by Google News (e.g. " - Bloomberg")
            if " - " in title:
                title = title.rsplit(" - ", 1)[0]
                
            link = item.find("link").text
            pubDate = item.find("pubDate").text
            
            # Simple date parsing/filtering could be added here if needed
            
            entries.append({
                "title": title,
                "url": link,
                "interest": check_interest(title),
                "source": source_name,
                "date": pubDate
            })
    except Exception as e:
        print(f"Error parsing Google News XML for {source_name}: {e}")
        
    return entries

def generate_markdown(all_entries):
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    date_str = datetime.datetime.now().strftime('%Y%m%d')
    os.makedirs("ideas/daily", exist_ok=True)
    filename = f"ideas/daily/{date_str}-kabu-jp.md"
    
    with open(filename, "w") as f:
        f.write(f"# 日本株トレンド: {today}\n\n")
        
        # Determine top topics based on interest
        top_entries = [e for e in all_entries if "★" in e['interest']]
        top_entries.sort(key=lambda x: len(x['interest']), reverse=True)
        
        f.write("## 注目トピック\n\n")
        f.write("| <div style=\"width:500px\">タイトル</div> | 興味度 | 媒体 | メモ |\n")
        f.write("|------------------------------------------|--------|------|------|\n")
        
        for e in top_entries[:15]:
            f.write(f"| [{e['title']}]({e['url']}) | {e['interest']} | {e['source']} | |\n")
            
        f.write("\n## 媒体別ニュース\n\n")
        
        # Group by source
        sources = sorted(list(set(e['source'] for e in all_entries)))
        for source in sources:
            f.write(f"### {source}\n\n")
            source_entries = [e for e in all_entries if e['source'] == source]
            for i, e in enumerate(source_entries[:10], 1): # Limit to 10 per source
                f.write(f"{i}. [{e['title']}]({e['url']}) ({e['date']})\n")
            f.write("\n")
            
    return filename

    return filename

def load_owned_stocks():
    owned_stocks = [] # List of tuples (code, name)
    try:
        if os.path.exists("Money/stock.md"):
            with open("Money/stock.md", "r") as f:
                lines = f.readlines()
                for line in lines[1:]: # Skip header
                    parts = line.split('\t')
                    if len(parts) >= 2:
                        code = parts[0].strip()
                        name = parts[1].strip()
                        # JP tickers are usually 4 digits (or 4 digits + letter now)
                        # New format includes letters (e.g. 212A), but always starts with digit?
                        # To exclude US tickers like TSLA, ensure it starts with digit or contains digit (US is all alpha)
                        if re.match(r'^[0-9][0-9A-Z]{3,4}$', code):
                            owned_stocks.append((code, name))
    except Exception as e:
        print(f"Error reading Money/stock.md: {e}")
    return owned_stocks

def main():
    # Load owned stocks
    owned_stocks = load_owned_stocks()
    owned_codes = [s[0] for s in owned_stocks]
    owned_names = [s[1] for s in owned_stocks]
    print(f"Owned JP Stocks: {owned_names}")
    
    # Update global INTERESTS
    global INTERESTS
    INTERESTS.extend(owned_names)
    INTERESTS.extend(owned_codes)

    sources = [
        {"name": "Bloomberg", "query": "site:bloomberg.co.jp"},
        {"name": "Reuters", "query": "site:jp.reuters.com"},
        {"name": "WSJ", "query": "site:jp.wsj.com"},
        {"name": "Kabutan", "query": "site:kabutan.jp"}
    ]
    
    # Add owned stocks specific queries to Kabutan or generally
    # For now, let's rely on interest boosting, but we can also add specific searches if we want robust collection.
    # The requirement is "collect as highest priority". 
    # Let's add specific Kabutan searches for owned stocks to ensure we don't miss them.
    for code in owned_codes:
         sources.append({"name": f"Kabutan ({code})", "query": f"site:kabutan.jp {code}"})
    
    all_entries = []
    for s in sources:
        entries = fetch_google_news_rss(s['query'], s['name'])
        all_entries.extend(entries)
    
    # Post-process to boost interest for owned stocks
    for e in all_entries:
        for code, name in owned_stocks:
             if code in e['title'] or name in e['title']:
                 if "★" in e['interest']:
                      if len(e['interest']) < 3:
                          e['interest'] = "★★★"
                 else:
                      e['interest'] = "★★★"

    outfile = generate_markdown(all_entries)
    print(f"日本株トレンド収集完了。 Saved to {outfile}")

if __name__ == "__main__":
    main()
