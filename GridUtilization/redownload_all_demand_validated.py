"""
Re-download ALL demand files with validation.
Based on working download_demand_parallel.py script.
"""
import os
import time
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

# Configuration
DOWNLOAD_DIR = Path(__file__).parent / "caiso_demand_clean"
OLD_DEMAND_DIR = Path(__file__).parent / "caiso_demand_downloads"
BACKUP_DIR = Path(__file__).parent / "caiso_demand_downloads_old_backup"

# Create clean download directory
DOWNLOAD_DIR.mkdir(exist_ok=True)

# Backup old directory
if OLD_DEMAND_DIR.exists():
    print(f"Backing up old demand directory to {BACKUP_DIR}")
    if BACKUP_DIR.exists():
        shutil.rmtree(BACKUP_DIR)
    shutil.move(str(OLD_DEMAND_DIR), str(BACKUP_DIR))
    print(f"Backup complete")

# Generate all dates
start_date = datetime(2020, 1, 1).date()
end_date = datetime(2026, 4, 1).date()
all_dates = []
current = start_date
while current <= end_date:
    all_dates.append(current)
    current += timedelta(days=1)

print(f"\n{'='*80}")
print(f"Re-downloading ALL demand files with validation")
print(f"{'='*80}")
print(f"Total dates: {len(all_dates)}")
print(f"Date range: {all_dates[0]} to {all_dates[-1]}")
print(f"Download to: {DOWNLOAD_DIR}")
print(f"{'='*80}\n")

# Setup Chrome
chrome_options = webdriver.ChromeOptions()
prefs = {
    "download.default_directory": str(DOWNLOAD_DIR.absolute()),
    "download.prompt_for_download": False,
    "download.directory_upgrade": True,
    "safebrowsing.enabled": True
}
chrome_options.add_experimental_option("prefs", prefs)

driver = webdriver.Chrome(options=chrome_options)

downloaded_count = 0
validation_failures = []
download_failures = []

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

def validate_and_rename(expected_date):
    """Validate downloaded file and rename to correct format."""
    csv_files = list(DOWNLOAD_DIR.glob("*.csv"))
    if not csv_files:
        return False, "No CSV file found"

    # Get most recent file
    latest = max(csv_files, key=lambda p: p.stat().st_mtime)

    # Wait a bit for file lock to release
    time.sleep(2)

    try:
        # Read and validate cell A1
        with open(latest, 'r', encoding='utf-8-sig') as f:
            first_line = f.readline().strip()

        if 'Demand' in first_line:
            parts = first_line.replace(',', ' ').split()
            if len(parts) >= 2:
                actual_date_str = parts[1]  # MM/DD/YYYY format
                actual_date = datetime.strptime(actual_date_str, '%m/%d/%Y').date()

                expected_date_str = expected_date.strftime('%Y%m%d')
                actual_date_str_formatted = actual_date.strftime('%Y%m%d')

                if actual_date == expected_date:
                    # Valid! Rename to correct format
                    correct_name = DOWNLOAD_DIR / f"{expected_date_str}_demand.csv"

                    if correct_name.exists():
                        correct_name.unlink()

                    # Retry rename with backoff
                    for retry in range(5):
                        try:
                            latest.rename(correct_name)
                            return True, f"Valid - {actual_date_str}"
                        except PermissionError:
                            if retry < 4:
                                time.sleep(1)
                            else:
                                raise
                else:
                    # Date mismatch - delete file
                    time.sleep(1)
                    latest.unlink()
                    return False, f"Date mismatch: expected {expected_date}, got {actual_date}"
            else:
                time.sleep(1)
                latest.unlink()
                return False, f"Cannot parse date from: {first_line}"
        else:
            time.sleep(1)
            latest.unlink()
            return False, f"Invalid file format: {first_line[:50]}"
    except Exception as e:
        if latest.exists():
            time.sleep(1)
            try:
                latest.unlink()
            except:
                pass
        return False, f"Validation error: {e}"

try:
    for i, date in enumerate(all_dates):
        date_str = f"{date.month}/{date.day}/{date.year}"
        date_key = date.strftime('%Y%m%d')

        print(f"[{i+1}/{len(all_dates)}] {date} ", end='', flush=True)

        try:
            # Navigate to demand page
            driver.get("https://www.caiso.com/todays-outlook/demand")
            time.sleep(3)

            # Find date input
            date_inputs = driver.find_elements(By.XPATH, "//input[@type='text' or @type='date']")
            if not date_inputs:
                print(f"ERROR: No date input found")
                download_failures.append({'date': date_key, 'error': 'No date input'})
                continue

            date_input = date_inputs[0]
            date_input.clear()
            time.sleep(0.5)
            date_input.send_keys(date_str)
            date_input.send_keys(Keys.RETURN)
            time.sleep(3)

            # Find Download button
            download_buttons = driver.find_elements(By.XPATH, "//button[contains(text(), 'Download')]")
            if not download_buttons:
                print(f"ERROR: No download button")
                download_failures.append({'date': date_key, 'error': 'No download button'})
                continue

            download_buttons[0].click()
            time.sleep(2)

            # Find CSV option
            csv_options = driver.find_elements(By.XPATH, "//*[contains(text(), 'Chart') and contains(text(), 'CSV')]")
            if not csv_options:
                print(f"ERROR: No CSV option")
                download_failures.append({'date': date_key, 'error': 'No CSV option'})
                continue

            csv_options[0].click()

            # Wait for download
            if wait_for_download(timeout=30):
                # Validate and rename
                success, message = validate_and_rename(date)

                if success:
                    downloaded_count += 1
                    print(f"OK - {message}")
                else:
                    print(f"VALIDATION FAILED - {message}")
                    validation_failures.append({'date': date_key, 'reason': message})
            else:
                print(f"TIMEOUT - Download didn't complete")
                download_failures.append({'date': date_key, 'error': 'Download timeout'})

        except Exception as e:
            print(f"ERROR - {e}")
            download_failures.append({'date': date_key, 'error': str(e)})

        # Progress report every 100 files
        if (i + 1) % 100 == 0:
            print(f"\n{'='*80}")
            print(f"Progress: {downloaded_count}/{i+1} successful ({downloaded_count/(i+1)*100:.1f}%)")
            print(f"Failed downloads: {len(download_failures)}")
            print(f"Validation failures: {len(validation_failures)}")
            print(f"{'='*80}\n")

        time.sleep(1)  # Rate limiting

finally:
    driver.quit()

# Final report
print(f"\n{'='*80}")
print(f"DOWNLOAD COMPLETE")
print(f"{'='*80}")
print(f"Total dates: {len(all_dates)}")
print(f"Successfully downloaded and validated: {downloaded_count}")
print(f"Failed downloads: {len(download_failures)}")
print(f"Validation failures: {len(validation_failures)}")
print(f"Success rate: {downloaded_count/len(all_dates)*100:.1f}%")

if download_failures:
    print(f"\n{'='*80}")
    print(f"Failed downloads (first 20):")
    for f in download_failures[:20]:
        print(f"  {f['date']}: {f['error']}")

    with open('failed_demand_downloads.txt', 'w') as f:
        for fail in download_failures:
            f.write(f"{fail['date']}\n")
    print(f"\nSaved {len(download_failures)} failed dates to failed_demand_downloads.txt")

if validation_failures:
    print(f"\n{'='*80}")
    print(f"Validation failures (first 20):")
    for v in validation_failures[:20]:
        print(f"  {v['date']}: {v['reason']}")

    with open('validation_failures.txt', 'w') as f:
        for fail in validation_failures:
            f.write(f"{fail['date']}: {fail['reason']}\n")

print(f"\n{'='*80}")
print(f"Clean validated files saved to: {DOWNLOAD_DIR}")
if BACKUP_DIR.exists():
    print(f"Old files backed up to: {BACKUP_DIR}")
print(f"{'='*80}")
