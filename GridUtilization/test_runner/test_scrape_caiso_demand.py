"""
Test scraping demand data from CAISO Today's Outlook and compare to renewables CSV.
"""
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import time
import csv
import io

# Test date
test_date = "01/15/2026"  # Format: MM/DD/YYYY
csv_file = "caiso_downloads/20260115_renewables_raw.csv"

print(f"Testing demand scrape for {test_date}")
print("=" * 60)

# Setup Chrome in headless mode
options = webdriver.ChromeOptions()
# options.add_argument('--headless')  # Comment out to see browser
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--disable-gpu')
options.add_argument('--window-size=1920,1080')

driver = webdriver.Chrome(options=options)

try:
    # Navigate to the page
    url = "https://www.caiso.com/todays-outlook/demand"
    print(f"Loading {url}...")
    driver.get(url)

    # Wait for page to load
    time.sleep(5)

    # Find and click on "Demand Trend" chart tab
    print("Looking for Demand Trend chart...")
    try:
        # Try different possible selectors
        demand_tab = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Demand Trend')]"))
        )
        demand_tab.click()
        print("Clicked on Demand Trend tab")
        time.sleep(2)
    except Exception as e:
        print(f"Could not find Demand Trend tab: {e}")
        print("Available tabs:")
        tabs = driver.find_elements(By.TAG_NAME, "button")
        for tab in tabs:
            print(f"  - {tab.text}")

    # Find date input field
    print(f"Entering date {test_date}...")
    try:
        date_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//input[@type='date' or @type='text']"))
        )
        date_input.clear()
        date_input.send_keys(test_date)
        date_input.send_keys(Keys.RETURN)
        print("Date entered and submitted")
        time.sleep(5)
    except Exception as e:
        print(f"Could not find or interact with date input: {e}")

    # Find download button
    print("Looking for Download button...")
    try:
        # Try to find download button
        download_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'Download')]"))
        )
        download_btn.click()
        print("Clicked Download button")
        time.sleep(2)

        # Look for "Chart Data (CSV)" option
        csv_option = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'Chart Data') and contains(text(), 'CSV')]"))
        )
        csv_option.click()
        print("Clicked Chart Data (CSV) option")
        time.sleep(3)

    except Exception as e:
        print(f"Could not find download options: {e}")

    # Take screenshot for debugging
    screenshot_path = "caiso_demand_screenshot.png"
    driver.save_screenshot(screenshot_path)
    print(f"Screenshot saved to {screenshot_path}")

    # Print page source snippet
    page_text = driver.find_element(By.TAG_NAME, "body").text
    print("\nPage text (first 500 chars):")
    print(page_text[:500])

finally:
    driver.quit()

print("\n" + "=" * 60)
print("Scraping test complete. Check if CSV was downloaded.")

# Compare with renewables CSV if it exists
print("\nComparing with renewables CSV demand...")
try:
    with open(csv_file) as f:
        for line in f:
            if line.startswith('Demand,'):
                csv_demand = [float(x) for x in line.strip().split(',')[1:-1]]
                print(f"Renewables CSV has {len(csv_demand)} 5-minute demand values")
                print(f"First 10 values: {csv_demand[:10]}")
                print(f"Average: {sum(csv_demand)/len(csv_demand):.0f} MW")
                break
except FileNotFoundError:
    print(f"File {csv_file} not found")
