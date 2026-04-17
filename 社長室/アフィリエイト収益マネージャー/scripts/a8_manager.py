import os
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# Path Configuration
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")

# A8.net URLs
LOGIN_URL = "https://pub.a8.net/a8v2/asLoginAction.do"
PARTICIPATING_PROGRAMS_URL = "https://pub.a8.net/a8v2/asParticipatingProgramListAction.do"

def load_config():
    if not os.path.exists(CONFIG_PATH):
        print(f"Error: {CONFIG_PATH} not found. Please create it based on resources/config.json.example.")
        return None
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)

def a8_scrape():
    config = load_config()
    if not config:
        return

    session = requests.Session()
    
    # 1. Login
    login_data = {
        "login": config.get("A8_ID"),
        "passwd": config.get("A8_PASSWORD"),
        "login_as_btn": "ログイン"
    }
    
    print("Logging into A8.net...")
    response = session.post(LOGIN_URL, data=login_data)
    
    if "asLoginAction" in response.url:
        print("Login failed. Please check your credentials in config.json.")
        return

    print("Successfully logged in.")

    # 2. Access Participating Programs
    print("Retrieving participating programs list...")
    response = session.get(PARTICIPATING_PROGRAMS_URL)
    soup = BeautifulSoup(response.text, "html.parser")
    
    # 3. Parse Programs
    # Usually A8.net uses tables for lists.
    # We look for program rows.
    # Note: A8.net has pagination, but for simplicity we start with page 1.
    
    programs = []
    # Identify program rows - this is a generic placeholder structure
    # Real A8 tables have specific classes or structures.
    # Based on general A8 UI knowledge:
    rows = soup.select("table.as_table_list tr")
    
    for row in rows:
        cells = row.find_all("td")
        if len(cells) > 2:
            name_cell = row.find("p", class_="program_name")
            if name_cell:
                name = name_cell.get_text(strip=True)
                # Link page is usually another action
                # Often a button like '広告リンク作成'
                link_btn = row.find("a", string="広告リンク")
                link_url = ""
                if link_btn:
                    link_url = "https://pub.a8.net/a8v2/" + link_btn.get("href")
                
                programs.append({
                    "name": name,
                    "management_url": link_url
                })

    # 4. Generate Report
    if not programs:
        print("No active programs found or failed to parse.")
        return

    report_path = os.path.join(REPORTS_DIR, f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# A8.net Participating Programs Report\n\n")
        f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        for p in programs:
            f.write(f"## {p['name']}\n")
            f.write(f"- [Manage Ad Links]({p['management_url']})\n\n")

    print(f"Report generated: {report_path}")

if __name__ == "__main__":
    a8_scrape()
