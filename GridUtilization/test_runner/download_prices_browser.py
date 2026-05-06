import asyncio
from playwright.async_api import async_playwright
import datetime
import os
import time

# Configuration
START_DATE = datetime.date(2020, 1, 1)
END_DATE = datetime.date(2025, 12, 31)
DOWNLOAD_DIR = os.path.join(os.getcwd(), "caiso_downloads")
OASIS_URL = "http://oasis.caiso.com/mrioasis/logon.do"

# Ensure download directory exists
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

async def download_prices():
    async with async_playwright() as p:
        # Launch browser (headless=True for GitHub Actions compatibility)
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(accept_downloads=True)
        page = await context.new_page()

        print("Navigating to CAISO OASIS...")
        try:
            await page.goto(OASIS_URL, timeout=60000)
        except Exception as e:
            print(f"Error loading OASIS home: {e}")
            
        print("\n" + "="*60)
        print("ACTION REQUIRED: Please manually navigate to:")
        print("Prices > Energy Prices > Hourly RTM LAP Prices")
        print("Scrip will check every 2 seconds...")
        print("="*60 + "\n")

        # Polling loop
        group_select = None
        for i in range(150): # Try for 5 minutes (150 * 2s)
            try:
                # Check for Group dropdown
                # Using a very loose selector to catch any dropdown
                # But filtering for ID starting with PFC_GroupType
                elements = await page.locator("select[id^='PFC_GroupType']").all()
                if elements:
                    if await elements[0].is_visible():
                        group_select = elements[0]
                        print("Report page detected! Taking over...")
                        break
            except Exception:
                pass
            
            print(f"Waiting for report... ({i*2}s)")
            await page.wait_for_timeout(2000)
            
        if not group_select:
             print("Timed out waiting for manual navigation.")
             await browser.close()
             return

        # Set Group to ALL_APNODES
        # group_select is already found
        
        # Check options
        try:
            options = await group_select.locator("option").all_inner_texts()
            target_option = "ALL_APNODES"
            if "ALL_APNODES" not in options and "ALL" in options:
                target_option = "ALL"
            
            # Select it
            await group_select.select_option(label=target_option)
            print(f"Script selected Group: {target_option}")
            await page.wait_for_timeout(1000) 
            
        except Exception as e:
             print(f"Script could not set Group to ALL. Please ensure it is selected manually! Error: {e}")

        # Locate Date Input
        # Robust selector: First visible text input
        date_input = page.locator("input[type='text']:visible").first 
        
        # Loop process - BACKWARDS from END_DATE
        current_date = END_DATE
        stop_date = START_DATE # Or just limit to 7 days as requested
        # Let's do the full range but backwards, user can stop it.
        
        while current_date >= stop_date:
            date_str = current_date.strftime("%m/%d/%Y")
            file_name = f"PRC_RTM_LAP_{current_date.strftime('%Y%m%d')}.zip"
            save_path = os.path.join(DOWNLOAD_DIR, file_name)
            
            if os.path.exists(save_path):
                # Check size - if < 2KB, likely error XML, so retry?
                if os.path.getsize(save_path) > 2000:
                    # print(f"Skipping {date_str}, already downloaded (valid size).")
                    current_date -= datetime.timedelta(days=1)
                    continue
                else:
                    print(f"Retrying {date_str} (existing file too small: {os.path.getsize(save_path)} bytes)")

            print(f"Processing {date_str}...")
            
            try:
                # RE-ASSERT GROUP: Ensure "ALL" is selected every time
                current_grp = await group_select.input_value()
                
                # Fill Date
                await date_input.click()
                await page.keyboard.press("Control+a")
                await page.keyboard.press("Backspace")
                await page.keyboard.type(date_str, delay=100)
                await page.keyboard.press("Tab")
                await page.wait_for_timeout(500)
                
                # Click Apply
                apply_btn = page.locator("#ApplyButton")
                if not await apply_btn.is_visible():
                     apply_btn = page.locator("text=Apply").first
                
                await apply_btn.click()
                print("  Clicked Apply...")
                
                # Wait for loading mask to disappear (robust)
                try:
                    await page.wait_for_selector(".ext-el-mask-msg", state="visible", timeout=1000)
                    await page.wait_for_selector(".ext-el-mask-msg", state="hidden", timeout=30000)
                except:
                    pass
                
                # Fixed wait
                await page.wait_for_timeout(3000) 
                
                # Initiate Download
                download_btn = page.locator("text=Download CSV")
                if not await download_btn.is_visible():
                     pass
                
                # Expect download (timeout 30s)
                async with page.expect_download(timeout=30000) as download_info:
                    await download_btn.click()

                download = await download_info.value
                await download.save_as(save_path)
                
                # Verify size
                if os.path.getsize(save_path) < 2000:
                     print(f"  Warning: Downloaded file is small ({os.path.getsize(save_path)} bytes). Likely error XML.")
                else:
                     print(f"  Saved: {file_name} ({os.path.getsize(save_path)} bytes)")
                
            except Exception as e:
                print(f"  Failed for {date_str}: {e}")
                # If fail, verify if it was "No Data Found"
                try:
                    if await page.get_by_text("No data found").is_visible():
                        print("    (Found 'No data found' message)")
                except:
                    pass
            
            current_date -= datetime.timedelta(days=1)
            
            # Rate limit polite wait
            await page.wait_for_timeout(2000)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(download_prices())
