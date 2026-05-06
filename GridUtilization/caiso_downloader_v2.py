"""
Download CAISO supply data using the actual API endpoints.

The CAISO Today's Outlook page uses these API patterns:
- Supply trend: https://www.caiso.com/outlook/SP/history/{YYYYMMDD}_fuelsource.csv
- Renewables trend: https://www.caiso.com/outlook/SP/history/{YYYYMMDD}_renewables.csv

These endpoints provide complete data including Large Hydro and Natural Gas.
"""
import os
import time
import datetime
import requests
from pathlib import Path

START_DATE = datetime.date(2020, 1, 1)
END_DATE = datetime.date(2021, 12, 31)  # Start with 2020-2021 to fix bad data

DOWNLOAD_DIR = Path(__file__).parent / "caiso_supply_v2"
BASE_URL = "https://www.caiso.com/outlook/SP/history"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/csv,application/csv,text/plain",
    "Referer": "https://www.caiso.com/todays-outlook/supply"
}

# Files to download per day
FILES = {
    "fuelsource.csv": "supply",
    "renewables.csv": "renewables"
}


def download_day(date, max_retries=3):
    """Download supply and renewables CSV for a given date."""
    date_str = date.strftime("%Y%m%d")
    results = {}

    for fname, desc in FILES.items():
        save_path = DOWNLOAD_DIR / f"{date_str}_{fname}"
        if save_path.exists():
            results[desc] = "exists"
            continue

        url = f"{BASE_URL}/{date_str}_{fname}"

        for attempt in range(1, max_retries + 1):
            try:
                r = requests.get(url, headers=HEADERS, timeout=30)

                if r.status_code == 429:
                    wait = 10 * attempt
                    print(f"    Rate limited. Waiting {wait}s...")
                    time.sleep(wait)
                    continue

                if r.status_code == 404:
                    results[desc] = "404"
                    break

                r.raise_for_status()

                if len(r.content) < 50:
                    results[desc] = "empty"
                    break

                # Save the file
                with open(save_path, "wb") as f:
                    f.write(r.content)
                results[desc] = "ok"
                break

            except requests.exceptions.RequestException as e:
                if attempt == max_retries:
                    results[desc] = f"error: {str(e)[:50]}"
                time.sleep(3 * attempt)

    return results


def main():
    DOWNLOAD_DIR.mkdir(exist_ok=True)

    print(f"Downloading CAISO data from {START_DATE} to {END_DATE}")
    print(f"Output directory: {DOWNLOAD_DIR}")
    print("=" * 80)

    total_days = (END_DATE - START_DATE).days + 1
    current = START_DATE
    day_num = 0
    success_count = 0
    error_count = 0

    while current <= END_DATE:
        day_num += 1
        date_str = current.strftime("%Y-%m-%d")

        # Check if both files already exist
        fs_path = DOWNLOAD_DIR / f"{current.strftime('%Y%m%d')}_fuelsource.csv"
        rn_path = DOWNLOAD_DIR / f"{current.strftime('%Y%m%d')}_renewables.csv"

        if fs_path.exists() and rn_path.exists():
            if day_num % 100 == 0:
                print(f"[{day_num}/{total_days}] {date_str}: already downloaded")
            current += datetime.timedelta(days=1)
            success_count += 1
            continue

        results = download_day(current)
        status = " | ".join(f"{k}={v}" for k, v in results.items())
        print(f"[{day_num}/{total_days}] {date_str}: {status}")

        if all(v in ["ok", "exists"] for v in results.values()):
            success_count += 1
        else:
            error_count += 1

        current += datetime.timedelta(days=1)

        # Polite delay
        time.sleep(0.5)

    # Summary
    print("\n" + "=" * 80)
    print(f"Download complete!")
    print(f"  Success: {success_count} days")
    print(f"  Errors: {error_count} days")

    fs_count = len(list(DOWNLOAD_DIR.glob("*_fuelsource.csv")))
    rn_count = len(list(DOWNLOAD_DIR.glob("*_renewables.csv")))
    print(f"  Files: {fs_count} fuelsource + {rn_count} renewables")


if __name__ == "__main__":
    main()
