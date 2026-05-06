"""
Test download for a single date to verify page structure.
"""
import os
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

DOWNLOAD_DIR = os.path.join(os.getcwd(), "test_demand_download")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Setup Chrome
chrome_options = Options()
chrome_options.add_experimental_option("prefs", {
    "download.default_directory": DOWNLOAD_DIR,
    "download.prompt_for_download": False,
})

driver = webdriver.Chrome(options=chrome_options)

try:
    url = "https://www.caiso.com/todays-outlook/demand"
    print(f"Navigating to {url}")
    driver.get(url)
    time.sleep(5)

    print(f"\nPage title: {driver.title}")
    print(f"Current URL: {driver.current_url}")

    # Save page source for inspection
    with open("page_source.html", "w", encoding="utf-8") as f:
        f.write(driver.page_source)
    print(f"Page source saved to page_source.html")

    # Try to find date-related elements
    print(f"\nSearching for date input elements...")

    # Method 1: Find all input elements
    inputs = driver.find_elements(By.TAG_NAME, "input")
    print(f"Found {len(inputs)} input elements:")
    for inp in inputs[:10]:  # Show first 10
        try:
            print(f"  Type: {inp.get_attribute('type')}, ID: {inp.get_attribute('id')}, Class: {inp.get_attribute('class')}")
        except:
            pass

    # Method 2: Find all buttons/links
    buttons = driver.find_elements(By.TAG_NAME, "button")
    links = driver.find_elements(By.TAG_NAME, "a")
    print(f"\nFound {len(buttons)} buttons and {len(links)} links")

    # Look for CSV/download related elements
    for link in links[:20]:
        try:
            text = link.text
            href = link.get_attribute('href')
            if 'csv' in text.lower() or 'csv' in (href or '').lower() or 'download' in text.lower():
                print(f"  Potential download link: {text} - {href}")
        except:
            pass

finally:
    input("\nPress Enter to close browser...")
    driver.quit()

print(f"\nTest complete. Check page_source.html for full page structure.")
