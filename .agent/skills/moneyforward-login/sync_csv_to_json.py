import csv
import json
import os

def sync():
    csv_file = "/Users/mamoru/AntigravityCompany/.agent/skills/moneyforward-login/portfolio_history.csv"
    json_file = "/Users/mamoru/AntigravityCompany/.agent/skills/moneyforward-login/portfolio_history.json"
    
    if not os.path.exists(csv_file):
        print(f"Error: {csv_file} not found")
        return

    history_data = []
    with open(csv_file, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            entry = {
                "date": row["date"],
                "total_assets": int(row["total_assets"]),
                "domestic": int(row["domestic"]),
                "us": int(row["us"]),
                "trust": int(row["trust"]),
                "cash": int(row["cash"]),
                "commodity": int(row["commodity"]),
                "crypto": int(row["crypto"]),
                "margin": int(row["margin"])
            }
            history_data.append(entry)
            
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(history_data, f, ensure_ascii=False, indent=2)
        
    print(f"Successfully synced {len(history_data)} entries to {json_file}")

if __name__ == "__main__":
    sync()
