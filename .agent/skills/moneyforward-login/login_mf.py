import os
import time
import re
import imaplib
import email
from email.header import decode_header
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv(dotenv_path="/Users/mamoru/ThisIsMyLife/.env")
load_dotenv() # Fallback to local if exists

GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
MF_PASSWORD = os.getenv("MF_PASSWORD")

def get_latest_mf_code():
    if not GMAIL_ADDRESS or not GMAIL_APP_PASSWORD:
        print("Gmail credentials missing.")
        return None

    try:
        # Connect to Gmail via IMAP
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        # Handle spaces in app password if needed
        clean_pwd = GMAIL_APP_PASSWORD.replace(" ", "")
        mail.login(GMAIL_ADDRESS, clean_pwd)
        mail.select("inbox")
        
        # Search all emails
        status, messages = mail.search(None, 'ALL')
        if status != "OK":
            print("Failed to search emails.")
            return None
        
        email_ids = messages[0].split()
        if not email_ids:
            print("No emails found at all.")
            return None
            
        # Check the last 10 emails
        for e_id in reversed(email_ids[-10:]):
            status, msg_data = mail.fetch(e_id, '(RFC822)')
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    
                    # Check Subject
                    subject = msg.get("Subject", "")
                    decoded_subject = ""
                    for text, encoding in decode_header(subject):
                        if isinstance(text, bytes):
                            decoded_subject += text.decode(encoding if encoding else "utf-8")
                        else:
                            decoded_subject += text
                            
                    # Print found subjects to help debug
                    # print(f"Found email: {decoded_subject}")
                    
                    if "確認コード" in decoded_subject or "マネーフォワード" in decoded_subject:
                        print(f"Found MoneyForward email: {decoded_subject}")
                        body = ""
                        if msg.is_multipart():
                            for part in msg.walk():
                                if part.get_content_type() == "text/plain":
                                    body = part.get_payload(decode=True).decode()
                        else:
                            body = msg.get_payload(decode=True).decode()
                            
                        # Find 6 digit code
                        match = re.search(r'(\d{6})', body)
                        if match:
                            return match.group(1)
        print("Could not find a 6-digit code in the recent MoneyForward emails.")
    except Exception as e:
        print(f"Error fetching email from IMAP: {e}")
    return None

def login():
    with sync_playwright() as p:
        # headless=False so you can visually confirm what is happening
        browser = p.chromium.launch(headless=False)
        state_file = "mf_state.json"
        
        if os.path.exists(state_file):
            print("Loading existing session state...")
            context = browser.new_context(storage_state=state_file)
        else:
            context = browser.new_context()
            
        page = context.new_page()
        print("Navigating to MoneyForward ME login (SSO)...")
        # Start at ME sign_in so it handles the redirect back correctly
        page.goto("https://moneyforward.com/sign_in")
        
        # Give it a moment to redirect to id.moneyforward.com
        page.wait_for_timeout(3000)
        
        # Handle Account Selector if already logged in structurally
        if "account_selector" in page.url:
            print("Account selector found. Clicking the account...")
            try:
                page.click(f"text={GMAIL_ADDRESS}", timeout=5000)
                page.wait_for_timeout(2000)
            except Exception as e:
                print(f"Could not click account in selector: {e}")
        
        if "sign_in" in page.url and "id.moneyforward.com" in page.url:
            if "password" not in page.url:
                print("Entering email...")
                email_selector = 'input[name="mfid_user[email]"]'
                page.wait_for_selector(email_selector, timeout=10000)
                if page.is_editable(email_selector):
                    page.fill(email_selector, GMAIL_ADDRESS)
                page.click("button#submitto")
                
                # Wait for password page to load
                page.wait_for_url("**/sign_in/password*", timeout=15000)
            
            print("Entering password...")
            password_selector = 'input[name="mfid_user[password]"]'
            page.wait_for_selector(password_selector, timeout=10000)
            page.fill(password_selector, MF_PASSWORD)
            page.click("button#submitto")
            
            # Wait a few seconds to let MF process the login
            page.wait_for_timeout(4000)
            
            # Check for incorrect password error
            if page.locator("text=メールアドレスまたはパスワードが違います").is_visible():
                print("=====================")
                print("エラー: メールアドレスまたはパスワードが間違っています。")
                print(".env ファイルの MF_PASSWORD をもう一度ご確認ください！")
                print("=====================")
                browser.close()
                return

            if page.locator("text=私はロボットではありません").is_visible() or page.locator("iframe[title*='reCAPTCHA']").is_visible():
                print("=====================")
                print("エラー: CAPTCHA (ロボット認証) に引っかかっています。自動化を少し休ませる必要があります。")
                print("=====================")
                browser.close()
                return
            
            # Check for 2FA / Confirmation Code (avoid matching hidden CSRF tokens)
            is_2fa = False
            if "two_factor_auth" in page.url or "email_otp" in page.url:
                is_2fa = True
            elif page.locator("text=確認コード").is_visible():
                is_2fa = True
                
            if is_2fa:
                print("2FA confirmation code required. Waiting for email...")
                time.sleep(10) # wait for email to be delivered
                code = None
                
                # Retry fetching the code a few times
                for attempt in range(6):
                    print(f"Polling Gmail for code (Attempt {attempt+1}/6)...")
                    code = get_latest_mf_code()
                    if code:
                        break
                    time.sleep(5)
                
                if code:
                    print(f"Successfully retrieved code: {code}")
                    # Get the input box by its exact placeholder shown on the screen
                    otp_input = page.get_by_placeholder("000000")
                    if otp_input.count() > 0:
                        otp_input.first.fill(code)
                    else:
                        print("Warning: Could not find the input box by placeholder. Falling back to key typing.")
                        page.keyboard.press("Tab")
                        page.keyboard.type(code)
                    
                    page.wait_for_timeout(1000)
                    # Try explicitly clicking the submit button since Enter might not be attached
                    try:
                        page.click("button#submitto", timeout=3000)
                    except Exception:
                        try:
                            page.click("input[type='submit']", timeout=3000)
                        except Exception:
                            try:
                                page.click("button[type='submit']", timeout=3000)
                            except Exception:
                                page.keyboard.press("Enter")
                                
                    page.wait_for_timeout(2000)
                    
                    # Handle Passkey Promotion if it appears after OTP
                    if "passkey_promotion" in page.url or page.locator("text=登録せず次へ").is_visible():
                        print("Skipping passkey promotion...")
                        try:
                            page.click("text=登録せず次へ", timeout=3000)
                        except Exception:
                            pass
                                
                    # Wait for redirect back to moneyforward.com
                    try:
                        page.wait_for_url("**/pf/*", timeout=10000)
                    except Exception:
                        pass
                else:
                    print("Failed to retrieve 2FA code from Gmail.")
            
            # Catch passkey promotion if it happened without 2FA
            page.wait_for_timeout(1000)
            if "passkey_promotion" in page.url or page.locator("text=登録せず次へ").is_visible():
                print("Skipping passkey promotion...")
                try:
                    page.click("text=登録せず次へ", timeout=3000)
                except Exception:
                    pass
            
            page.wait_for_load_state('networkidle')
            
            # Wait additional time to let any post-login redirects finish
            page.wait_for_timeout(5000)
            
            print("Login flow completed.")
            
            # Save the session state
            state_file = "mf_state.json"
            context.storage_state(path=state_file)
            print(f"Session saved to {state_file}")
            
        else:
            print("Did not land on the expected sign-in page. Perhaps already logged in?")
            
        print("Final Page URL:", page.url)
        print("Final Page Title:", page.title())
        
        # Keep browser open for a few seconds to let user verify
        time.sleep(5)
        browser.close()

if __name__ == "__main__":
    if not (GMAIL_ADDRESS and GMAIL_APP_PASSWORD and MF_PASSWORD):
        print("Error: Missing credentials in .env file.")
        print("Please create an .env file with GMAIL_ADDRESS, GMAIL_APP_PASSWORD, and MF_PASSWORD.")
        exit(1)
        
    print("Starting process...")
    login()
