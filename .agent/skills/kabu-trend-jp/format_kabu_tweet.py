import os
import glob
import re
from datetime import datetime

MATCH_KEYWORDS = [
    "日経平均", "米国株式", "Topix", "グロース", "マザーズ", 
    "ストップ高", "ストップ安", "決算", "上方修正", "下方修正",
    "増益", "減益", "自社株買い"
]

def get_latest_file():
    # ideas/daily/YYYYMMDD-kabu-jp.md
    files = glob.glob(os.path.join("ideas", "daily", "*-kabu-jp.md"))
    if not files:
        return None
    return max(files, key=os.path.getctime)

def parse_topics(filepath):
    topics = []
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract "注目トピック" section
    match = re.search(r'## 注目トピック\n\n(.*?)\n\n##', content, re.DOTALL)
    if not match:
        return []
    
    table_content = match.group(1)
    
    # Parse markdown table lines
    lines = table_content.split('\n')
    for line in lines:
        if '|' not in line or '---' in line or 'タイトル' in line:
            continue
        
        # Format: | [Title](URL) | ★★★ | Media | |
        parts = line.split('|')
        if len(parts) < 3:
            continue
            
        title_part = parts[1].strip()
        interest = parts[2].strip()
        
        # Only High interest
        if '★★★' not in interest:
            continue
            
        # Extract Title Text from [Title](URL)
        title_match = re.match(r'\[(.*?)\]\(.*?\)', title_part)
        if title_match:
            title = title_match.group(1)
            # Basic cleanup
            title = re.sub(r'Stock Price Quote.*', '', title) # Remove Bloomberg quote suffix
            title = re.sub(r'\|.*', '', title) # Remove site suffix like "| 決算速報 - 株探ニュース"
            title = title.strip()
            
            topics.append(title)
            
    return topics

def format_tweet(topics):
    today = datetime.now().strftime("%Y/%m/%d")
    tweet = f"【日本株トレンド】{today}\n\n"
    
    count = 0
    # Prioritize interesting keywords
    sorted_topics = []
    others = []
    
    for t in topics:
        if any(k in t for k in MATCH_KEYWORDS):
            sorted_topics.append(t)
        else:
            others.append(t)
            
    # Combine (prioritized first)
    all_candidates = sorted_topics + others
    
    # Select unique titles (simple dedupe)
    seen = set()
    unique_candidates = []
    for c in all_candidates:
        if c not in seen:
            unique_candidates.append(c)
            seen.add(c)
            
    # Take top 3-5
    for t in unique_candidates[:4]:
        tweet += f"・{t}\n"
    
    tweet += "\n#日本株 #株探 #Bloomberg"
    return tweet

def main():
    latest_file = get_latest_file()
    if not latest_file:
        print("No trend file found.")
        return

    topics = parse_topics(latest_file)
    tweet_text = format_tweet(topics)
    print(tweet_text)

if __name__ == "__main__":
    main()
