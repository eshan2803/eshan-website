"""
Automated browser-based download of CAISO supply data using Selenium.

This script automates the manual process:
1. Navigate to https://www.caiso.com/todays-outlook/supply
2. For each date:
   - Supply trend: select date, download Chart Data (CSV)
   - Renewables trend: select date, enable "Show Demand", download Chart Data (CSV)

Requirements:
    pip install selenium
    Download ChromeDriver: https://chromedriver.chromium.org/
"""
import os
import time
import datetime
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

# Date range to download (2020-2021 have bad data)
START_DATE = datetime.date(2020, 1, 1)
END_DATE = datetime.date(2021, 12, 31)

# Output directory
DOWNLOAD_DIR = Path(__file__).parent / "caiso_downloads"
DOWNLOAD_DIR.mkdir(exist_ok=True)

# Configure Chrome to download files to our directory
chrome_options = Options()
chrome_options.add_experimental_option("prefs", {
    "download.default_directory": str(DOWNLOAD_DIR.absolute()),
    "download.prompt_for_download": False,
    "download.directory_upgrade": True,
    "safebrowsing.enabled": True
})

# Optional: run headless (no visible browser window)
# chrome_options.add_argument("--headless")


def wait_for_download(download_dir, timeout=30):
    """Wait for a file to finish downloading (no .crdownload files)."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        # Check if any files are still downloading
        downloading = list(download_dir.glob("*.crdownload"))
        if not downloading:
            time.sleep(1)  # Extra second to ensure file is complete
            return True
        time.sleep(0.5)
    return False


def download_day(driver, date):
    """Download supply and renewables data for a single date."""
    date_str = date.strftime("%-m/%-d/%Y")  # Format: 1/1/2020
    print(f"\n  Processing {date.strftime('%Y-%m-%d')}...")

    try:
        # Navigate to the page
        driver.get("https://www.caiso.com/todays-outlook/supply")

        # Wait for page to load
        time.sleep(3)

        # ====================
        # SUPPLY TREND CHART
        # ====================
        print("    Downloading Supply trend...")

        # Find the date input for Supply trend chart
        # The input might have id like "supply-date" or similar
        # We'll need to inspect the actual page to find the correct selector
        supply_date_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='text'][placeholder*='date' i]"))
        )

        # Clear and enter the date
        supply_date_input.clear()
        supply_date_input.send_keys(date_str)
        time.sleep(1)

        # Find and click the Download button for Supply trend
        # Look for a button with text "Download" near the Supply trend chart
        download_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Download')]")
        download_button.click()
        time.sleep(1)

        # Click "Chart data (CSV)" option
        csv_option = driver.find_element(By.XPATH, "//a[contains(text(), 'Chart data') and contains(text(), 'CSV')]")
        csv_option.click()

        # Wait for download to complete
        wait_for_download(DOWNLOAD_DIR, timeout=30)
        print("    ✓ Supply trend downloaded")

        # ====================
        # RENEWABLES TREND CHART
        # ====================
        print("    Downloading Renewables trend...")

        # Scroll down to Renewables chart
        driver.execute_script("window.scrollBy(0, 500);")
        time.sleep(1)

        # Find the date input for Renewables trend chart
        renewables_date_input = driver.find_elements(By.CSS_SELECTOR, "input[type='text'][placeholder*='date' i]")[1]

        # Clear and enter the date
        renewables_date_input.clear()
        renewables_date_input.send_keys(date_str)
        time.sleep(1)

        # Enable "Show Demand" option
        show_demand_checkbox = driver.find_element(By.XPATH, "//input[@type='checkbox' and following-sibling::*[contains(text(), 'Show Demand')]]")
        if not show_demand_checkbox.is_selected():
            show_demand_checkbox.click()
        time.sleep(1)

        # Find and click the Download button for Renewables trend
        download_buttons = driver.find_elements(By.XPATH, "//button[contains(text(), 'Download')]")
        renewables_download = download_buttons[1]  # Second download button
        renewables_download.click()
        time.sleep(1)

        # Click "Chart data (CSV)" option
        csv_options = driver.find_elements(By.XPATH, "//a[contains(text(), 'Chart data') and contains(text(), 'CSV')]")
        csv_options[1].click()  # Second CSV option

        # Wait for download to complete
        wait_for_download(DOWNLOAD_DIR, timeout=30)
        print("    ✓ Renewables trend downloaded")

        # Rename downloaded files with date prefix
        # Files are typically named like "CAISO-supply-MMDDYYYY.csv" and "CAISO-renewables-MMDDYYYY.csv"
        # We'll look for the most recently downloaded files
        time.sleep(2)
        csv_files = sorted(DOWNLOAD_DIR.glob("*.csv"), key=os.path.getmtime, reverse=True)

        if len(csv_files) >= 2:
            # Rename with our date format
            date_prefix = date.strftime("%Y%m%d")
            supply_file = csv_files[1]  # Second most recent (first downloaded)
            renewables_file = csv_files[0]  # Most recent

            supply_file.rename(DOWNLOAD_DIR / f"{date_prefix}_supply_raw.csv")
            renewables_file.rename(DOWNLOAD_DIR / f"{date_prefix}_renewables_raw.csv")

            print(f"    ✓ Files renamed: {date_prefix}_supply_raw.csv, {date_prefix}_renewables_raw.csv")

        return True

    except Exception as e:
        print(f"    ✗ ERROR: {str(e)[:100]}")
        return False


def main():
    print("=" * 80)
    print("CAISO Data Browser Download")
    print("=" * 80)
    print(f"Date range: {START_DATE} to {END_DATE}")
    print(f"Output directory: {DOWNLOAD_DIR}")
    print()
    print("Starting browser automation...")

    # Initialize Chrome driver
    driver = webdriver.Chrome(options=chrome_options)
    driver.maximize_window()

    try:
        total_days = (END_DATE - START_DATE).days + 1
        current = START_DATE
        day_num = 0
        success_count = 0
        error_count = 0

        while current <= END_DATE:
            day_num += 1

            # Check if files already exist
            date_prefix = current.strftime("%Y%m%d")
            supply_file = DOWNLOAD_DIR / f"{date_prefix}_supply_raw.csv"
            renewables_file = DOWNLOAD_DIR / f"{date_prefix}_renewables_raw.csv"

            if supply_file.exists() and renewables_file.exists():
                if day_num % 50 == 0:
                    print(f"[{day_num}/{total_days}] {current.strftime('%Y-%m-%d')}: already downloaded")
                current += datetime.timedelta(days=1)
                success_count += 1
                continue

            print(f"[{day_num}/{total_days}] {current.strftime('%Y-%m-%d')}:")

            success = download_day(driver, current)
            if success:
                success_count += 1
            else:
                error_count += 1

            current += datetime.timedelta(days=1)

            # Polite delay between downloads
            time.sleep(2)

        # Summary
        print("\n" + "=" * 80)
        print("Download complete!")
        print(f"  Success: {success_count} days")
        print(f"  Errors: {error_count} days")
        print(f"  Files in {DOWNLOAD_DIR}: {len(list(DOWNLOAD_DIR.glob('*.csv')))}")

    finally:
        driver.quit()
        print("\nBrowser closed.")


if __name__ == "__main__":
    main()
