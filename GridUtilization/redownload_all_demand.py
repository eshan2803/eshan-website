"""
Re-download ALL demand files from scratch with validation.
Ensures filename date matches cell A1 date.
"""
import os
import time
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import glob

# Configuration
DOWNLOAD_DIR = os.path.join(os.getcwd(), "caiso_demand_clean")
OLD_DEMAND_DIR = os.path.join(os.getcwd(), "caiso_demand_downloads")
BACKUP_DIR = os.path.join(os.getcwd(), "caiso_demand_downloads_old_backup")

# Create clean download directory
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Backup old directory
if os.path.exists(OLD_DEMAND_DIR):
    print(f"Backing up old demand directory to {BACKUP_DIR}")
    import shutil
    if os.path.exists(BACKUP_DIR):
        shutil.rmtree(BACKUP_DIR)
    shutil.move(OLD_DEMAND_DIR, BACKUP_DIR)

# Generate all dates from 2020-01-01 to 2026-04-01
start_date = datetime(2020, 1, 1)
end_date = datetime(2026, 4, 1)
all_dates = []
current = start_date
while current <= end_date:
    all_dates.append(current)
    current += timedelta(days=1)

print(f"Total dates to download: {len(all_dates)}")
print(f"Date range: {all_dates[0].strftime('%Y-%m-%d')} to {all_dates[-1].strftime('%Y-%m-%d')}")

# Setup Chrome with download directory
chrome_options = Options()
chrome_options.add_experimental_option("prefs", {
    "download.default_directory": DOWNLOAD_DIR,
    "download.prompt_for_download": False,
    "download.directory_upgrade": True,
    "safebrowsing.enabled": True
})

driver = webdriver.Chrome(options=chrome_options)
wait = WebDriverWait(driver, 20)

downloaded_count = 0
failed_downloads = []
validation_failures = []

try:
    for i, date in enumerate(all_dates):
        date_str = date.strftime('%Y%m%d')
        date_display = date.strftime('%Y-%m-%d')

        print(f"\n[{i+1}/{len(all_dates)}] Downloading {date_display} ({date_str})")

        # Navigate to CAISO page
        url = "http://www.caiso.com/TodaysOutlook/Pages/default.aspx"
        driver.get(url)
        time.sleep(2)

        try:
            # Click on "Demand" tab
            demand_tab = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Demand')]")))
            demand_tab.click()
            time.sleep(1)

            # Find date picker input
            date_picker = wait.until(EC.presence_of_element_located((By.ID, "demandDatePicker")))

            # Clear and enter date (format MM/DD/YYYY)
            date_picker.clear()
            date_picker.send_keys(date.strftime('%m/%d/%Y'))
            time.sleep(1)

            # Click CSV download button
            csv_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(@title, 'demand') and contains(@title, 'CSV')]")))
            csv_button.click()

            # Wait for download to complete
            time.sleep(3)

            # Find the downloaded file
            downloads = glob.glob(os.path.join(DOWNLOAD_DIR, "*.csv"))
            if downloads:
                latest_file = max(downloads, key=os.path.getctime)

                # Validate: check cell A1 for date
                try:
                    with open(latest_file, 'r', encoding='utf-8-sig') as f:
                        first_line = f.readline().strip()
                        if 'Demand' in first_line:
                            parts = first_line.replace(',', ' ').split()
                            if len(parts) >= 2:
                                actual_date_str = parts[1]
                                actual_dt = datetime.strptime(actual_date_str, '%m/%d/%Y')
                                actual_date = actual_dt.strftime('%Y%m%d')

                                if actual_date == date_str:
                                    # Rename to correct format
                                    correct_name = f"{date_str}_demand.csv"
                                    correct_path = os.path.join(DOWNLOAD_DIR, correct_name)
                                    os.rename(latest_file, correct_path)
                                    downloaded_count += 1
                                    print(f"  SUCCESS: Validated and saved as {correct_name}")
                                else:
                                    print(f"  VALIDATION FAILED: Expected {date_str}, got {actual_date}")
                                    print(f"    Cell A1: {actual_date_str}")
                                    validation_failures.append({
                                        'expected': date_str,
                                        'actual': actual_date,
                                        'file': latest_file
                                    })
                                    # Delete invalid file
                                    os.remove(latest_file)
                            else:
                                print(f"  ERROR: Cannot parse date from cell A1: {first_line}")
                                validation_failures.append({
                                    'expected': date_str,
                                    'actual': 'unknown',
                                    'file': latest_file
                                })
                                os.remove(latest_file)
                except Exception as e:
                    print(f"  ERROR validating file: {e}")
                    validation_failures.append({
                        'expected': date_str,
                        'actual': 'error',
                        'error': str(e)
                    })
            else:
                print(f"  FAILED: No file downloaded")
                failed_downloads.append(date_str)

        except Exception as e:
            print(f"  ERROR: {e}")
            failed_downloads.append(date_str)

        # Progress update
        if (i + 1) % 50 == 0:
            print(f"\n{'='*80}")
            print(f"Progress: {downloaded_count}/{i+1} successful ({downloaded_count/(i+1)*100:.1f}%)")
            print(f"Failed: {len(failed_downloads)}, Validation failures: {len(validation_failures)}")
            print(f"{'='*80}")

        # Rate limiting
        time.sleep(1)

finally:
    driver.quit()

# Final report
print(f"\n{'='*80}")
print("DOWNLOAD COMPLETE")
print(f"{'='*80}")
print(f"Total dates: {len(all_dates)}")
print(f"Successfully downloaded: {downloaded_count}")
print(f"Failed downloads: {len(failed_downloads)}")
print(f"Validation failures: {len(validation_failures)}")

if failed_downloads:
    print(f"\nFailed downloads (first 20):")
    for d in failed_downloads[:20]:
        print(f"  {d}")

    with open('failed_demand_downloads.txt', 'w') as f:
        for d in failed_downloads:
            f.write(f"{d}\n")
    print(f"\nSaved {len(failed_downloads)} failed dates to failed_demand_downloads.txt")

if validation_failures:
    print(f"\nValidation failures (first 20):")
    for v in validation_failures[:20]:
        print(f"  Expected: {v['expected']}, Got: {v.get('actual', 'unknown')}")

print(f"\nClean demand files saved to: {DOWNLOAD_DIR}")
print(f"Old demand files backed up to: {BACKUP_DIR}")
