"""
Download demand data for a specific year.
Usage: python download_demand_by_year.py <year>
"""
import os
import time
import datetime
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import sys

if len(sys.argv) < 2:
    print("Usage: python download_demand_by_year.py <year>")
    sys.exit(1)

YEAR = int(sys.argv[1])
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

driver = webdriver.Chrome(options=chrome_options)
start_date = datetime.date(YEAR, 1, 1)
end_date = datetime.date(YEAR, 12, 31)
current_date = start_date
success = 0
skip = 0
errors = 0

print(f"[Year {YEAR}] Starting download...")

try:
    while current_date <= end_date:
        date_str = f"{current_date.month}/{current_date.day}/{current_date.year}"
        output_file = DOWNLOAD_DIR / f"{current_date.strftime('%Y%m%d')}_demand.csv"

        if output_file.exists():
            skip += 1
            current_date += datetime.timedelta(days=1)
            continue

        try:
            driver.get("https://www.caiso.com/todays-outlook/demand")
            time.sleep(3)

            date_inputs = driver.find_elements(By.XPATH, "//input[@type='text' or @type='date']")
            if date_inputs:
                date_input = date_inputs[0]
                date_input.clear()
                time.sleep(0.5)
                date_input.send_keys(date_str)
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
                            if rename_downloaded_file(current_date):
                                success += 1
                                if success % 10 == 0:
                                    print(f"[Year {YEAR}] Progress: {success} OK, {skip} skipped, {errors} errors")
                            else:
                                errors += 1
                        else:
                            errors += 1
                    else:
                        errors += 1
                else:
                    errors += 1
            else:
                errors += 1

        except Exception as e:
            errors += 1
            time.sleep(2)

        current_date += datetime.timedelta(days=1)
        time.sleep(1)

    print(f"[Year {YEAR}] COMPLETE: {success} OK, {skip} skipped, {errors} errors")

finally:
    driver.quit()
