"""
Test script to download CAISO data for a single date.
This helps verify the automation is working before running the full batch.
"""
import asyncio
from playwright.async_api import async_playwright
import datetime
from pathlib import Path

# Test with a single date from 2020
TEST_DATE = datetime.date(2020, 1, 1)

# Output directory
DOWNLOAD_DIR = Path(__file__).parent / "caiso_downloads"
DOWNLOAD_DIR.mkdir(exist_ok=True)

# URL
CAISO_SUPPLY_URL = "https://www.caiso.com/todays-outlook/supply"


async def download_day(page, date):
    """Download supply and renewables data for a single date."""
    date_str_windows = date.strftime("%#m/%#d/%Y")  # Windows format: 1/1/2020
    date_prefix = date.strftime("%Y%m%d")

    print(f"\nProcessing {date.strftime('%Y-%m-%d')}...")

    try:
        # Navigate to the page
        print("  Navigating to page...")
        await page.goto(CAISO_SUPPLY_URL, wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(2000)

        # ====================
        # SUPPLY TREND CHART
        # ====================
        print("  Downloading Supply trend...")

        # Find the Supply date input by ID
        supply_date_input = page.locator("#dateSupply")

        # Clear and enter the date
        print(f"    Filling date: {date_str_windows}")
        await supply_date_input.click()
        await page.keyboard.press("Control+a")
        await supply_date_input.fill(date_str_windows)
        await page.keyboard.press("Tab")
        await page.wait_for_timeout(1500)

        # Find the first Download button
        print("    Clicking Download button...")
        download_btn = page.locator("button:has-text('Download')").first
        await download_btn.click()
        await page.wait_for_timeout(1000)

        # Click "Chart data" link in the dropdown menu
        print("    Clicking 'Chart data' link...")
        csv_link = page.locator("a:has-text('Chart data')").first

        # Handle download
        supply_file = DOWNLOAD_DIR / f"{date_prefix}_supply_raw.csv"
        async with page.expect_download(timeout=30000) as download_info:
            await csv_link.click()

        download = await download_info.value
        await download.save_as(supply_file)

        print(f"  OK Supply trend saved: {supply_file.name} ({supply_file.stat().st_size} bytes)")

        # ====================
        # RENEWABLES TREND CHART
        # ====================
        print("  Downloading Renewables trend...")

        # Scroll down to ensure Renewables chart is visible
        await page.evaluate("window.scrollBy(0, 500)")
        await page.wait_for_timeout(500)

        # Find the Renewables date input by ID
        renewables_date_input = page.locator("#dateRenewables")

        # Clear and enter the date
        print(f"    Filling date: {date_str_windows}")
        await renewables_date_input.click()
        await page.keyboard.press("Control+a")
        await renewables_date_input.fill(date_str_windows)
        await page.keyboard.press("Tab")
        await page.wait_for_timeout(1500)

        # Enable "Show Demand" checkbox (if not already checked)
        # We need to find the checkbox - let's try a more specific approach
        print("    Checking 'Show Demand' option...")
        try:
            # Find all checkboxes and check the one near Renewables section
            checkboxes = await page.locator("input[type='checkbox']").all()
            for checkbox in checkboxes:
                # Try to find if this checkbox is near "Show Demand" text
                parent = checkbox.locator("xpath=..")
                parent_text = await parent.inner_text() if await parent.count() > 0 else ""
                if "demand" in parent_text.lower():
                    if not await checkbox.is_checked():
                        await checkbox.check()
                        print("      Checked 'Show Demand'")
                    break
        except Exception as e:
            print(f"      Warning: Could not find 'Show Demand' checkbox: {str(e)[:80]}")

        await page.wait_for_timeout(1000)

        # Find the second Download button (for Renewables)
        print("    Clicking Download button...")
        download_btn2 = page.locator("button:has-text('Download')").nth(1)
        await download_btn2.click()
        await page.wait_for_timeout(1000)

        # Click second "Chart data" link
        print("    Clicking 'Chart data' link...")
        csv_link2 = page.locator("a:has-text('Chart data')").nth(1)

        # Handle download
        renewables_file = DOWNLOAD_DIR / f"{date_prefix}_renewables_raw.csv"
        async with page.expect_download(timeout=30000) as download_info2:
            await csv_link2.click()

        download2 = await download_info2.value
        await download2.save_as(renewables_file)

        print(f"  OK Renewables trend saved: {renewables_file.name} ({renewables_file.stat().st_size} bytes)")

        return True

    except Exception as e:
        print(f"  ERROR: {str(e)[:200]}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    print("=" * 80)
    print("CAISO Single Date Download Test")
    print("=" * 80)
    print(f"Test date: {TEST_DATE}")
    print(f"Output directory: {DOWNLOAD_DIR}")
    print()

    async with async_playwright() as p:
        # Launch browser (visible so you can see what's happening)
        print("Launching browser...")
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(accept_downloads=True)
        page = await context.new_page()

        try:
            success = await download_day(page, TEST_DATE)

            print("\n" + "=" * 80)
            if success:
                print("SUCCESS! Downloaded both files.")
                print("\nNext steps:")
                print("  1. Check the files in caiso_downloads/")
                print("  2. If they look correct, run: python download_caiso_supply_browser.py")
            else:
                print("FAILED! Check the error messages above.")
                print("You may need to adjust selectors in the script.")

        finally:
            print("\nClosing browser in 5 seconds...")
            await page.wait_for_timeout(5000)
            await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
