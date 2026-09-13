#!/usr/bin/env python
"""Demo autofill on ProofServe real job."""

import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup

print("🚀 ProofServe Autofill Demo")
print("=" * 60)

options = Options()
driver = webdriver.Chrome(options=options)

try:
    # Navigate to ProofServe job
    url = "https://www.proofserve.com/careers/4716759005"
    print(f"🌐 Opening: {url}")
    driver.get(url)

    # Wait for page
    time.sleep(3)

    # Scroll down to find form
    print("📍 Scrolling to find form...")
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(2)

    # Parse HTML
    soup = BeautifulSoup(driver.page_source, "html.parser")
    forms = soup.find_all("form")

    print(f"\n📋 Forms found: {len(forms)}")

    if forms:
        form = forms[0]
        fields = form.find_all(["input", "textarea", "select"])
        print(f"✓ Fields in first form: {len(fields)}")

        for i, field in enumerate(fields[:10], 1):
            name = field.get("name", "unnamed")
            field_type = field.get("type", field.name)
            label = field.get("placeholder", "")
            print(f"  {i}. {name} ({field_type}) - {label}")
    else:
        print("❌ No forms found on page after scroll")
        print("\nTrying to find and click 'Apply' button...")

        # Look for apply button
        page_text = soup.get_text()
        if "Apply now" in page_text:
            print("✓ Found 'Apply now' button on page")
            # Try to click via Selenium
            try:
                apply_link = driver.find_element(By.LINK_TEXT, "Apply now")
                print("  Clicking apply button...")
                apply_link.click()
                time.sleep(3)

                # Check again for form
                soup = BeautifulSoup(driver.page_source, "html.parser")
                forms = soup.find_all("form")
                if forms:
                    print(f"✓ Form appeared after click! Found {len(forms)} forms")
                else:
                    print("Still no form visible")
            except Exception as e:
                print(f"  Could not click: {e}")

    print("\n" + "=" * 60)
    print("Browser is open. Check the page and press Ctrl+C to close.")
    print("=" * 60)

    # Keep browser open
    while True:
        time.sleep(1)

except KeyboardInterrupt:
    print("\n✓ Closing...")
except Exception as e:
    print(f"Error: {e}")
finally:
    driver.quit()
