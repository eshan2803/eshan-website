"""
Download CAISO supply data using browser automation (Playwright).

Automates the manual process:
1. Navigate to https://www.caiso.com/todays-outlook/supply
2. For each date in dates_to_download.txt:
   - Supply trend: select date, download Chart Data (CSV)
   - Renewables trend: select date, enable "Show Demand", download Chart Data (CSV)

Requirements:
    pip install playwright
    playwright install chromium

Improvements:
- Retry logic with exponential backoff
- Periodic browser restarts to prevent memory issues
- Longer timeouts for slow connections
- Saves list of failed dates for manual review
"""
import asyncio
from playwright.async_api import async_playwright
import datetime
import os
from pathlib import Path
import time

# Input file with dates to download (check for temp file first, then regular file)
TEMP_DATES_FILE = Path(__file__).parent / "temp_supply_dates.txt"
DATES_FILE = Path(__file__).parent / "dates_to_download.txt"

# Output directory
DOWNLOAD_DIR = Path(__file__).parent / "caiso_downloads"
DOWNLOAD_DIR.mkdir(exist_ok=True)

# Failed dates log
FAILED_DATES_FILE = Path(__file__).parent / "failed_downloads.txt"

# URL
CAISO_SUPPLY_URL = "https://www.caiso.com/todays-outlook/supply"

# Configuration
MAX_RETRIES = 3
TIMEOUT_MS = 60000  # 60 seconds (increased from 30)
RESTART_BROWSER_EVERY = 50  # Restart browser every N downloads to prevent memory issues


async def download_day(page, date, retry_count=0):
    """Download supply and renewables data for a single date with retry logic."""
    date_str_windows = date.strftime("%#m/%#d/%Y")  # Windows format: 1/1/2020 (no leading zeros)
    date_prefix = date.strftime("%Y%m%d")

    if retry_count == 0:
        print(f"\nProcessing {date.strftime('%Y-%m-%d')}...")
    else:
        print(f"  Retry {retry_count}/{MAX_RETRIES}...")

    try:
        # Navigate to the page with longer timeout
        await page.goto(CAISO_SUPPLY_URL, wait_until="networkidle", timeout=TIMEOUT_MS)
        await page.wait_for_timeout(2000)

        # ====================
        # SUPPLY TREND CHART
        # ====================
        print("  Downloading Supply trend...")

        # Find the Supply date input by ID (found via inspector: dateSupply)
        supply_date_input = page.locator("#dateSupply")

        # Wait for the date input to be visible and ready
        await supply_date_input.wait_for(state="visible", timeout=TIMEOUT_MS)
        await page.wait_for_timeout(500)

        # Clear and enter the date with multiple approaches
        await supply_date_input.click()
        await page.wait_for_timeout(300)

        # Select all and delete to clear
        await page.keyboard.press("Control+A")
        await page.keyboard.press("Backspace")
        await page.wait_for_timeout(300)

        # Type the date
        await supply_date_input.type(date_str_windows, delay=50)
        await page.wait_for_timeout(500)

        print(f"    Set date to: {date_str_windows}")

        # Press Enter to trigger the date change and chart reload
        await page.keyboard.press("Enter")
        await page.wait_for_timeout(1000)

        # Wait for the chart to reload with the new date's data
        # Wait for network to be idle (chart data loading)
        await page.wait_for_load_state("networkidle", timeout=TIMEOUT_MS)
        await page.wait_for_timeout(2000)  # Additional buffer for chart rendering

        # Find the first Download button
        download_btn = page.locator("button:has-text('Download')").first
        await download_btn.click()
        await page.wait_for_timeout(1000)

        # Click "Chart data" link in the dropdown menu
        csv_link = page.locator("a:has-text('Chart data')").first

        # Handle download with longer timeout
        supply_file = DOWNLOAD_DIR / f"{date_prefix}_supply_raw.csv"
        async with page.expect_download(timeout=TIMEOUT_MS) as download_info:
            await csv_link.click()

        download = await download_info.value
        await download.save_as(supply_file)

        print(f"  OK Supply trend saved: {supply_file.name}")

        # ====================
        # RENEWABLES TREND CHART
        # ====================
        print("  Downloading Renewables trend...")

        # Scroll down to ensure Renewables chart is visible
        await page.evaluate("window.scrollBy(0, 500)")
        await page.wait_for_timeout(500)

        # Find the Renewables date input by ID (found via inspector: dateRenewables)
        renewables_date_input = page.locator("#dateRenewables")

        # Wait for the date input to be visible and ready
        await renewables_date_input.wait_for(state="visible", timeout=TIMEOUT_MS)
        await page.wait_for_timeout(500)

        # Clear and enter the date with multiple approaches
        await renewables_date_input.click()
        await page.wait_for_timeout(300)

        # Select all and delete to clear
        await page.keyboard.press("Control+A")
        await page.keyboard.press("Backspace")
        await page.wait_for_timeout(300)

        # Type the date
        await renewables_date_input.type(date_str_windows, delay=50)
        await page.wait_for_timeout(500)

        print(f"    Set date to: {date_str_windows}")

        # Press Enter to trigger the date change and chart reload
        await page.keyboard.press("Enter")
        await page.wait_for_timeout(1000)

        # Wait for the chart to reload with the new date's data
        await page.wait_for_load_state("networkidle", timeout=TIMEOUT_MS)
        await page.wait_for_timeout(2000)  # Additional buffer for chart rendering

        # Enable "Show Demand" checkbox
        # Look for checkbox with label containing "Show Demand"
        try:
            # Try to find checkbox by nearby text
            show_demand = page.locator('text="Show Demand" >> .. >> input[type="checkbox"]').first
            if not await show_demand.is_checked():
                await show_demand.check()
                await page.wait_for_timeout(500)
                print("      Enabled 'Show Demand' option")
        except Exception as e:
            print(f"      Warning: Could not find 'Show Demand' checkbox: {str(e)[:80]}")
            # Continue anyway - chart might work without it

        # Find the second Download button (for Renewables)
        download_btn2 = page.locator("button:has-text('Download')").nth(1)
        await download_btn2.click()
        await page.wait_for_timeout(1000)

        # Click second "Chart data" link
        csv_link2 = page.locator("a:has-text('Chart data')").nth(1)

        # Handle download with longer timeout
        renewables_file = DOWNLOAD_DIR / f"{date_prefix}_renewables_raw.csv"
        async with page.expect_download(timeout=TIMEOUT_MS) as download_info2:
            await csv_link2.click()

        download2 = await download_info2.value
        await download2.save_as(renewables_file)

        print(f"  OK Renewables trend saved: {renewables_file.name}")

        return True

    except Exception as e:
        error_msg = str(e)[:150]
        print(f"  ERROR: {error_msg}")

        # Retry with exponential backoff
        if retry_count < MAX_RETRIES:
            wait_time = (2 ** retry_count) * 2  # 2, 4, 8 seconds
            print(f"  Waiting {wait_time}s before retry...")
            await page.wait_for_timeout(wait_time * 1000)
            return await download_day(page, date, retry_count + 1)
        else:
            print(f"  FAILED after {MAX_RETRIES} retries")
            return False


async def main():
    print("=" * 80)
    print("CAISO Supply Data Browser Download (Playwright)")
    print("=" * 80)

    # Read dates from file (check temp file first, then regular file)
    dates_file = None
    if TEMP_DATES_FILE.exists():
        dates_file = TEMP_DATES_FILE
        print(f"Using temp dates file: {TEMP_DATES_FILE.name}")
    elif DATES_FILE.exists():
        dates_file = DATES_FILE
        print(f"Using dates file: {DATES_FILE.name}")
    else:
        print(f"ERROR: No dates file found!")
        print(f"Expected: {TEMP_DATES_FILE.name} or {DATES_FILE.name}")
        return

    with open(dates_file, 'r') as f:
        date_strings = [line.strip() for line in f if line.strip()]

    dates_to_download = [datetime.datetime.strptime(d, "%Y-%m-%d").date() for d in date_strings]

    print(f"Dates to download: {len(dates_to_download)} days")
    print(f"Output directory: {DOWNLOAD_DIR}")
    print(f"Date range: {dates_to_download[0]} to {dates_to_download[-1]}")
    print(f"Timeouts: {TIMEOUT_MS/1000}s, Max retries: {MAX_RETRIES}")
    print(f"Browser restart: every {RESTART_BROWSER_EVERY} downloads")
    print()

    async with async_playwright() as p:
        browser = None
        context = None
        page = None

        total_days = len(dates_to_download)
        success_count = 0
        error_count = 0
        skipped_count = 0
        failed_dates = []
        start_time = time.time()

        try:
            for day_num, current_date in enumerate(dates_to_download, 1):
                # Periodic browser restart to prevent memory issues
                if (day_num - skipped_count - 1) % RESTART_BROWSER_EVERY == 0 or browser is None:
                    if browser is not None:
                        print(f"\n[Restarting browser after {RESTART_BROWSER_EVERY} downloads...]")
                        await browser.close()

                    print("Launching browser...")
                    browser = await p.chromium.launch(headless=False)
                    context = await browser.new_context(accept_downloads=True)
                    page = await context.new_page()

                # Check if files already exist
                date_prefix = current_date.strftime("%Y%m%d")
                supply_file = DOWNLOAD_DIR / f"{date_prefix}_supply_raw.csv"
                renewables_file = DOWNLOAD_DIR / f"{date_prefix}_renewables_raw.csv"

                if supply_file.exists() and renewables_file.exists():
                    if day_num % 50 == 0:
                        elapsed = time.time() - start_time
                        rate = (success_count + skipped_count) / elapsed if elapsed > 0 else 0
                        remaining = (total_days - day_num) / rate if rate > 0 else 0
                        print(f"[{day_num}/{total_days}] {current_date.strftime('%Y-%m-%d')}: already downloaded | Progress: {day_num/total_days*100:.1f}% | ETA: {remaining/60:.1f} min")
                    skipped_count += 1
                    continue

                print(f"[{day_num}/{total_days}] {current_date.strftime('%Y-%m-%d')}:")

                success = await download_day(page, current_date)
                if success:
                    success_count += 1
                else:
                    error_count += 1
                    failed_dates.append(current_date.strftime('%Y-%m-%d'))

                # Progress report every 25 dates
                if day_num % 25 == 0:
                    elapsed = time.time() - start_time
                    rate = (success_count + skipped_count) / elapsed if elapsed > 0 else 0
                    remaining = (total_days - day_num) / rate if rate > 0 else 0
                    print(f"\n*** Progress: {day_num}/{total_days} ({day_num/total_days*100:.1f}%) | Success: {success_count} | Errors: {error_count} | ETA: {remaining/60:.1f} min ***\n")

                # Polite delay between downloads
                await page.wait_for_timeout(2000)

            # Summary
            elapsed = time.time() - start_time
            print("\n" + "=" * 80)
            print("Download complete!")
            print(f"  Total time: {elapsed/60:.1f} minutes")
            print(f"  Success: {success_count} days")
            print(f"  Skipped: {skipped_count} days (already exist)")
            print(f"  Errors: {error_count} days")
            print(f"  Files in {DOWNLOAD_DIR}: {len(list(DOWNLOAD_DIR.glob('*.csv')))}")

            # Save failed dates
            if failed_dates:
                with open(FAILED_DATES_FILE, 'w') as f:
                    f.write('\n'.join(failed_dates))
                print(f"\n  Failed dates saved to: {FAILED_DATES_FILE}")
                print(f"  You can manually review these {len(failed_dates)} dates")

        finally:
            if browser:
                await browser.close()
                print("\nBrowser closed.")


if __name__ == "__main__":
    asyncio.run(main())
