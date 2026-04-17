import urllib.request
import urllib.error
import json
import xml.etree.ElementTree as ET
import datetime
import time
import os
import re
import ssl
import urllib.parse
import html

# Helper to make HTTP requests
def fetch_url(url, is_json=True):
    req = urllib.request.Request(url)
    req.add_header('User-Agent', 'neta-trend-collector/1.0 (trend analysis tool)')
    try:
        with urllib.request.urlopen(req) as response:
            data = response.read()
            if is_json:
                return json.loads(data)
            return data
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

# Interest Analysis
def get_interprets_from_gemini():
    interests = ["AI", "Security", "OSS", "SaaS", "Career", "JavaScript", "TypeScript"] # Defaults
    try:
        if os.path.exists("GEMINI.md"):
            with open("GEMINI.md", "r") as f:
                content = f.read()
                # Simple extraction: lines starting with "- " under "## Interests"
                # This is a basic parser.
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
print(f"Interests: {INTERESTS}")

def check_interest(text):
    text_lower = text.lower()
    score = 0
    
    # Direct matches
    for keyword in INTERESTS:
        if keyword.lower() in text_lower:
            score += 2
            
    # Key terms
    high_value_terms = ["security", "ai", "gpt", "llm", "vulnerability", "hack", "react", "typescript", "rust", "go", "startup"]
    for term in high_value_terms:
         if term in text_lower:
             score += 1

    if score >= 4: return "★★★" # Higher threshold since we are summing up
    if score >= 2: return "★★"
    if score >= 4: return "★★★" # Higher threshold since we are summing up
    if score >= 2: return "★★"
    return "★"

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
        # print(f"Translation failed for '{text[:20]}...': {e}") 
        return text

def fetch_hatena():
    urls = [
        "https://b.hatena.ne.jp/hotentry/it.rss"
    ]
    entries = []
    seen_links = set()
    
    print("Fetching Hatena...")
    for url in urls:
        xml_data = fetch_url(url, is_json=False)
        if not xml_data: continue
        
        try:
            root = ET.fromstring(xml_data)
            # RSS 1.0 (RDF) usually used by Hatena
            # Need to handle namespaces properly or just search by tag name ignoring ns
            # Hatena RSS 1.0: <item> under <rdf:RDF>
            
            # Simple non-namespace aware parsing for robustness
            for item in root.findall(".//{http://purl.org/rss/1.0/}item"):
                link = item.find("{http://purl.org/rss/1.0/}link").text
                if link in seen_links: continue
                seen_links.add(link)
                
                title = item.find("{http://purl.org/rss/1.0/}title").text
                bookmark_count = 0
                # count is in {http://www.hatena.ne.jp/info/xmlns#}bookmarkcount
                bc = item.find("{http://www.hatena.ne.jp/info/xmlns#}bookmarkcount")
                if bc is not None:
                    bookmark_count = int(bc.text)
                
                entries.append({
                    "title": title,
                    "url": link,
                    "users": bookmark_count,
                    "interest": check_interest(title),
                    "source": "Hatena",
                    "category": "IT" # Placeholder
                })
        except Exception as e:
            print(f"Error parsing Hatena XML: {e}")
            
    return sorted(entries, key=lambda x: x['users'], reverse=True)[:30]

def fetch_hn():
    print("Fetching Hacker News...")
    entries = []
    try:
        top_ids = fetch_url("https://hacker-news.firebaseio.com/v0/topstories.json")
        if not top_ids: return []
        
        for id in top_ids[:30]:
            item = fetch_url(f"https://hacker-news.firebaseio.com/v0/item/{id}.json")
            if not item: continue
            
            title = item.get("title", "")
            entries.append({
                "title": translate_text(title),
                "url": f"https://news.ycombinator.com/item?id={id}",
                "points": item.get("score", 0),
                "interest": check_interest(title), # Check interest on original English title
                "source": "HN",
                "category": "Tech"
            })
            time.sleep(0.1)
    except Exception as e:
        print(f"Error in HN fetch: {e}")
    return entries

def fetch_reddit():
    subreddits = [
        "netsec", "cybersecurity",
        "OpenAI", "LocalLLaMA", "ClaudeCode",
        "programming", "technology",
        "opensource", "indiehackers", "webdev", "javascript",
        "cscareerquestions", "productivity"
    ]
    
    entries = {} # Key by subreddit
    print("Fetching Reddit...")
    
    for sub in subreddits:
        try:
            url = f"https://old.reddit.com/r/{sub}/hot.json?limit=5"
            data = fetch_url(url)
            if not data: continue
            
            sub_entries = []
            for child in data['data']['children']:
                d = child['data']
                if d.get('stickied'): continue # Skip stickied posts
                
                sub_entries.append({
                    "title": translate_text(d['title']),
                    "url": f"https://www.reddit.com{d['permalink']}",
                    "ups": d['ups'],
                    "comments": d['num_comments'],
                    "interest": check_interest(d['title']), # Check interest on original English title
                    "subreddit": sub,
                    "id": d['id']
                })
            entries[sub] = sub_entries
            time.sleep(1.0) # Be nice to Reddit API
        except Exception as e:
            print(f"Error fetching r/{sub}: {e}")
            
    return entries

def generate_reports(hatena, hn, reddit):
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    date_str = datetime.datetime.now().strftime('%Y%m%d')
    os.makedirs("ideas/daily", exist_ok=True)
    filename_md = f"ideas/daily/{date_str}-trend.md"
    filename_html = f"ideas/daily/{date_str}-trend.html"
    
    with open(filename_md, "w") as f:
        f.write(f"# トレンドネタ: {today}\n\n")
        
        # Hatena
        f.write("## はてブIT（日本市場）\n\n")
        f.write("### 注目トピック\n\n")
        f.write("| タイトル | ブクマ数 | 興味度 | カテゴリ | メモ |\n")
        f.write("|---------|---------|--------|---------|------|\n")
        
        top_hatena = [e for e in hatena if "★" in e['interest']]
        # Sort by interest length (number of stars) desc
        top_hatena.sort(key=lambda x: len(x['interest']), reverse=True)
        
        for e in top_hatena[:10]:
            f.write(f"| [{e['title']}]({e['url']}) | {e['users']} users | {e['interest']} | {e['category']} | |\n")
            
        f.write("\n### 全エントリー\n\n")
        for i, e in enumerate(hatena[:20], 1):
             f.write(f"{i}. [{e['title']}]({e['url']}) ({e['users']} users)\n")
             
        # HN
        f.write("\n## Hacker News（グローバル）\n\n")
        f.write("### 注目トピック\n\n")
        f.write("| タイトル | ポイント | 興味度 | カテゴリ | メモ |\n")
        f.write("|---------|---------|--------|---------|------|\n")
        
        top_hn = [e for e in hn if "★" in e['interest']]
        top_hn.sort(key=lambda x: len(x['interest']), reverse=True)
        
        for e in top_hn[:10]:
             f.write(f"| [{e['title']}]({e['url']}) | {e['points']}pt | {e['interest']} | {e['category']} | |\n")
             
        f.write("\n### 全エントリー\n\n")
        for i, e in enumerate(hn[:20], 1):
            f.write(f"{i}. [{e['title']}]({e['url']}) ({e['points']}pt)\n")

        # Reddit
        f.write("\n## Reddit（13サブレッド）\n\n")
        f.write("### 注目トピック\n\n")
        f.write("| タイトル | 投票数 | コメント数 | 興味度 | カテゴリ | サブレッド | メモ |\n")
        f.write("|---------|--------|-----------|--------|---------|-----------|------|\n")
        
        all_reddit = []
        for sub, items in reddit.items():
            all_reddit.extend(items)
            
        top_reddit = [e for e in all_reddit if "★" in e['interest']]
        top_reddit.sort(key=lambda x: len(x['interest']), reverse=True)
        
        for e in top_reddit[:10]:
             # Assuming category based on sub
            cat = "Tech"
            if e['subreddit'] in ["netsec", "cybersecurity"]: cat = "Security"
            elif e['subreddit'] in ["OpenAI", "LocalLLaMA"]: cat = "AI"
            
            f.write(f"| [{e['title']}]({e['url']}) | {e['ups']} ups | {e['comments']} | {e['interest']} | {cat} | r/{e['subreddit']} | |\n")
            
        f.write("\n### カテゴリ別エントリー\n\n")
        
        # Grouping for display
        categories = {
            "セキュリティ系": ["netsec", "cybersecurity"],
            "AI系": ["OpenAI", "LocalLLaMA", "ClaudeCode"],
            "OSS/個人開発系": ["opensource", "indiehackers", "webdev", "javascript"],
            "キャリア/実践系": ["cscareerquestions", "productivity", "programming", "technology"]
        }
        
        for cat_name, subs in categories.items():
            f.write(f"#### {cat_name}\n")
            for sub in subs:
                if sub in reddit:
                    for e in reddit[sub]:
                         f.write(f"1. [{e['title']}]({e['url']}) ({e['ups']} ups, {e['comments']} comments) - r/{sub}\n")
            f.write("\n")
            
    # HTML Generation
    html_content = f"""
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Neta Trend {today}</title>
        <style>
            body {{ font-family: 'Helvetica Neue', Arial, sans-serif; background-color: #0d1117; color: #c9d1d9; margin: 0; padding: 20px; }}
            .container {{ max-width: 1000px; margin: 0 auto; background: #161b22; padding: 30px; border-radius: 8px; border-top: 5px solid #58a6ff; box-shadow: 0 4px 15px rgba(0,0,0,0.5); }}
            h1 {{ color: #58a6ff; text-align: center; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 30px; }}
            h2 {{ color: #58a6ff; border-bottom: 1px solid #30363d; padding-bottom: 5px; margin-top: 40px; font-size: 1.4em; }}
            h3 {{ color: #8b949e; font-size: 1.1em; margin-top: 20px; }}
            h4 {{ color: #c9d1d9; font-size: 1em; }}
            table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; }}
            th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #30363d; font-size: 0.95em; }}
            th {{ background: #21262d; color: #8b949e; text-transform: uppercase; font-size: 0.85em; letter-spacing: 1px; }}
            tr:hover {{ background-color: #21262d; }}
            a {{ color: #58a6ff; text-decoration: none; }}
            a:hover {{ text-decoration: underline; color: #79c0ff; }}
            .interest {{ color: #e3b341; font-weight: bold; white-space: nowrap; }}
            ul {{ padding-left: 20px; }}
            .list-item {{ margin-bottom: 8px; font-size: 0.95em; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>トレンドネタ: {today}</h1>
    """

    # Hatena
    html_content += "<h2>はてブIT（日本市場）</h2>\n<h3>注目トピック</h3>\n<table><thead><tr><th width='10%'>興味度</th><th width='65%'>タイトル</th><th width='15%'>ブクマ数</th><th width='10%'>カテゴリ</th></tr></thead><tbody>"
    for e in top_hatena[:10]:
        html_content += f"<tr><td class='interest'>{e['interest']}</td><td><a href='{html.escape(e['url'])}' target='_blank'>{html.escape(e['title'])}</a></td><td>{e['users']} users</td><td>{html.escape(e['category'])}</td></tr>"
    html_content += "</tbody></table>\n<h3>全エントリー</h3><ul>"
    for e in hatena[:20]:
         html_content += f"<li class='list-item'><a href='{html.escape(e['url'])}' target='_blank'>{html.escape(e['title'])}</a> ({e['users']} users)</li>"
    html_content += "</ul>"

    # HN
    html_content += "<h2>Hacker News（グローバル）</h2>\n<h3>注目トピック</h3>\n<table><thead><tr><th width='10%'>興味度</th><th width='65%'>タイトル</th><th width='15%'>ポイント</th><th width='10%'>カテゴリ</th></tr></thead><tbody>"
    for e in top_hn[:10]:
        html_content += f"<tr><td class='interest'>{e['interest']}</td><td><a href='{html.escape(e['url'])}' target='_blank'>{html.escape(e['title'])}</a></td><td>{e['points']}pt</td><td>{html.escape(e['category'])}</td></tr>"
    html_content += "</tbody></table>\n<h3>全エントリー</h3><ul>"
    for e in hn[:20]:
         html_content += f"<li class='list-item'><a href='{html.escape(e['url'])}' target='_blank'>{html.escape(e['title'])}</a> ({e['points']}pt)</li>"
    html_content += "</ul>"

    # Reddit
    html_content += "<h2>Reddit（13サブレッド）</h2>\n<h3>注目トピック</h3>\n<table><thead><tr><th width='10%'>興味度</th><th width='55%'>タイトル</th><th width='10%'>Voting</th><th width='10%'>Cat</th><th width='15%'>Sub</th></tr></thead><tbody>"
    for e in top_reddit[:10]:
        cat = "Tech"
        if e['subreddit'] in ["netsec", "cybersecurity"]: cat = "Security"
        elif e['subreddit'] in ["OpenAI", "LocalLLaMA"]: cat = "AI"
        html_content += f"<tr><td class='interest'>{e['interest']}</td><td><a href='{html.escape(e['url'])}' target='_blank'>{html.escape(e['title'])}</a></td><td>{e['ups']} ups / {e['comments']} cmts</td><td>{cat}</td><td>r/{e['subreddit']}</td></tr>"
    html_content += "</tbody></table>\n<h3>カテゴリ別エントリー</h3>"

    for cat_name, subs in categories.items():
        html_content += f"<h4>{cat_name}</h4><ul>"
        for sub in subs:
            if sub in reddit:
                for e in reddit[sub]:
                     html_content += f"<li class='list-item'><a href='{html.escape(e['url'])}' target='_blank'>{html.escape(e['title'])}</a> ({e['ups']} ups, {e['comments']} comments) - r/{sub}</li>"
        html_content += "</ul>"

    html_content += """
        </div>
    </body>
    </html>
    """

    with open(filename_html, "w") as f:
        f.write(html_content)

    return filename_md, filename_html

def main():
    hatena = fetch_hatena()
    hn = fetch_hn()
    reddit = fetch_reddit()
    
    md_file, html_file = generate_reports(hatena, hn, reddit)
    print(f"ネタ収集完了。\nMarkdown: {md_file}\nHTML: {html_file}")

if __name__ == "__main__":
    main()
