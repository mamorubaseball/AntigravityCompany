import urllib.request
import urllib.parse
import urllib.error
import xml.etree.ElementTree as ET
import json
import datetime
import os
import ssl
import time
import re

# Helper to make HTTP requests
def fetch_url(url, is_json=False):
    # Fix for SSL
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    req = urllib.request.Request(url)
    req.add_header('User-Agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36')
    
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=10) as response:
            data = response.read()
            if is_json:
                return json.loads(data)
            return data
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

# Interest Analysis (Shared logic + US specific)
def get_interprets_from_gemini():
    interests = ["AI", "Security", "OSS", "SaaS", "Career", "JavaScript", "TypeScript"]
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
# Add US stock specific English keywords
INTERESTS.extend(["Stock", "Market", "Invest", "Earnings", "IPO", "Fed", "Rate", "Bond", "Crypto", "Bitcoin", "NVIDIA", "Tesla", "Apple", "Microsoft", "Google", "Amazon", "Meta"])

def check_interest(text):
    text_lower = text.lower()
    score = 0
    
    for keyword in INTERESTS:
        if keyword.lower() in text_lower:
            score += 2
            
    high_value_terms = [
        "security", "ai", "gpt", "llm", "semi", "earnings", "profit", "loss", 
        "dividend", "buyback", "split", "merger", "acquisition", "takeover",
        "bull", "bear", "rally", "crash", "correction", "inflation", "cpi", "fomc"
    ]
    for term in high_value_terms:
         if term in text_lower:
             score += 1

    if score >= 4: return "★★★"
    if score >= 2: return "★★"
    return "★"

# ... imports

def translate_text(text, source_lang='auto', target_lang='ja'):
    if not text or len(text) < 2: return text
    
    # Simple use of Google Translate GTX endpoint (Free, no key, subject to rate limits)
    # This avoids external dependencies like googletrans
    try:
        base_url = "https://translate.googleapis.com/translate_a/single"
        params = {
            "client": "gtx",
            "sl": source_lang,
            "tl": target_lang,
            "dt": "t",
            "q": text
        }
        query_string = urllib.parse.urlencode(params)
        url = f"{base_url}?{query_string}"
        
        # Use simple UA
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0')
        
        # Fix SSL context
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        with urllib.request.urlopen(req, context=ctx, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
            # Result is often [[["Translated Text", "Original", ...], ...], ...]
            # We combine parts if multiple sentences
             # data[0] is the list of sentences
            translated = "".join([x[0] for x in data[0] if x[0]])
            return translated
    except Exception as e:
        # Fallback to original text on error (e.g. rate limit)
        print(f"Translation failed for '{text[:20]}...': {e}") 
        return text

def parse_rss(url, source_name):
    print(f"Fetching {source_name} RSS...")
    xml_data = fetch_url(url)
    if not xml_data: return []
    
    entries = []
    try:
        root = ET.fromstring(xml_data)
        # Handle standard RSS 2.0
        for item in root.findall(".//item")[:5]: # Limit to 5 items
            title = item.find("title").text
            link = item.find("link").text
            
            # Helper to get text or empty string
            def get_text(elem, tag):
                found = elem.find(tag)
                return found.text if found is not None else ""

            pubDate = get_text(item, "pubDate")
            
            # Translate title
            jp_title = translate_text(title)
            
            entries.append({
                "title": jp_title,
                "original_title": title, # Keep original for reference if needed
                "url": link,
                "interest": check_interest(title if title else ""), # Check interest on ORIGINAL English
                "source": source_name,
                "date": pubDate
            })
            time.sleep(1.0)
    except Exception as e:
        print(f"Error parsing RSS for {source_name}: {e}")
        
    return entries

# ... (imports are same)

def fetch_google_news_rss(query, source_name):
    # Google News RSS URL format for US (English)
    # hl=en-US&gl=US&ceid=US:en
    base_url = "https://news.google.com/rss/search?q={}&hl=en-US&gl=US&ceid=US:en"
    encoded_query = urllib.parse.quote(query)
    url = base_url.format(encoded_query)
    
    print(f"Fetching {source_name} from Google News...")
    xml_data = fetch_url(url)
    if not xml_data: return []
    
    entries = []
    try:
        root = ET.fromstring(xml_data)
        for item in root.findall(".//channel/item")[:5]: # Limit to 5 items
            title = item.find("title").text
            if " - " in title:
                title = title.rsplit(" - ", 1)[0]
                
            link = item.find("link").text
            pubDate = item.find("pubDate").text
            
            # Translate title
            jp_title = translate_text(title)
            
            entries.append({
                "title": jp_title,
                "original_title": title,
                "url": link,
                "interest": check_interest(title), # Check interest on original
                "source": source_name,
                "date": pubDate
            })
            time.sleep(1.0)
    except Exception as e:
        print(f"Error parsing Google News XML for {source_name}: {e}")
        
    return entries

def fetch_yahoo_chart_news():
    # Attempting to fetch market data. 
    # Note: Yahoo Finance aggressively rate limits or blocks bots (HTTP 429).
    # We will try with a very specific user agent or just fail silently.
    
    tickers = ["^GSPC", "^IXIC", "USDJPY=X", "NVDA"]
    results = []
    print("Fetching Yahoo Finance Market Data...")
    
    for ticker in tickers:
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=1d"
            # Use a more standard browser User-Agent
            req = urllib.request.Request(url)
            req.add_header('User-Agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36')
            
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

            with urllib.request.urlopen(req, context=ctx, timeout=10) as response:
                data = json.loads(response.read())
                meta = data['chart']['result'][0]['meta']
                symbol = meta['symbol']
                price = meta['regularMarketPrice']
                prev = meta['chartPreviousClose']
                change = price - prev
                pct = (change / prev) * 100
                
                results.append(f"{symbol}: {price:.2f} ({change:+.2f} / {pct:+.2f}%)")
            
            time.sleep(1) # Be nice
        except Exception:
            # Silently fail if blocked to avoid cluttering output
            pass
            
    return results

def fetch_finviz_news():
    url = "https://finviz.com/news.ashx"
    print(f"Fetching {url}...")
    html = fetch_url(url)
    if not html: return []
    entries = []
    try:
        html_str = html.decode('utf-8', errors='ignore')
        matches = re.findall(r'<a href="([^"]+)" class="nn-tab-link"[^>]*>(.*?)</a>', html_str)
        for href, title in matches:
            if href.startswith('/'):
                href = "https://finviz.com" + href
            t_str = title.strip()
            # Translate
            jp_title = translate_text(t_str)
            
            entries.append({
                "title": jp_title,
                "original_title": t_str,
                "url": href,
                "interest": check_interest(t_str),
                "source": "Finviz",
                "date": ""
            })
            time.sleep(1.0)
    except Exception as e:
        print(f"Error parsing Finviz: {e}")
    return entries[:10]

def fetch_finviz_ticker_news(ticker):
    url = f"https://finviz.com/quote.ashx?t={ticker}&p=d"
    print(f"Fetching news for {ticker} from Finviz...")
    html = fetch_url(url)
    if not html: return []
    
    entries = []
    try:
        html_str = html.decode('utf-8', errors='ignore')
        # Find news table
        start = html_str.find('id="news-table"')
        if start == -1: return []
        
        # Simplified parser for the table
        # We look for <tr>...</tr> rows inside the table
        # Each row has a date/time td and a link td
        
        # Extract the table part roughly to reduce search space
        table_end = html_str.find('</table>', start)
        table_html = html_str[start:table_end]
        
        # Split by tr to get rows
        rows = table_html.split('<tr')
        
        current_date_str = datetime.datetime.now().strftime('%b-%d-%y') # Default if not found
        
        for row in rows[1:]: # Skip first split usually empty or header
            # clean up row string
            row = "<tr" + row
            
            # Regex to pull link and text
            # Looking for <a ... class="tab-link-news" ...>(.*?)</a>
            link_match = re.search(r'<a[^>]+class="tab-link-news"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', row, re.DOTALL)
            if not link_match: continue
            
            href = link_match.group(1)
            if href.startswith('/'):
                href = "https://finviz.com" + href
            title = link_match.group(2).replace('&amp;', '&').replace('&quot;', '"')
            
            # Source usually in <div class="news-link-right">...</div> or just after link
            # But we can just use "Finviz ({ticker})" or try to parse
            source_match = re.search(r'<div class="news-link-right">\s*<span>\((.*?)\)</span>', row)
            source = source_match.group(1) if source_match else "Finviz"
            
            # Date/Time parsing
            # <td width="130" align="right"> Feb-04-26 05:02PM </td> OR <td ...> 05:02PM </td>
            date_match = re.search(r'<td width="130"[^>]*>(.*?)</td>', row, re.DOTALL)
            date_text = ""
            if date_match:
                date_text = date_match.group(1).strip()
                # Format: "Feb-04-26 05:02PM" or "05:02PM"
                if len(date_text) > 8: # Has date
                    current_date_str = date_text.split(' ')[0] # Update current date
            
            full_date = f"{current_date_str} {date_text if len(date_text) <= 8 else date_text.split(' ')[1]}"
            
            # Translate
            jp_title = translate_text(title)
            
            entries.append({
                "title": jp_title,
                "original_title": title,
                "url": href,
                "interest": check_interest(title),
                "source": f"{source} ({ticker})",
                "date": full_date
            })
            
            if len(entries) >= 3: # Limit per ticker
                break
                
            time.sleep(0.5)
            
    except Exception as e:
        print(f"Error parsing Finviz for {ticker}: {e}")
        
    return entries

def generate_markdown(news_entries, market_data, tickers):
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    date_str = datetime.datetime.now().strftime('%Y%m%d')
    os.makedirs("ideas/daily", exist_ok=True)
    filename = f"ideas/daily/{date_str}-kabu-us.md"
    
    with open(filename, "w") as f:
        f.write(f"# 米国株トレンド: {today}\n\n")
        
        if market_data:
            f.write("## マーケット概況 (Yahoo Finance)\n")
            for m in market_data:
                f.write(f"- {m}\n")
            f.write("\n")
        
        # Determine top topics
        # Filter duplicates for top topics just in case
        seen_urls = set()
        unique_entries = []
        for e in news_entries:
            if e['url'] not in seen_urls:
                unique_entries.append(e)
                seen_urls.add(e['url'])

        top_entries = [e for e in unique_entries if "★" in e['interest']]
        top_entries.sort(key=lambda x: len(x['interest']), reverse=True)
        
        f.write("## 注目トピック\n\n")
        f.write("| <div style=\"width:500px\">タイトル</div> | 興味度 | 媒体 | メモ |\n")
        f.write("|------------------------------------------|--------|------|------|\n")
        
        for e in top_entries[:20]: # Increased to 20
            f.write(f"| [{e['title']}]({e['url']}) | {e['interest']} | {e['source']} | |\n")
            
        f.write("\n## 媒体別ニュース\n\n")
        
        sources = sorted(list(set(e['source'].split(' (')[0] for e in unique_entries))) # Group by base source mostly
        
        # Group by source specifically for display? or just list all
        # Let's group by the 'source' field we put in entry
        
        # Custom grouping: If source has (Ticker), maybe group under "Individual Tickers"?
        # Or just mix them in. The user wants "info collection from this place too", so mixed is probably fine or separate section.
        # User output requirement wasn't specific on layout, but "add these infos".
        
        # Let's group Finviz Ticker news separately or with Finviz?
        # Current implementation of source is "Source (Ticker)" e.g. "Motley Fool (GOOGL)"
        
        # Let's try to group smartly.
        # Major sources first.
        major_sources = ["Bloomberg", "WSJ", "CNBC", "Reuters", "SeekingAlpha", "Barrons", "MarketWatch", "Kabutan"]
        
        for source in major_sources:
            source_entries = [e for e in unique_entries if e['source'] == source]
            if source_entries:
                f.write(f"### {source}\n\n")
                for i, e in enumerate(source_entries[:10], 1):
                    f.write(f"{i}. [{e['title']}]({e['url']})\n")
                f.write("\n")
        
        # Individual Tickers Section
        f.write("### 注目銘柄ニュース (Finviz)\n\n")
        ticker_entries = [e for e in unique_entries if "(" in e['source'] and any(t in e['source'] for t in tickers)]
        # Sort by date ? or Ticker?
        # Let's sort by interest then date
        ticker_entries.sort(key=lambda x: (len(x['interest']), x['date']), reverse=True)
        
        for i, e in enumerate(ticker_entries, 1):
             f.write(f"{i}. **{e['source']}**: [{e['title']}]({e['url']}) {e['interest']}\n")
        f.write("\n")
            
        # Others
        other_entries = [e for e in unique_entries if e['source'] not in major_sources and e not in ticker_entries]
        if other_entries:
            f.write("### その他\n\n")
            for i, e in enumerate(other_entries[:10], 1):
                f.write(f"{i}. {e['source']}: [{e['title']}]({e['url']})\n")
            f.write("\n")

    return filename

    return entries

def load_owned_stocks():
    owned_tickers = []
    try:
        if os.path.exists("Money/stock.md"):
            with open("Money/stock.md", "r") as f:
                lines = f.readlines()
                for line in lines[1:]: # Skip header
                    parts = line.split('\t')
                    if len(parts) >= 1:
                        ticker = parts[0].strip()
                        # US tickers are usually alphabetic and uppercase
                        if re.match(r'^[A-Z]+$', ticker):
                            owned_tickers.append(ticker)
    except Exception as e:
        print(f"Error reading Money/stock.md: {e}")
    return owned_tickers

def fetch_scorpion_capital():
    url = "https://scorpioncapital.com/"
    print(f"Fetching {url}...")
    # Scorpion Capital usually has reports linked on homepage
    # We need to simulate a browser carefully
    req = urllib.request.Request(url)
    req.add_header('User-Agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36')
    
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    entries = []
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=15) as response:
            html = response.read().decode('utf-8', errors='ignore')
            # Look for report links. Structure seems div based or standard a tags.
            # Based on typical Squarespace sites (which it seems to be from debug output), links might be in specific blocks.
            # We'll look for generic links that might be reports
            
            # Pattern: <a href="..." ...> Title ... </a>
            # We will grab all links and filter for likely reports or show top links
            # Simple heuristic: look for "report" or specific company names in text or url
            
            # Since structure is complex, let's grab all <a> tags with some text length
            link_pattern = re.compile(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', re.DOTALL)
            matches = link_pattern.findall(html)
            
            for href, text in matches:
                clean_text = re.sub(r'<[^>]+>', '', text).strip()
                if len(clean_text) > 10 and ("report" in clean_text.lower() or "research" in clean_text.lower() or "short" in clean_text.lower()):
                     # Normalize URL
                    if href.startswith('/'):
                        href = "https://scorpioncapital.com" + href
                        
                    jp_title = translate_text(clean_text)
                    entries.append({
                        "title": jp_title,
                        "original_title": clean_text,
                        "url": href,
                        "interest": "★★★", # Always high interest
                        "source": "Scorpion Capital",
                        "date": ""
                    })
            
            # If no "report" keyword found, just take top few substantial links as fallback (it might be just company names)
            if not entries:
                 for href, text in matches[:20]:
                    clean_text = re.sub(r'<[^>]+>', '', text).strip()
                    if len(clean_text) > 5 and not "function" in clean_text:
                         if href.startswith('/'):
                            href = "https://scorpioncapital.com" + href
                         entries.append({
                            "title": translate_text(clean_text),
                            "original_title": clean_text,
                            "url": href,
                            "interest": "★★★",
                            "source": "Scorpion Capital",
                            "date": ""
                        })
    except Exception as e:
        print(f"Error fetching Scorpion Capital: {e}")
        
    # Deduplicate
    unique_entries = []
    seen = set()
    for e in entries:
        if e['url'] not in seen and e['title']:
            unique_entries.append(e)
            seen.add(e['url'])
            
    return unique_entries[:5]

def main():
    # Load owned tickers
    owned_tickers = load_owned_stocks()
    print(f"Owned US Tickers: {owned_tickers}")
    
    # Update global INTERESTS with owned tickers to ensure high priority checking
    global INTERESTS
    INTERESTS.extend(owned_tickers)
    
    rss_sources = [
        {"name": "Bloomberg", "url": "https://feeds.bloomberg.com/markets/news.rss"},
        {"name": "WSJ", "url": "https://feeds.a.dj.com/rss/RSSMarketsMain.xml"},
        {"name": "CNBC", "url": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114"},
        {"name": "SeekingAlpha", "url": "https://seekingalpha.com/feed.xml"},
        {"name": "Barrons", "url": "https://feeds.content.dowjones.io/public/rss/mw_topstories"},
        {"name": "MarketWatch", "url": "https://feeds.content.dowjones.io/public/rss/mw_topstories"}
    ]
    
    all_news = []
    
    # RSS Feeds
    for s in rss_sources:
        entries = parse_rss(s['url'], s['name'])
        all_news.extend(entries)
        
    # Google News RSS Sources (Reuters, Kabutan US)
    google_sources = [
        {"name": "Reuters", "query": "site:reuters.com"},
        {"name": "Kabutan", "query": "site:us.kabutan.jp"}
    ]
    
    for s in google_sources:
        entries = fetch_google_news_rss(s['query'], s['name'])
        all_news.extend(entries)

    finviz = fetch_finviz_news()
    all_news.extend(finviz)
    
    # Scorpion Capital
    scorpion = fetch_scorpion_capital()
    all_news.extend(scorpion)
    
    # Finviz Tickers (Owned + Target)
    target_tickers = ["ASTS", "CRCL", "GOOGL", "MRVL", "SOFI", "PFE", "PLTR", "NVDA"]
    # Merge and deduplicate
    combined_tickers = list(set(target_tickers + owned_tickers))
    
    for t in combined_tickers:
        t_news = fetch_finviz_ticker_news(t)
        all_news.extend(t_news)
    
    # Market Data
    market_data = fetch_yahoo_chart_news()
    
    # Enhance interest check for owned tickers in all news
    for news in all_news:
        for t in owned_tickers:
            # If ticker or name in title (basic check), boost interest
            if t in news['original_title'] or t in news['title']:
                if "★" in news['interest']:
                     if len(news['interest']) < 3:
                         news['interest'] = "★★★"
                else: # No interest score yet
                     news['interest'] = "★★★"
    
    outfile = generate_markdown(all_news, market_data, combined_tickers)
    print(f"米国株トレンド収集完了。 Saved to {outfile}")

if __name__ == "__main__":
    main()
