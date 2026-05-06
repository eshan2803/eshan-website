"""
Download CAISO Renewables Trend data with Demand for 2020-2025.

This script downloads renewable trend CSV files which include the Demand row
that we need for correct penetration calculations.
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

# Date range to download
START_DATE = datetime.date(2020, 1, 1)
END_DATE = datetime.date(2025, 12, 31)

# Output directory
DOWNLOAD_DIR = Path(__file__).parent / "caiso_downloads"
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
# Comment out to see browser
# chrome_options.add_argument("--headless")

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
    # Find the most recently downloaded CSV
    csv_files = list(DOWNLOAD_DIR.glob("*.csv"))
    if not csv_files:
        return False

    latest = max(csv_files, key=lambda p: p.stat().st_mtime)

    # Rename to our format
    new_name = DOWNLOAD_DIR / f"{date.strftime('%Y%m%d')}_renewables_raw.csv"

    # Skip if already exists
    if new_name.exists():
        if latest != new_name:
            latest.unlink()  # Delete duplicate
        return True

    latest.rename(new_name)
    return True

def download_day(driver, date):
    """Download renewables trend data with demand for a single date."""
    # Format: 1/1/2020 (no leading zeros)
    date_str = f"{date.month}/{date.day}/{date.year}"
    output_file = DOWNLOAD_DIR / f"{date.strftime('%Y%m%d')}_renewables_raw.csv"

    # Skip if already downloaded
    if output_file.exists():
        print(f"  {date.strftime('%Y-%m-%d')}: Already downloaded, skipping")
        return True

    print(f"  {date.strftime('%Y-%m-%d')}: Downloading...", end="", flush=True)

    try:
        # Navigate to supply page
        driver.get("https://www.caiso.com/todays-outlook/supply")
        time.sleep(3)

        # Find Renewables Trend tab/section
        # Look for text containing "Renewables"
        try:
            renewables_section = driver.find_element(By.XPATH, "//*[contains(text(), 'Renewables trend') or contains(text(), 'Renewables Trend')]")
            driver.execute_script("arguments[0].scrollIntoView(true);", renewables_section)
            time.sleep(1)
        except:
            print(" ERROR: Could not find Renewables section")
            return False

        # Find date input near renewables section
        # Try multiple selectors
        date_input = None
        selectors = [
            "//input[@type='text' and contains(@placeholder, 'date')]",
            "//input[@type='date']",
            "//input[contains(@id, 'renewables')]",
            "(//input[@type='text'])[last()]"  # Often the last date input
        ]

        for selector in selectors:
            try:
                inputs = driver.find_elements(By.XPATH, selector)
                if inputs:
                    # Try the last one (usually renewables is second on page)
                    date_input = inputs[-1]
                    break
            except:
                continue

        if not date_input:
            print(" ERROR: Could not find date input")
            return False

        # Enter date
        date_input.clear()
        date_input.send_keys(date_str)
        date_input.send_keys(Keys.RETURN)
        time.sleep(3)

        # Enable "Show Demand" checkbox if present
        try:
            # Look for checkbox with label "Show Demand"
            checkboxes = driver.find_elements(By.XPATH, "//input[@type='checkbox']")
            for cb in checkboxes:
                # Check nearby text for "Demand"
                parent = cb.find_element(By.XPATH, "./..")
                if "demand" in parent.text.lower():
                    if not cb.is_selected():
                        cb.click()
                        time.sleep(1)
                    break
        except:
            pass  # Checkbox might already be enabled

        # Find Download button (look for last one on page, usually for renewables)
        download_buttons = driver.find_elements(By.XPATH, "//button[contains(text(), 'Download')]")
        if not download_buttons:
            print(" ERROR: No download button found")
            return False

        download_button = download_buttons[-1]  # Use last one
        download_button.click()
        time.sleep(1)

        # Click "Chart data (CSV)" option
        csv_links = driver.find_elements(By.XPATH, "//*[contains(text(), 'Chart') and contains(text(), 'CSV')]")
        if not csv_links:
            print(" ERROR: No CSV option found")
            return False

        csv_links[0].click()

        # Wait for download
        if not wait_for_download(timeout=30):
            print(" TIMEOUT waiting for download")
            return False

        # Rename file
        if not rename_downloaded_file(date):
            print(" ERROR renaming file")
            return False

        print(" ✓")
        return True

    except Exception as e:
        print(f" ERROR: {e}")
        return False

# Main execution
driver = webdriver.Chrome(options=chrome_options)

try:
    print("=" * 60)
    print("Downloading CAISO Renewables Trend Data (2020-2025)")
    print("=" * 60)

    current_date = START_DATE
    success_count = 0
    skip_count = 0
    error_count = 0

    while current_date <= END_DATE:
        result = download_day(driver, current_date)

        if result is True:
            success_count += 1
        elif result == "skip":
            skip_count += 1
        else:
            error_count += 1
            # On error, wait longer before retry
            time.sleep(5)

        current_date += datetime.timedelta(days=1)

        # Brief pause between downloads
        time.sleep(2)

        # Progress update every 50 days
        if success_count % 50 == 0 and success_count > 0:
            print(f"\nProgress: {success_count} downloaded, {skip_count} skipped, {error_count} errors")

    print("\n" + "=" * 60)
    print(f"Complete: {success_count} downloaded, {skip_count} skipped, {error_count} errors")
    print("=" * 60)

finally:
    driver.quit()
