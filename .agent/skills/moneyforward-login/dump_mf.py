from playwright.sync_api import sync_playwright
import time
import os

def dump():
    state_file = "mf_state.json"
    if not os.path.exists(state_file):
        print("mf_state.json not found!")
        return

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(storage_state=state_file)
        page = context.new_page()
        # Just go directly to the target URLs using the valid cookies
        print("Fetching /pf/")
        page.goto("https://moneyforward.com/pf/")
        page.wait_for_load_state("networkidle")
        with open("sidebar.html", "w", encoding="utf-8") as f:
            facilities = page.locator("#facilities")
            if facilities.count() > 0:
                f.write(facilities.first.inner_html())
            else:
                f.write(page.content())
                
        print("Fetching /bs/portfolio")
        page.goto("https://moneyforward.com/bs/portfolio")
        page.wait_for_load_state("networkidle")
        with open("portfolio.html", "w", encoding="utf-8") as f:
            f.write(page.content())
            
        print("Dump complete!")
        browser.close()

if __name__ == "__main__":
    dump()
