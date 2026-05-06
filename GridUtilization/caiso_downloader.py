"""
Download CAISO supply trend data (fuelsource.csv + storage.csv) for each day.
Uses the direct API: https://www.caiso.com/outlook/history/{YYYYMMDD}/fuelsource.csv
5-minute resolution, all fuel types including batteries.
"""
import os
import time
import datetime
import requests

START_DATE = datetime.date(2020, 1, 1)
END_DATE = datetime.date(2025, 12, 31)

DOWNLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "caiso_supply")
BASE_URL = "https://www.caiso.com/outlook/history"

HEADERS = {"User-Agent": "Mozilla/5.0"}

# Files to download per day
FILES = ["fuelsource.csv", "storage.csv"]


def download_day(date, max_retries=3):
    """Download fuelsource.csv and storage.csv for a given date."""
    date_str = date.strftime("%Y%m%d")
    results = {}

    for fname in FILES:
        save_path = os.path.join(DOWNLOAD_DIR, f"{date_str}_{fname}")
        if os.path.exists(save_path):
            results[fname] = "exists"
            continue

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
                    results[fname] = "404"
                    break

                r.raise_for_status()

                if len(r.content) < 50:
                    results[fname] = "empty"
                    break

                with open(save_path, "wb") as f:
                    f.write(r.content)
                results[fname] = "ok"
                break

            except requests.exceptions.RequestException as e:
                if attempt == max_retries:
                    results[fname] = f"error: {e}"
                time.sleep(3 * attempt)

    return results


def main():
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    total_days = (END_DATE - START_DATE).days + 1
    current = START_DATE
    day_num = 0

    while current <= END_DATE:
        day_num += 1
        date_str = current.strftime("%Y-%m-%d")

        # Check if both files already exist
        fs_path = os.path.join(DOWNLOAD_DIR, f"{current.strftime('%Y%m%d')}_fuelsource.csv")
        st_path = os.path.join(DOWNLOAD_DIR, f"{current.strftime('%Y%m%d')}_storage.csv")
        if os.path.exists(fs_path) and os.path.exists(st_path):
            current += datetime.timedelta(days=1)
            continue

        results = download_day(current)
        status = " | ".join(f"{k}={v}" for k, v in results.items())
        print(f"[{day_num}/{total_days}] {date_str}: {status}")

        current += datetime.timedelta(days=1)

        # Polite delay — 0.5s per day, ~18 min for 2192 days
        time.sleep(0.5)

    # Count results
    fs_count = len([f for f in os.listdir(DOWNLOAD_DIR) if f.endswith("_fuelsource.csv")])
    st_count = len([f for f in os.listdir(DOWNLOAD_DIR) if f.endswith("_storage.csv")])
    print(f"\nDone. {fs_count} fuelsource + {st_count} storage files in {DOWNLOAD_DIR}")


if __name__ == "__main__":
    main()
