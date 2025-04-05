#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test file for the Illinois ICC docket sheet scraping functionality.
Tests the extraction of docket sheet entries from case pages.
"""

import os
import sys
import traceback
from bs4 import BeautifulSoup
from datetime import datetime, date
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Add the project root to Python path to allow running test directly
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
sys.path.insert(0, project_root)
print(f"Added {project_root} to Python path")


def test_docket_sheet_parsing():
    """
    Test the docket sheet parsing functionality against a live website.
    This test gets a real docket sheet page and verifies that we can parse the data.
    """
    # Test case URL - using a known case that has a docket sheet
    case_id = "P2021-0858"  # Use this as default
    
    # If command line arguments are provided, use them as test case ID
    if len(sys.argv) > 1:
        case_id = sys.argv[1]
    
    # Construct the URL
    case_url = f"https://www.icc.illinois.gov/docket/{case_id}/docket-sheet"
    print(f"Testing docket sheet parsing using URL: {case_url}")
    
    driver = None
    success = False
    
    try:
        # Import the necessary classes
        from openpuc_scrapers.scrapers.il import IllinoisICC
        
        # Initialize Chrome WebDriver with headless option
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        print("Initializing WebDriver...")
        driver = webdriver.Chrome(options=chrome_options)
        
        # Navigate to the case page
        print(f"Navigating to {case_url}...")
        driver.get(case_url)
        
        # Wait for the page to load
        wait = WebDriverWait(driver, 30)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "h1")))
        print("Page loaded successfully")
        
        # Create a scraper instance
        scraper = IllinoisICC()
        
        # Get the page HTML and parse it
        html = driver.page_source
        soup = BeautifulSoup(html, "html.parser")
        
        # Parse the docket sheet
        docket_entries = scraper._parse_docket_sheet_from_soup(soup)
        print(f"Found {len(docket_entries)} docket sheet entries")
        
        # Print the first few entries for inspection
        for i, entry in enumerate(docket_entries[:3]):  # Show first 3 entries
            print(f"\nDocket Entry #{i+1}:")
            print(f"Date: {entry.get('date')}")
            print(f"Title: {entry.get('title')}")
            print(f"Description: {entry.get('description')}")
        
        # Convert the dictionary entries to ILICCDocketSheetEntry objects
        print("\nConverting to ILICCDocketSheetEntry objects...")
        
        from openpuc_scrapers.scrapers.il import ILICCDocketSheetEntry
        model_entries = []
        
        for entry_dict in docket_entries:
            docket_entry = ILICCDocketSheetEntry(
                action_date=entry_dict.get("date"),
                action_title=entry_dict.get("title"),
                action_description=entry_dict.get("description")
            )
            model_entries.append(docket_entry)
        
        print(f"Successfully converted {len(model_entries)} entries to ILICCDocketSheetEntry objects")
        
        # Print model entries (up to 2)
        max_entries_to_show = min(2, len(model_entries))
        for i in range(max_entries_to_show):
            entry = model_entries[i]
            print(f"\nModel Entry #{i+1}:")
            print(f"Action Date: {entry.action_date}")
            print(f"Action Title: {entry.action_title}")
            print(f"Action Description: {entry.action_description}")
        
        success = True
        print("\nDocket sheet parsing test passed successfully")
    
    except Exception as e:
        print(f"Error during docket sheet parsing test: {e}")
        traceback.print_exc()
    
    finally:
        # Close the WebDriver
        if driver:
            driver.quit()
            print("WebDriver closed")
        
        if success:
            print("✅ Test completed successfully")
        else:
            print("❌ Test failed")
            sys.exit(1)


if __name__ == "__main__":
    test_docket_sheet_parsing() 