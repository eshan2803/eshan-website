"""
Download demand data for missing dates only.
"""
import os
import time
import datetime
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

DOWNLOAD_DIR = Path(__file__).parent / "caiso_demand_downloads"
DOWNLOAD_DIR.mkdir(exist_ok=True)

chrome_options = webdriver.ChromeOptions()
prefs = {
    "download.default_directory": str(DOWNLOAD_DIR.absolute()),
    "download.prompt_for_download": False,
    "download.directory_upgrade": True,
    "safebrowsing.enabled": True
}
chrome_options.add_experimental_option("prefs", prefs)
chrome_options.add_argument("--headless")

def wait_for_download(timeout=30):
    start_time = time.time()
    while time.time() - start_time < timeout:
        downloading = list(DOWNLOAD_DIR.glob("*.crdownload"))
        if not downloading:
            time.sleep(1)
            return True
        time.sleep(0.5)
    return False

def rename_downloaded_file(date):
    csv_files = list(DOWNLOAD_DIR.glob("*.csv"))
    if not csv_files:
        return False
    latest = max(csv_files, key=lambda p: p.stat().st_mtime)
    new_name = DOWNLOAD_DIR / f"{date.strftime('%Y%m%d')}_demand.csv"
    if new_name.exists():
        if latest != new_name:
            latest.unlink()
        return True
    latest.rename(new_name)
    return True

# Read missing dates (check for temp file first, then regular file)
dates_file = None
if os.path.exists("temp_missing_dates.txt"):
    dates_file = "temp_missing_dates.txt"
elif os.path.exists("missing_dates.txt"):
    dates_file = "missing_dates.txt"
else:
    print("ERROR: No missing dates file found (temp_missing_dates.txt or missing_dates.txt)")
    exit(1)

with open(dates_file, "r") as f:
    missing_dates = [line.strip() for line in f if line.strip()]

print(f"Downloading {len(missing_dates)} missing dates...")
print("=" * 60)

driver = webdriver.Chrome(options=chrome_options)
success = 0
errors = 0

try:
    for i, date_str in enumerate(missing_dates):
        date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        date_input_str = f"{date.month}/{date.day}/{date.year}"

        print(f"[{i+1}/{len(missing_dates)}] {date_str}...", end="", flush=True)

        try:
            driver.get("https://www.caiso.com/todays-outlook/demand")
            time.sleep(3)

            date_inputs = driver.find_elements(By.XPATH, "//input[@type='text' or @type='date']")
            if date_inputs:
                date_input = date_inputs[0]
                date_input.clear()
                time.sleep(0.5)
                date_input.send_keys(date_input_str)
                date_input.send_keys(Keys.RETURN)
                time.sleep(3)

                download_buttons = driver.find_elements(By.XPATH, "//button[contains(text(), 'Download')]")
                if download_buttons:
                    download_buttons[0].click()
                    time.sleep(2)

                    csv_options = driver.find_elements(By.XPATH, "//*[contains(text(), 'Chart') and contains(text(), 'CSV')]")
                    if csv_options:
                        csv_options[0].click()

                        if wait_for_download(timeout=30):
                            if rename_downloaded_file(date):
                                success += 1
                                print(" OK")
                            else:
                                errors += 1
                                print(" ERROR renaming")
                        else:
                            errors += 1
                            print(" TIMEOUT")
                    else:
                        errors += 1
                        print(" NO CSV OPTION")
                else:
                    errors += 1
                    print(" NO DOWNLOAD BUTTON")
            else:
                errors += 1
                print(" NO DATE INPUT")

        except Exception as e:
            errors += 1
            print(f" ERROR: {str(e)[:30]}")
            time.sleep(2)

        time.sleep(1)

        if (i + 1) % 10 == 0:
            print(f"\nProgress: {success} OK, {errors} errors\n")

finally:
    driver.quit()

print("\n" + "=" * 60)
print(f"Complete: {success} downloaded, {errors} errors")
print("=" * 60)
