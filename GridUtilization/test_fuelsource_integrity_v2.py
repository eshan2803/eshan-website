"""
Download random fuelsource files via API and compare with existing files.
"""
import os
import csv
import requests
from datetime import datetime

# Pick 3 random dates to test
test_dates = [
    datetime(2020, 7, 15).date(),
    datetime(2022, 3, 20).date(),
    datetime(2024, 11, 8).date(),
]

DOWNLOAD_DIR = "test_fuelsource_download"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

print("="*80)
print("TESTING FUELSOURCE FILE INTEGRITY")
print("="*80)

for test_date in test_dates:
    date_str = test_date.strftime('%Y%m%d')
    existing_file = f"caiso_supply/{date_str}_fuelsource.csv"

    print(f"\nTest date: {test_date} ({date_str})")
    print("-"*80)

    if not os.path.exists(existing_file):
        print(f"  SKIP: {existing_file} doesn't exist locally")
        continue

    # Download fresh copy via API
    url = f"https://www.caiso.com/outlook/SP/history/{date_str}_fuelsource.csv"
    print(f"  Downloading: {url}")

    try:
        response = requests.get(url, timeout=30)

        if response.status_code != 200:
            print(f"  ERROR: HTTP {response.status_code}")
            continue

        # Save downloaded file
        downloaded_file = os.path.join(DOWNLOAD_DIR, f"{date_str}_fuelsource.csv")
        with open(downloaded_file, 'wb') as f:
            f.write(response.content)

        print(f"  Downloaded successfully")

        # Read both files
        with open(existing_file, 'r', encoding='utf-8-sig') as f:
            existing_reader = csv.DictReader(f)
            existing_rows = list(existing_reader)

        with open(downloaded_file, 'r', encoding='utf-8-sig') as f:
            downloaded_reader = csv.DictReader(f)
            downloaded_rows = list(downloaded_reader)

        print(f"  Existing file: {len(existing_rows)} rows")
        print(f"  Downloaded file: {len(downloaded_rows)} rows")

        if len(existing_rows) != len(downloaded_rows):
            print(f"  *** ROW COUNT MISMATCH ***")
            continue

        # Compare data (all rows, key columns)
        differences = 0
        sample_diffs = []

        for i in range(len(existing_rows)):
            ex = existing_rows[i]
            dl = downloaded_rows[i]

            # Compare key columns
            for col in ['Time', 'Solar', 'Wind', 'Natural gas', 'Batteries']:
                if col in ex and col in dl:
                    if ex[col] != dl[col]:
                        differences += 1
                        if len(sample_diffs) < 5:
                            sample_diffs.append({
                                'row': i,
                                'col': col,
                                'existing': ex[col],
                                'downloaded': dl[col]
                            })

        if differences == 0:
            print(f"  *** PERFECT MATCH: Files are identical ***")
            print(f"  File is correctly labeled!")
        else:
            print(f"  *** MISMATCH: {differences} differences found ***")
            print(f"  Sample differences:")
            for diff in sample_diffs:
                print(f"    Row {diff['row']}, {diff['col']}: existing='{diff['existing']}', downloaded='{diff['downloaded']}'")
            print(f"  *** This suggests file may be mislabeled or corrupted! ***")

    except Exception as e:
        print(f"  ERROR: {e}")

print(f"\n{'='*80}")
print("TEST COMPLETE")
print("="*80)
print("\nConclusion:")
print("  If all tests show PERFECT MATCH, fuelsource files are correctly labeled.")
print("  If any test shows MISMATCH, fuelsource files may have same issue as demand.")
