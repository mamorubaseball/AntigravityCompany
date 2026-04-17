import os
import sys
import subprocess
import datetime

def run_command(cmd_args):
    print(f"Running: {' '.join(cmd_args)}")
    result = subprocess.run(cmd_args, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error executing {' '.join(cmd_args)}:")
        print(result.stderr)
        sys.exit(1)
    print(result.stdout)
    return result.stdout

def main():
    # Because this script is in .agent/skills/us-market-summary/
    # The workspace root is 3 levels up
    workspace = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
    
    # 1. Generate HTML
    script_gen = os.path.join(workspace, "generate_us_market_card.py")
    run_command(["python3", script_gen])
    
    # Deriving the generated filename
    date_str = datetime.datetime.now().strftime('%Y%m%d')
    html_path = os.path.join(workspace, f"ideas/daily/{date_str}-us-summary.html")
    img_path = os.path.join(workspace, f"ideas/daily/{date_str}-us-summary.png")
    
    if not os.path.exists(html_path):
        print(f"HTML file was not created at {html_path}")
        sys.exit(1)
        
    # 2. Take Screenshot
    script_shot = os.path.join(workspace, "take_report_screenshot.py")
    run_command(["python3", script_shot, html_path, img_path])
    
    if not os.path.exists(img_path):
        print(f"Image was not created at {img_path}")
        sys.exit(1)
        
    # 3. Post to X
    script_post = os.path.join(workspace, ".agent", "skills", "x-poster-kabu", "post_x.py")
    tweet_text = f"🇺🇸 米株 朝メモ（{datetime.datetime.now().strftime('%m/%d')}）\n\n・主要4指標\n・重要ニューストップ5\n\n#米国株 #投資"
    run_command(["python3", script_post, tweet_text, "--image", img_path])
    
    print("All tasks completed successfully!")

if __name__ == "__main__":
    main()
