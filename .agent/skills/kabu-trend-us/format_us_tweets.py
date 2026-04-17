import os
import glob
import re
import json
import argparse
from datetime import datetime

def get_latest_file():
    # ideas/daily/YYYYMMDD-kabu-us.md
    files = glob.glob(os.path.join("ideas", "daily", "*-kabu-us.md"))
    if not files:
        return None
    return max(files, key=os.path.getctime)

def parse_news(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
        
    entries = []
    
    # 1. 注目トピック Table
    table_match = re.search(r'## 注目トピック\n\n(.*?)\n\n##', content, re.DOTALL)
    if table_match:
        lines = table_match.group(1).split('\n')
        for line in lines:
            if '|' not in line or '---' in line or 'タイトル' in line: continue
            parts = line.split('|')
            if len(parts) < 3: continue
            
            title_part = parts[1].strip()
            # extract title and url
            m = re.match(r'\[(.*?)\]\((.*?)\)', title_part)
            if m:
                title = m.group(1)
                url = m.group(2)
                interest = parts[2].strip()
                source = parts[3].strip()
                entries.append({"title": title, "url": url, "interest": interest, "source": source, "section": "Top"})

    # 2. 媒体別ニュース Lists
    # Finds lines like "1. [Title](URL)" or "1. **Source**: [Title](URL)"
    # We can just scan all lines for markdown links
    lines = content.split('\n')
    current_section = ""
    
    for line in lines:
        if line.startswith("### "):
            current_section = line.strip().replace("### ", "")
            continue
            
        # Match list items
        # Format 1: 1. [Title](URL)
        # Format 2: 1. **Source**: [Title](URL) ...
        
        m = re.search(r'\[(.*?)\]\((.*?)\)', line)
        if m:
            title = m.group(1)
            url = m.group(2)
            
            # Simple deduplication based on title similarity or url?
            # For now, just add.
            entries.append({"title": title, "url": url, "interest": "★", "source": current_section, "section": "List"})

    return entries

def filter_by_ticker(entries, ticker):
    # Filter entries related to ticker
    relevant = []
    
    keywords = [ticker]
    # Add common names if needed, e.g. "Tesla" for "TSLA"
    if ticker == "TSLA": keywords.append("Tesla")
    if ticker == "NVDA": keywords.append("NVIDIA")
    if ticker == "SOFI": keywords.append("SoFi")
    if ticker == "GOOGL": keywords.append("Google"); keywords.append("Alphabet")
    if ticker == "AAPL": keywords.append("Apple")
    if ticker == "MSFT": keywords.append("Microsoft")
    if ticker == "AMZN": keywords.append("Amazon")
    if ticker == "PLTR": keywords.append("Palantir")
    
    for e in entries:
        t_text = e['title'].lower()
        s_text = e['source'].lower()
        
        # Check source for "(TICKER)" pattern from Finviz
        if f"({ticker})".lower() in s_text:
            relevant.append(e)
            continue
            
        # Check title
        for k in keywords:
            if k.lower() in t_text:
                relevant.append(e)
                break
                
    return relevant

def create_tweet_data(ticker, entries):
    if not entries:
        return None
        
    today = datetime.now().strftime("%Y/%m/%d")
    
    unique_entries = []
    seen = set()
    for e in entries:
        if e['title'] not in seen:
            unique_entries.append(e)
            seen.add(e['title'])
            
    tweet_text = f"【米国株】${ticker} {today}\n\n"
    
    sources = []
    for e in unique_entries[:3]:
        tweet_text += f"・{e['title']}\n"
        sources.append({"title": e['title'], "url": e['url'], "source": e['source']})
        
    tweet_text += "\n【感想】\n(ここにニュースを読んだ感想や考察を記入)\n"
    
    # Append the first source URL if valid
    if sources:
        first_url = sources[0]['url']
        if first_url.startswith("http"):
            tweet_text += f"\n{first_url}\n"
        
    tweet_text += f"\n#{ticker} #米国株"
    if ticker == "TSLA": tweet_text += " #Tesla"
    if ticker == "NVDA": tweet_text += " #NVIDIA"
    if ticker == "SOFI": tweet_text += " #SoFi"
    if ticker == "PLTR": tweet_text += " #Palantir"
    
    return {"ticker": ticker, "text": tweet_text, "sources": sources}

def get_tweet_weight(text):
    weight = 0
    for char in text:
        # Full-width characters (e.g. Hiragana, Kanji) count as 2
        if len(char.encode('utf-8')) > 1:
            weight += 2
        else:
            weight += 1
    return weight

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tickers", nargs="+", required=True, help="List of tickers")
    args = parser.parse_args()
    
    latest_file = get_latest_file()
    if not latest_file:
        print(json.dumps([]))
        return

    all_entries = parse_news(latest_file)
    
    tweets_data = []
    for t in args.tickers:
        relevant = filter_by_ticker(all_entries, t)
        if relevant:
            data = create_tweet_data(t, relevant)
            if data:
                # Check length
                weight = get_tweet_weight(data['text'])
                if weight > 280:
                    data['text'] += "\n\n(WARNING: Content may exceed 280 char limit. Please edit.)"
                tweets_data.append(data)
                
    print(json.dumps(tweets_data, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
