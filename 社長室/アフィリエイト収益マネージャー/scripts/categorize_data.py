import json
import os

# Paths
BASE_DIR = "/Users/mamoru/AntigravityCompany/社長室/アフィリエイト収益マネージャー"
INPUT_FILE = os.path.join(BASE_DIR, "reports/tracking_urls_progress.json")
OUTPUT_JS = os.path.join(BASE_DIR, "dashboard_data.js")

# Keywords for categorization
CATEGORIES = {
    "投資": ["証券", "iDeCo", "資産運用", "ALTERNA", "オルタナ", "Oh!ya", "ベルテックス", "Oh!Ya", "旬の厳選", "案件", "不動産投資"],
    "エンジニア": ["エンジニア", "IT", "テック", "TECH", "アカリク", "プログラミング", "学生", "理系", "クラウドリンク", "ユニゾンキャリア", "ウズカレ", "キャリセン", "TECH-BASE", "就活", "就職"],
}

# Explicit overrides/exceptions
OVERRIDES = {
    "マネーイングリッシュ": "その他",
    "マネーフォワード": "その他",
    "LIBERTY ENGLISH": "その他",
    "ミリオンゲームDX": "その他"
}

def categorize_item(name):
    # Check overrides first
    for key, cat in OVERRIDES.items():
        if key in name:
            return cat
            
    for category, keywords in CATEGORIES.items():
        for keyword in keywords:
            if keyword.lower() in name.lower():
                return category
    return "その他"

def main():
    if not os.path.exists(INPUT_FILE):
        print(f"Error: {INPUT_FILE} not found.")
        return

    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    categorized_data = []
    for item in data:
        category = categorize_item(item['name'])
        categorized_data.append({
            "name": item['name'],
            "tracking_url": item['tracking_url'],
            "category": category
        })

    # Sort by category
    categorized_data.sort(key=lambda x: (x['category'] != '投資', x['category'] != 'エンジニア', x['category']))

    js_content = f"const AFFILIATE_DATA = {json.dumps(categorized_data, ensure_ascii=False, indent=2)};"
    
    with open(OUTPUT_JS, 'w', encoding='utf-8') as f:
        f.write(js_content)
    
    print(f"Categorized data saved to {OUTPUT_JS}")

if __name__ == "__main__":
    main()
