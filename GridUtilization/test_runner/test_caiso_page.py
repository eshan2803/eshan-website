"""
Test script to inspect the CAISO Today's Outlook page and identify selectors.

This script opens the page and pauses so you can:
1. Inspect the page structure using browser dev tools (F12)
2. Identify the correct selectors for date inputs, buttons, and checkboxes
3. Test interaction manually

The script will print out what it finds and wait for your inspection.
"""
import asyncio
from playwright.async_api import async_playwright
import datetime


async def inspect_page():
    print("=" * 80)
    print("CAISO Page Inspector")
    print("=" * 80)
    print("\nThis script will open the CAISO Today's Outlook page and help you")
    print("identify the correct selectors for automation.\n")

    async with async_playwright() as p:
        # Launch browser (visible)
        print("Launching browser...")
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(accept_downloads=True)
        page = await context.new_page()

        try:
            # Navigate to the page
            print("Navigating to https://www.caiso.com/todays-outlook/supply...")
            await page.goto("https://www.caiso.com/todays-outlook/supply",
                          wait_until="networkidle", timeout=30000)

            print("OK - Page loaded!\n")
            await page.wait_for_timeout(2000)

            # Try to find date inputs
            print("Looking for date input fields...")
            date_inputs = await page.locator("input[type='text']").all()
            print(f"  Found {len(date_inputs)} text input fields")

            for i, input_elem in enumerate(date_inputs):
                try:
                    placeholder = await input_elem.get_attribute("placeholder") or ""
                    id_attr = await input_elem.get_attribute("id") or ""
                    name_attr = await input_elem.get_attribute("name") or ""
                    is_visible = await input_elem.is_visible()

                    if is_visible:
                        print(f"    Input {i}: id='{id_attr}', name='{name_attr}', placeholder='{placeholder}'")
                except:
                    pass

            # Look for Download buttons
            print("\nLooking for Download buttons...")
            download_btns = await page.locator("button, a").filter(has_text="Download").all()
            print(f"  Found {len(download_btns)} elements with 'Download' text")

            for i, btn in enumerate(download_btns):
                try:
                    tag = await btn.evaluate("el => el.tagName")
                    text = await btn.text_content()
                    is_visible = await btn.is_visible()

                    if is_visible:
                        print(f"    Button {i}: <{tag}> text='{text[:50]}'")
                except:
                    pass

            # Look for checkboxes
            print("\nLooking for checkboxes (for 'Show Demand')...")
            checkboxes = await page.locator("input[type='checkbox']").all()
            print(f"  Found {len(checkboxes)} checkboxes")

            for i, checkbox in enumerate(checkboxes):
                try:
                    id_attr = await checkbox.get_attribute("id") or ""
                    label_elem = await page.locator(f"label[for='{id_attr}']").first.text_content() if id_attr else ""
                    is_visible = await checkbox.is_visible()

                    if is_visible:
                        print(f"    Checkbox {i}: id='{id_attr}', label='{label_elem}'")
                except:
                    pass

            # Try to identify chart containers
            print("\nLooking for chart containers...")

            # Common patterns for chart divs
            possible_selectors = [
                "#supply-chart",
                "#renewables-chart",
                ".chart-container",
                "[id*='chart']",
                "[class*='chart']"
            ]

            for selector in possible_selectors:
                try:
                    elements = await page.locator(selector).all()
                    if elements:
                        print(f"  Found {len(elements)} elements matching: {selector}")
                except:
                    pass

            # Now pause for manual inspection
            print("\n" + "=" * 80)
            print("BROWSER IS OPEN - You can now:")
            print("  1. Press F12 to open DevTools")
            print("  2. Use the element picker to inspect date inputs")
            print("  3. Look for the Download buttons and their structure")
            print("  4. Check the 'Show Demand' checkbox location")
            print("\nPress Enter in this terminal when you're done inspecting...")
            print("=" * 80)

            # Wait for user input
            await asyncio.get_event_loop().run_in_executor(None, input)

            # Try a test interaction
            print("\nAttempting test interaction with first date input...")
            test_date = "1/1/2020"

            try:
                first_input = page.locator("input[type='text']").first
                await first_input.click()
                await first_input.fill(test_date)
                print(f"  OK - Successfully filled date: {test_date}")
                await page.wait_for_timeout(2000)
            except Exception as e:
                print(f"  ERROR - Failed: {str(e)[:100]}")

            print("\nPress Enter to close browser...")
            await asyncio.get_event_loop().run_in_executor(None, input)

        finally:
            await browser.close()
            print("\nBrowser closed.")


if __name__ == "__main__":
    asyncio.run(inspect_page())
