"""
Re-download specific dates using CAISO OASIS API.
Uses dates from dates_to_download.txt
"""
import os
import time
import datetime
import requests

DATES_FILE = "dates_to_download.txt"
DOWNLOAD_DIR = "caiso_supply"
BASE_URL = "https://www.caiso.com/outlook/history"
HEADERS = {"User-Agent": "Mozilla/5.0"}

def download_day(date, max_retries=3):
    """Download fuelsource.csv for a given date."""
    date_str = date.strftime("%Y%m%d")
    fname = "fuelsource.csv"
    save_path = os.path.join(DOWNLOAD_DIR, f"{date_str}_{fname}")
    
    url = f"{BASE_URL}/{date_str}/{fname}"
    
    for attempt in range(1, max_retries + 1):
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            
            if r.status_code == 429:
                wait = 10 * attempt
                print(f"    Rate limited. Waiting {wait}s...")
                time.sleep(wait)
                continue
            
            if r.status_code == 404:
                return "404"
            
            r.raise_for_status()
            
            if len(r.content) < 50:
                return "empty"
            
            with open(save_path, "wb") as f:
                f.write(r.content)
            return "ok"
        
        except requests.exceptions.RequestException as e:
            if attempt == max_retries:
                return f"error: {e}"
            time.sleep(3 * attempt)
    
    return "failed"

def main():
    # Read dates to download
    with open(DATES_FILE, 'r') as f:
        date_strings = [line.strip() for line in f if line.strip()]
    
    dates = [datetime.datetime.strptime(d, "%Y-%m-%d").date() for d in date_strings]
    
    print(f"Re-downloading {len(dates)} dates using CAISO OASIS API")
    print(f"Output directory: {DOWNLOAD_DIR}")
    print()
    
    success = 0
    errors = 0
    not_found = 0
    
    for i, date in enumerate(dates, 1):
        date_str = date.strftime("%Y-%m-%d")
        
        result = download_day(date)
        
        if result == "ok":
            success += 1
            print(f"[{i}/{len(dates)}] {date_str}: OK")
        elif result == "404":
            not_found += 1
            print(f"[{i}/{len(dates)}] {date_str}: NOT FOUND (404)")
        else:
            errors += 1
            print(f"[{i}/{len(dates)}] {date_str}: ERROR ({result})")
        
        # Polite delay
        time.sleep(0.5)
    
    print()
    print("=" * 80)
    print(f"Download complete!")
    print(f"  Success: {success}")
    print(f"  Not found: {not_found}")
    print(f"  Errors: {errors}")

if __name__ == "__main__":
    main()
