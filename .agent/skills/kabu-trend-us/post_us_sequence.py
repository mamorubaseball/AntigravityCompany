import subprocess
import json
import time
import os
import sys

def run_command_stream(command):
    print(f"Running: {command}")
    # Initialize process
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    # Stream output
    while True:
        output = process.stdout.readline()
        if output == '' and process.poll() is not None:
            break
        if output:
            print(output.strip())
            
    rc = process.poll()
    if rc != 0:
        print(f"Error running command: {command}")
        print(process.stderr.read())
        return False
    return True

def run_command_capture(command):
    print(f"Running: {command}")
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error running command: {command}")
        print(result.stderr)
        return None
    return result.stdout

def main():
    # 1. Run Data Collection
    print("Step 1: Collecting US Stock Data...")
    if not run_command_stream("python3 collect_kabu_us.py"):
        print("Data collection failed.")
        return
    
    # 2. Format Tweets
    print("Step 2: Formatting Tweets...")
    # Tickers to post about
    tickers = ["TSLA", "SOFI", "NVDA"]
    # Run the format script
    cmd = f"python3 .agent/skills/kabu-trend-us/format_us_tweets.py --tickers {' '.join(tickers)}"
    output = run_command_capture(cmd)
    
    if not output:
        print("No tweets generated.")
        return

    try:
        tweets = json.loads(output)
    except json.JSONDecodeError:
        print("Failed to parse tweet JSON.")
        print("Output:", output)
        return

    if not tweets:
        print("No news found for specified tickers.")
        return

    print(f"Generated {len(tweets)} tweets.")

    # 3. Post Sequence
    print("Step 3: Posting to X...")
    for i, tweet in enumerate(tweets):
        print(f"Posting tweet {i+1}/{len(tweets)} for {tickers[i] if i < len(tickers) else 'Unknown'}...")
        
        with open("temp_tweet.txt", "w") as f:
            f.write(tweet)
            
        post_cmd = "python3 .agent/skills/x-poster-kabu/post_x.py \"$(cat temp_tweet.txt)\""
        if not run_command_stream(post_cmd):
            print("Failed to post tweet.")
        
        os.remove("temp_tweet.txt")
        
        if i < len(tweets) - 1:
            print("Waiting 300 seconds (5 minutes)...")
            time.sleep(300)

    print("All tweets posted!")

if __name__ == "__main__":
    main()
