"""
Download a random fuelsource file and compare with existing to verify integrity.
"""
import os
import csv
import random
import time
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

# Pick 3 random dates to test
test_dates = [
    datetime(2020, 7, 15).date(),
    datetime(2022, 3, 20).date(),
    datetime(2024, 11, 8).date(),
]

DOWNLOAD_DIR = os.path.join(os.getcwd(), "test_fuelsource_download")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Setup Chrome
chrome_options = Options()
chrome_options.add_experimental_option("prefs", {
    "download.default_directory": DOWNLOAD_DIR,
    "download.prompt_for_download": False,
})

driver = webdriver.Chrome(options=chrome_options)

print("="*80)
print("TESTING FUELSOURCE FILE INTEGRITY")
print("="*80)

try:
    for test_date in test_dates:
        date_str = test_date.strftime('%Y%m%d')
        existing_file = f"caiso_supply/{date_str}_fuelsource.csv"

        print(f"\nTest date: {test_date} ({date_str})")
        print("-"*80)

        if not os.path.exists(existing_file):
            print(f"  SKIP: {existing_file} doesn't exist")
            continue

        # Download fresh copy
        print(f"  Downloading fresh copy...")

        driver.get("http://www.caiso.com/outlook/SP/renewables.html")
        time.sleep(3)

        try:
            # Find date picker
            date_picker = driver.find_element(By.ID, "fuelsourceDatePicker")
            date_picker.clear()
            date_picker.send_keys(test_date.strftime('%m/%d/%Y'))
            time.sleep(2)

            # Click CSV download button
            csv_button = driver.find_element(By.XPATH, "//a[contains(@title, 'fuel') and contains(@title, 'CSV')]")
            csv_button.click()
            time.sleep(4)

            # Find downloaded file
            import glob
            downloads = glob.glob(os.path.join(DOWNLOAD_DIR, "*.csv"))
            if not downloads:
                print(f"  ERROR: No file downloaded")
                continue

            latest_download = max(downloads, key=os.path.getctime)

            # Compare files
            print(f"  Comparing files...")

            # Read existing file
            with open(existing_file, 'r', encoding='utf-8-sig') as f:
                existing_reader = csv.DictReader(f)
                existing_rows = list(existing_reader)

            # Read downloaded file
            with open(latest_download, 'r', encoding='utf-8-sig') as f:
                downloaded_reader = csv.DictReader(f)
                downloaded_rows = list(downloaded_reader)

            # Compare
            print(f"  Existing file: {len(existing_rows)} rows")
            print(f"  Downloaded file: {len(downloaded_rows)} rows")

            if len(existing_rows) != len(downloaded_rows):
                print(f"  *** ROW COUNT MISMATCH ***")
                continue

            # Compare data (first 10 rows, key columns)
            differences = 0
            for i in range(min(10, len(existing_rows))):
                ex = existing_rows[i]
                dl = downloaded_rows[i]

                # Compare key columns
                for col in ['Time', 'Solar', 'Wind', 'Natural gas', 'Batteries']:
                    if col in ex and col in dl:
                        if ex[col] != dl[col]:
                            differences += 1
                            if differences <= 3:
                                print(f"  Diff row {i}, {col}: existing='{ex[col]}', downloaded='{dl[col]}'")

            if differences == 0:
                print(f"  *** MATCH: Files are identical (sampled 10 rows) ***")
            else:
                print(f"  *** MISMATCH: {differences} differences found ***")
                print(f"  *** This suggests file may be mislabeled! ***")

            # Clean up downloaded file
            os.remove(latest_download)

        except Exception as e:
            print(f"  ERROR: {e}")

        time.sleep(2)

finally:
    driver.quit()

print(f"\n{'='*80}")
print("TEST COMPLETE")
print("="*80)
