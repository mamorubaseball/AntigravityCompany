import csv
import json
import re
import os

history = {}

def clean_num(val):
    if not val: return 0
    val = val.replace(",", "").strip()
    if "." in val:
        val = val.split(".")[0]
    return int(re.sub(r'[^\d\-]', '', val))

# Read Monthly Assets
csv_assets = 'finacial_dashboad - Monthly Assets.csv'
if os.path.exists(csv_assets):
    with open(csv_assets, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            date = row.get('month', '').strip()
            amt = row.get('amount', '')
            if not date or not amt: continue
            history[date] = {
                "date": date,
                "total_assets": clean_num(amt)
            }

# Read Asset Allocations
csv_alloc = 'finacial_dashboad - Asset Allocations.csv'
if os.path.exists(csv_alloc):
    with open(csv_alloc, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            date = row.get('month', '').strip()
            if not date or date in ["差分", "年率", "2027年1月_目標資産分布", "積立額(400万円くらい？)", ""]: continue
            if date not in history:
                history[date] = {"date": date, "total_assets": 0}
                
            history[date]["domestic"] = clean_num(row.get('DomesticStocks', '0'))
            history[date]["us"] = clean_num(row.get('USstocks', '0'))
            history[date]["trust"] = clean_num(row.get('Investment', '0'))
            history[date]["cash"] = clean_num(row.get('Cash', '0'))
            history[date]["commodity"] = 0 # Ignored for past data
            history[date]["crypto"] = clean_num(row.get('BitCoin', '0'))
            history[date]["margin"] = 0 # Ignored for past data
            
            if history[date]["total_assets"] == 0:
                history[date]["total_assets"] = clean_num(row.get('総額', '0'))

# Fill missing keys with 0
for date, data in history.items():
    for k in ["domestic", "us", "trust", "cash", "commodity", "crypto", "margin"]:
        if k not in data:
            data[k] = 0

# Sort by date properly
def sort_key(d):
    # Try parsing YYYY/MM/DD
    try:
        parts = d["date"].split("/")
        return f"{parts[0]:04d}/{parts[1]:02d}/{parts[2]:02d}"
    except:
        return d["date"]

sorted_history = sorted(history.values(), key=sort_key)

with open('portfolio_history.json', 'w', encoding='utf-8') as f:
    json.dump(sorted_history, f, indent=2, ensure_ascii=False)

print(f"Generated portfolio_history.json with {len(sorted_history)} records.")
