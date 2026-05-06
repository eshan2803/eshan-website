"""Test if date changing works correctly on CAISO website"""
import asyncio
from playwright.async_api import async_playwright
from pathlib import Path

async def test_date_change():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(accept_downloads=True)
        page = await context.new_page()
        
        # Navigate to CAISO
        await page.goto("https://www.caiso.com/todays-outlook/supply", wait_until="networkidle")
        await page.wait_for_timeout(2000)
        
        # Change Supply date to 2020-06-15
        test_date = "6/15/2020"
        print(f"Changing date to {test_date}...")
        
        supply_date_input = page.locator("#dateSupply")
        await supply_date_input.click()
        await supply_date_input.fill("")
        await supply_date_input.fill(test_date)
        await page.keyboard.press("Enter")
        
        # Wait for chart to reload
        await page.wait_for_load_state("networkidle", timeout=60000)
        await page.wait_for_timeout(3000)
        
        print("Downloading to test...")
        download_dir = Path("test_download")
        download_dir.mkdir(exist_ok=True)
        
        # Download
        download_btn = page.locator("button:has-text('Download')").first
        await download_btn.click()
        await page.wait_for_timeout(1000)
        
        csv_link = page.locator("a:has-text('Chart data')").first
        
        async with page.expect_download(timeout=60000) as download_info:
            await csv_link.click()
        
        download = await download_info.value
        test_file = download_dir / "test_supply.csv"
        await download.save_as(test_file)
        
        print(f"Downloaded to {test_file}")
        
        # Check the file header
        with open(test_file, 'r') as f:
            first_line = f.readline()
            print(f"File header: {first_line[:60]}...")
            
            if "06/15/2020" in first_line or "6/15/2020" in first_line:
                print("SUCCESS: Date change worked!")
            else:
                print("FAILED: Still showing wrong date")
        
        await browser.close()

asyncio.run(test_date_change())
