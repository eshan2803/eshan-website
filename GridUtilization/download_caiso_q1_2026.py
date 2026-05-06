"""
Download CAISO supply + renewables data for Q1 2026 via browser automation (Playwright).

Uses jQuery datepicker API to change dates (the only reliable method).

For each date:
1. Navigate to https://www.caiso.com/todays-outlook/supply
2. Set Supply date via jQuery datepicker, trigger change + Enter, download CSV
3. Set Renewables date via jQuery datepicker, check Show Demand, download CSV
"""
import asyncio
from playwright.async_api import async_playwright
import datetime
import os
from pathlib import Path
import time

DOWNLOAD_DIR = Path(__file__).parent / "caiso_downloads"
DOWNLOAD_DIR.mkdir(exist_ok=True)
FAILED_DATES_FILE = Path(__file__).parent / "failed_downloads_q1_2026.txt"
CAISO_SUPPLY_URL = "https://www.caiso.com/todays-outlook/supply"

START_DATE = datetime.date(2026, 1, 1)
END_DATE = datetime.date(2026, 3, 31)

TIMEOUT_MS = 60000


async def set_date(page, input_id, date_obj):
    """Set date using jQuery datepicker API and trigger chart reload."""
    date_str = date_obj.strftime("%#m/%#d/%Y")  # Windows: no leading zeros

    await page.evaluate(f"""() => {{
        jQuery("#{input_id}").datepicker("setDate", "{date_str}");
        jQuery("#{input_id}").trigger("change");
    }}""")

    # Press Enter on the input to trigger the chart reload
    await page.locator(f"#{input_id}").press("Enter")

    # Wait for chart to reload
    try:
        await page.wait_for_load_state("networkidle", timeout=15000)
    except:
        pass
    await page.wait_for_timeout(3000)


async def download_day(page, date):
    """Download supply and renewables data for a single date."""
    date_prefix = date.strftime("%Y%m%d")
    supply_file = DOWNLOAD_DIR / f"{date_prefix}_supply_raw.csv"
    renewables_file = DOWNLOAD_DIR / f"{date_prefix}_renewables_raw.csv"

    if supply_file.exists() and renewables_file.exists():
        return "skipped"

    print(f"  {date.strftime('%Y-%m-%d')}:", end=" ", flush=True)

    try:
        # Navigate fresh each time
        await page.goto(CAISO_SUPPLY_URL, wait_until="networkidle", timeout=TIMEOUT_MS)
        await page.wait_for_timeout(3000)

        # ── SUPPLY TREND ──
        if not supply_file.exists():
            await set_date(page, "dateSupply", date)

            # Verify date
            val = await page.locator("#dateSupply").input_value()
            target = date.strftime("%#m/%#d/%Y")
            if target not in val and date.strftime("%m/%d/%Y") not in val:
                print(f"supply date mismatch ({val})", end=" ", flush=True)

            # Download
            download_btn = page.locator("button:has-text('Download')").first
            await download_btn.click()
            await page.wait_for_timeout(1000)
            csv_link = page.locator("a:has-text('Chart data')").first

            async with page.expect_download(timeout=TIMEOUT_MS) as dl_info:
                await csv_link.click()
            dl = await dl_info.value
            await dl.save_as(supply_file)
            print("supply", end=" ", flush=True)

        # ── RENEWABLES TREND ──
        if not renewables_file.exists():
            # Scroll to renewables section
            await page.evaluate("window.scrollBy(0, 500)")
            await page.wait_for_timeout(500)

            await set_date(page, "dateRenewables", date)

            # Open Options dropdown (2nd Options button = renewables)
            options_btn = page.locator("button:has-text('Options')").nth(1)
            await options_btn.click()
            await page.wait_for_timeout(500)

            # Enable "Show Demand" checkbox
            show_demand = page.locator("#showDemand")
            if await show_demand.is_visible() and not await show_demand.is_checked():
                await show_demand.check()
                await page.wait_for_timeout(2000)
                print("demand", end=" ", flush=True)

            # Download (second Download button for renewables)
            download_btn = page.locator("button:has-text('Download')").nth(1)
            await download_btn.click()
            await page.wait_for_timeout(1000)
            csv_link = page.locator("a:has-text('Chart data')").nth(1)

            async with page.expect_download(timeout=TIMEOUT_MS) as dl_info:
                await csv_link.click()
            dl = await dl_info.value
            await dl.save_as(renewables_file)
            print("renewables", end=" ", flush=True)

        print("OK")
        return "success"

    except Exception as e:
        print(f"ERROR: {str(e)[:100]}")
        return "failed"


async def main():
    print("=" * 70)
    print(f"CAISO Supply Browser Download: Q1 2026")
    print(f"Date range: {START_DATE} to {END_DATE}")
    print(f"Output: {DOWNLOAD_DIR}")
    print("=" * 70)

    dates = []
    current = START_DATE
    while current <= END_DATE:
        dates.append(current)
        current += datetime.timedelta(days=1)

    print(f"Total dates: {len(dates)}\n")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(accept_downloads=True)
        page = await context.new_page()

        success = 0
        failed = 0
        skipped = 0
        failed_dates = []
        start_time = time.time()

        try:
            for i, date in enumerate(dates, 1):
                # Restart browser every 30 downloads to prevent memory issues
                if i > 1 and (i - 1) % 30 == 0:
                    print(f"\n  [Restarting browser at {i}/{len(dates)}...]")
                    await browser.close()
                    browser = await p.chromium.launch(headless=False)
                    context = await browser.new_context(accept_downloads=True)
                    page = await context.new_page()

                result = await download_day(page, date)

                if result == "success":
                    success += 1
                elif result == "skipped":
                    skipped += 1
                elif result == "failed":
                    failed += 1
                    failed_dates.append(date.strftime('%Y-%m-%d'))

                # Progress every 15 dates
                if i % 15 == 0:
                    elapsed = time.time() - start_time
                    done = success + skipped
                    rate = done / max(elapsed, 1)
                    remaining = (len(dates) - i) / max(rate, 0.01)
                    print(f"  [{i}/{len(dates)}] OK:{success} Skip:{skipped} Fail:{failed} ETA:{remaining/60:.1f}min")

                await page.wait_for_timeout(1000)

        finally:
            await browser.close()

        elapsed = time.time() - start_time
        print(f"\n{'=' * 70}")
        print(f"Complete in {elapsed/60:.1f} minutes")
        print(f"  Success: {success}, Skipped: {skipped}, Failed: {failed}")

        if failed_dates:
            with open(FAILED_DATES_FILE, 'w') as f:
                f.write('\n'.join(failed_dates))
            print(f"  Failed dates saved to: {FAILED_DATES_FILE}")


if __name__ == "__main__":
    asyncio.run(main())
