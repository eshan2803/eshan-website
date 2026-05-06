"""
Re-download ALL demand files in parallel with validation.
7 Chrome instances (one per year: 2020-2026) for faster download.
"""
import os
import time
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import multiprocessing

# Configuration
DOWNLOAD_DIR = Path(__file__).parent / "caiso_demand_clean"
OLD_DEMAND_DIR = Path(__file__).parent / "caiso_demand_downloads"
BACKUP_DIR = Path(__file__).parent / "caiso_demand_downloads_old_backup"

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

def validate_and_rename(expected_date, latest_file):
    """Validate downloaded file and rename to correct format."""
    # Wait for file lock to release
    time.sleep(2)

    try:
        # Read and validate cell A1
        with open(latest_file, 'r', encoding='utf-8-sig') as f:
            first_line = f.readline().strip()

        if 'Demand' in first_line:
            parts = first_line.replace(',', ' ').split()
            if len(parts) >= 2:
                actual_date_str = parts[1]  # MM/DD/YYYY format
                actual_date = datetime.strptime(actual_date_str, '%m/%d/%Y').date()

                expected_date_str = expected_date.strftime('%Y%m%d')

                if actual_date == expected_date:
                    # Valid! Rename to correct format
                    correct_name = DOWNLOAD_DIR / f"{expected_date_str}_demand.csv"

                    if correct_name.exists():
                        time.sleep(1)
                        correct_name.unlink()

                    # Retry rename with backoff
                    for retry in range(5):
                        try:
                            time.sleep(1)
                            latest_file.rename(correct_name)
                            return True, f"Valid - {actual_date_str}"
                        except (PermissionError, OSError):
                            if retry < 4:
                                time.sleep(1)
                            else:
                                raise
                else:
                    # Date mismatch - delete file
                    time.sleep(1)
                    latest_file.unlink()
                    return False, f"Date mismatch: expected {expected_date}, got {actual_date}"
            else:
                time.sleep(1)
                latest_file.unlink()
                return False, f"Cannot parse date from: {first_line}"
        else:
            time.sleep(1)
            latest_file.unlink()
            return False, f"Invalid file format: {first_line[:50]}"
    except Exception as e:
        if latest_file.exists():
            time.sleep(1)
            try:
                latest_file.unlink()
            except:
                pass
        return False, f"Validation error: {e}"

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
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=chrome_options)

    success = 0
    validation_failures = 0
    download_failures = 0

    try:
        current_date = start_date

        while current_date <= end_date:
            date_str = f"{current_date.month}/{current_date.day}/{current_date.year}"
            date_key = current_date.strftime('%Y%m%d')

            try:
                driver.get("https://www.caiso.com/todays-outlook/demand")
                time.sleep(3)

                # Find date input
                date_inputs = driver.find_elements(By.XPATH, "//input[@type='text' or @type='date']")
                if not date_inputs:
                    print(f"[W{worker_id}] {date_key}: ERROR - No date input")
                    download_failures += 1
                    current_date += timedelta(days=1)
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
                    print(f"[W{worker_id}] {date_key}: ERROR - No download button")
                    download_failures += 1
                    current_date += timedelta(days=1)
                    continue

                download_buttons[0].click()
                time.sleep(2)

                # Find CSV option
                csv_options = driver.find_elements(By.XPATH, "//*[contains(text(), 'Chart') and contains(text(), 'CSV')]")
                if not csv_options:
                    print(f"[W{worker_id}] {date_key}: ERROR - No CSV option")
                    download_failures += 1
                    current_date += timedelta(days=1)
                    continue

                csv_options[0].click()

                # Wait for download
                if wait_for_download(timeout=30):
                    # Find the downloaded file
                    csv_files = list(DOWNLOAD_DIR.glob("*.csv"))
                    if csv_files:
                        latest = max(csv_files, key=lambda p: p.stat().st_mtime)

                        # Validate and rename
                        valid, message = validate_and_rename(current_date, latest)

                        if valid:
                            success += 1
                            print(f"[W{worker_id}] {date_key}: OK - {message} ({success}/{success+validation_failures+download_failures})")
                        else:
                            validation_failures += 1
                            print(f"[W{worker_id}] {date_key}: VALIDATION FAILED - {message}")
                    else:
                        download_failures += 1
                        print(f"[W{worker_id}] {date_key}: ERROR - No file found")
                else:
                    download_failures += 1
                    print(f"[W{worker_id}] {date_key}: TIMEOUT")

            except Exception as e:
                download_failures += 1
                print(f"[W{worker_id}] {date_key}: ERROR - {e}")

            current_date += timedelta(days=1)
            time.sleep(1)

        print(f"\n[Worker {worker_id}] COMPLETE: {success} OK, {validation_failures} validation failed, {download_failures} download failed")

    finally:
        driver.quit()

def main():
    """Main parallel download coordinator."""
    # Create clean download directory
    DOWNLOAD_DIR.mkdir(exist_ok=True)

    # Backup old directory
    if OLD_DEMAND_DIR.exists():
        print(f"Backing up old demand directory...")
        if BACKUP_DIR.exists():
            shutil.rmtree(BACKUP_DIR)
        shutil.move(str(OLD_DEMAND_DIR), str(BACKUP_DIR))
        print(f"Backup complete: {BACKUP_DIR}")

    # Define year ranges
    year_ranges = [
        (2020, 1, 1, 2020, 12, 31, 1),  # 2020
        (2021, 1, 1, 2021, 12, 31, 2),  # 2021
        (2022, 1, 1, 2022, 12, 31, 3),  # 2022
        (2023, 1, 1, 2023, 12, 31, 4),  # 2023
        (2024, 1, 1, 2024, 12, 31, 5),  # 2024
        (2025, 1, 1, 2025, 12, 31, 6),  # 2025
        (2026, 1, 1, 2026, 4, 1, 7),    # 2026 (partial)
    ]

    print("=" * 80)
    print("PARALLEL DEMAND FILE DOWNLOAD WITH VALIDATION")
    print("=" * 80)
    print(f"Workers: {len(year_ranges)} (one per year)")
    print(f"Download to: {DOWNLOAD_DIR}")
    print("=" * 80)

    workers = []
    for y_start, m_start, d_start, y_end, m_end, d_end, worker_id in year_ranges:
        worker_start = datetime(y_start, m_start, d_start).date()
        worker_end = datetime(y_end, m_end, d_end).date()

        days_count = (worker_end - worker_start).days + 1
        print(f"Worker {worker_id}: {worker_start} to {worker_end} ({days_count} days)")

        p = multiprocessing.Process(
            target=download_worker,
            args=(worker_start, worker_end, worker_id)
        )
        p.start()
        workers.append(p)
        time.sleep(2)  # Stagger startup

    print("\nAll workers started. Downloading in parallel...")
    print("=" * 80)

    # Wait for all workers
    for p in workers:
        p.join()

    # Final report
    final_files = list(DOWNLOAD_DIR.glob("*_demand.csv"))
    print("\n" + "=" * 80)
    print("DOWNLOAD COMPLETE")
    print("=" * 80)
    print(f"Total validated files: {len(final_files)}")
    print(f"Files saved to: {DOWNLOAD_DIR}")
    print("=" * 80)

if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
