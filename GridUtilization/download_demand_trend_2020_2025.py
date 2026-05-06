"""
Download CAISO Demand Trend data for 2020-2025.

Downloads from https://www.caiso.com/todays-outlook/demand
"""
import os
import time
import datetime
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys

# Date range
START_DATE = datetime.date(2020, 1, 1)
END_DATE = datetime.date(2025, 12, 31)

# Output directory
DOWNLOAD_DIR = Path(__file__).parent / "caiso_demand_downloads"
DOWNLOAD_DIR.mkdir(exist_ok=True)

# Configure Chrome
chrome_options = webdriver.ChromeOptions()
prefs = {
    "download.default_directory": str(DOWNLOAD_DIR.absolute()),
    "download.prompt_for_download": False,
    "download.directory_upgrade": True,
    "safebrowsing.enabled": True
}
chrome_options.add_experimental_option("prefs", prefs)

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
    """Rename the downloaded file to our standard format."""
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

def download_day(driver, date):
    """Download demand trend data for a single date."""
    date_str = f"{date.month}/{date.day}/{date.year}"
    output_file = DOWNLOAD_DIR / f"{date.strftime('%Y%m%d')}_demand.csv"

    if output_file.exists():
        print(f"  {date.strftime('%Y-%m-%d')}: Already downloaded")
        return True

    print(f"  {date.strftime('%Y-%m-%d')}: Downloading...", end="", flush=True)

    try:
        # Navigate to demand page
        driver.get("https://www.caiso.com/todays-outlook/demand")
        time.sleep(4)

        # Find date input
        date_inputs = driver.find_elements(By.XPATH, "//input[@type='text' or @type='date']")
        if not date_inputs:
            print(" ERROR: No date input found")
            return False

        date_input = date_inputs[0]  # Usually first one on demand page
        date_input.clear()
        time.sleep(0.5)
        date_input.send_keys(date_str)
        date_input.send_keys(Keys.RETURN)
        time.sleep(4)

        # Find Download button
        download_buttons = driver.find_elements(By.XPATH, "//button[contains(text(), 'Download')]")
        if not download_buttons:
            print(" ERROR: No download button")
            return False

        download_buttons[0].click()
        time.sleep(2)

        # Click "Chart Data (CSV)"
        csv_options = driver.find_elements(By.XPATH, "//*[contains(text(), 'Chart') and contains(text(), 'CSV')]")
        if not csv_options:
            print(" ERROR: No CSV option")
            return False

        csv_options[0].click()

        # Wait for download
        if not wait_for_download(timeout=30):
            print(" TIMEOUT")
            return False

        # Rename file
        if not rename_downloaded_file(date):
            print(" ERROR renaming")
            return False

        print(" OK")
        return True

    except Exception as e:
        print(f" ERROR: {str(e)[:50]}")
        return False

# Main
driver = webdriver.Chrome(options=chrome_options)

try:
    print("=" * 60)
    print("Downloading CAISO Demand Trend Data (2020-2025)")
    print("=" * 60)

    current_date = START_DATE
    success = 0
    errors = 0

    while current_date <= END_DATE:
        result = download_day(driver, current_date)

        if result:
            success += 1
        else:
            errors += 1
            time.sleep(5)  # Wait longer after error

        current_date += datetime.timedelta(days=1)
        time.sleep(2)

        if success % 100 == 0 and success > 0:
            print(f"\nProgress: {success} downloaded, {errors} errors")

    print("\n" + "=" * 60)
    print(f"Complete: {success} downloaded, {errors} errors")
    print("=" * 60)

finally:
    driver.quit()
