import sys
import re
import time
import subprocess
import os

def run_command_stream(command):
    print(f"Running: {command}")
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    while True:
        output = process.stdout.readline()
        if output == '' and process.poll() is not None:
            break
        if output:
            print(output.strip())
    rc = process.poll()
    if rc != 0:
        print(f"Error running command: {command}")
        return False
    return True

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 post_from_draft.py <draft_file.md>")
        return
        
    filepath = sys.argv[1]
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return
        
    with open(filepath, 'r') as f:
        content = f.read()
        
    # Regex to find blocks: ## Tweet (TICKER) \n ```text \n (CONTENT) \n ```
    # Note: re.DOTALL makes . match newlines
    pattern = re.compile(r'## Tweet \((.*?)\)\n```text\n(.*?)\n```', re.DOTALL)
    matches = pattern.findall(content)
    
    if not matches:
        print("No tweets found in draft.")
        return
        
    print(f"Found {len(matches)} tweets.")
    
    for i, (ticker, text) in enumerate(matches):
        print(f"Posting tweet {i+1}/{len(matches)} for {ticker}...")
        
        tweet_content = text.strip()
        
        # Use a temporary file to handle special characters safely
        temp_file = "temp_tweet_post.txt"
        with open(temp_file, "w") as f:
            f.write(tweet_content)
            
        cmd = f"python3 .agent/skills/x-poster-kabu/post_x.py \"$(cat {temp_file})\""
        
        try:
            if not run_command_stream(cmd):
                print(f"Failed to post tweet for {ticker}.")
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)
        
        if i < len(matches) - 1:
            print("Waiting 300 seconds (5 minutes)...")
            time.sleep(300)
            
    print("All tweets posted!")

if __name__ == "__main__":
    main()
