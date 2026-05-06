"""
Parallel download of CAISO Demand Trend data.
Splits work across multiple Chrome instances for faster download.
"""
import os
import time
import datetime
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import multiprocessing
import sys

DOWNLOAD_DIR = Path(__file__).parent / "caiso_demand_downloads"
DOWNLOAD_DIR.mkdir(exist_ok=True)

def wait_for_download(timeout=30):
    """Wait for download to complete."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        downloading = list(DOWNLOAD_DIR.glob("*.crdownload"))
        if not downloading:
            time.sleep(1)
            return True
        time.sleep(0.5)
    return False

def rename_downloaded_file(date):
    """Rename the downloaded file."""
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

def download_worker(start_date, end_date, worker_id):
    """Worker process to download a range of dates."""
    chrome_options = webdriver.ChromeOptions()
    prefs = {
        "download.default_directory": str(DOWNLOAD_DIR.absolute()),
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    }
    chrome_options.add_experimental_option("prefs", prefs)
    chrome_options.add_argument("--headless")  # Run headless for parallel
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=chrome_options)

    try:
        current_date = start_date
        success = 0
        skip = 0
        errors = 0

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
                                    print(f"[Worker {worker_id}] {current_date.strftime('%Y-%m-%d')}: OK ({success}/{success+errors})")
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
            time.sleep(1)  # Brief pause

        print(f"[Worker {worker_id}] Complete: {success} OK, {skip} skipped, {errors} errors")

    finally:
        driver.quit()

def main():
    """Main parallel download coordinator."""
    # One Chrome instance per year (2020-2025)
    years = [2020, 2021, 2022, 2023, 2024, 2025]

    print("=" * 70)
    print(f"Parallel Download: {len(years)} workers (one per year)")
    print("=" * 70)

    workers = []
    for i, year in enumerate(years):
        worker_start = datetime.date(year, 1, 1)
        worker_end = datetime.date(year, 12, 31)

        print(f"Worker {i+1}: Year {year} ({worker_start} to {worker_end})")

        p = multiprocessing.Process(target=download_worker, args=(worker_start, worker_end, i+1))
        p.start()
        workers.append(p)

        time.sleep(2)  # Stagger startup

    print("\nAll workers started. Downloading...")
    print("=" * 70)

    # Wait for all workers
    for p in workers:
        p.join()

    print("\n" + "=" * 70)
    print(f"Complete! Total files: {len(list(DOWNLOAD_DIR.glob('*.csv')))}")
    print("=" * 70)

if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
