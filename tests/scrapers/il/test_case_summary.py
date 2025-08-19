"""
Test script for Illinois ICC case summary scraping.
"""
import sys
import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from bs4 import BeautifulSoup

# Add the project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
    print(f"Added {project_root} to Python path")

def get_driver(headless=True):
    """Create and configure a WebDriver instance."""
    options = Options()
    if headless:
        options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    return webdriver.Chrome(options=options)

def test_case_summary_scraping():
    """
    Test the case summary scraping functionality.
    """
    # Import the necessary classes
    try:
        from openpuc_scrapers.scrapers.il import IllinoisICC, ILICCCaseData
    except ImportError as e:
        print(f"Error importing required modules: {e}")
        print("Ensure the openpuc_scrapers package is installed or in your PYTHONPATH")
        return False
    
    # Test case URLs
    test_cases = [
        {
            "url": "https://www.icc.illinois.gov/docket/P2025-0274",
            "number": "25-0274",
            "category": "Electric"
        },
        {
            "url": "https://www.icc.illinois.gov/docket/P2021-0858",
            "number": "21-0858",
            "category": "Electric"
        }
    ]
    
    # Use command line argument for case index if provided
    if len(sys.argv) > 1:
        try:
            case_index = int(sys.argv[1])
            if 0 <= case_index < len(test_cases):
                test_cases = [test_cases[case_index]]
            else:
                print(f"Invalid case index: {case_index}. Must be between 0 and {len(test_cases)-1}")
        except ValueError:
            print(f"Invalid case index: {sys.argv[1]}. Must be an integer")
    
    driver = None
    success = False
    
    try:
        # Create a scraper instance
        print("Creating scraper instance...")
        scraper = IllinoisICC()
        
        # Set up WebDriver
        print("Initializing WebDriver...")
        driver = get_driver()
        
        # Test each case
        for case_data in test_cases:
            case_url = case_data["url"]
            docket_govid = case_data["number"]
            case_category = case_data["category"]
            
            print(f"\nTesting case summary scraping for case: {docket_govid}")
            print(f"URL: {case_url}")
            
            # Navigate to the case page
            print(f"Navigating to case page...")
            driver.get(case_url)
            
            # Wait for page to load
            print("Waiting for page to load...")
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.TAG_NAME, "h1"))
            )
            print("Page loaded successfully")
            
            # Get the page HTML
            html = driver.page_source
            soup = BeautifulSoup(html, 'html.parser')
            
            # Test the case summary scraping
            print("Scraping case summary...")
            case = scraper.scrape_case_summary(
                {
                    "case_url": case_url,
                    "docket_govid": docket_govid,
                    "category": case_category
                }
            )
            
            # Verify results
            if not case:
                print("ERROR: Failed to scrape case summary")
                continue
                
            if not isinstance(case, ILICCCaseData):
                print(f"ERROR: Result is not an ILICCCaseData, got {type(case)}")
                continue
            
            # Check basic case properties
            print("\nCase summary details:")
            print(f"  Case Number: {case.docket_govid}")
            print(f"  Title: {case.case_title}")
            print(f"  Category: {case.category}")
            print(f"  Status: {case.case_status}")
            print(f"  URL: {case.case_url}")
            
            # Check additional case fields
            print("\nAdditional case fields:")
            if case.service_type:
                print(f"  Service Type: {case.service_type}")
            if case.filing_date:
                print(f"  Filing Date: {case.filing_date}")
            if case.applicant:
                print(f"  Applicant: {case.applicant}")
            if case.industry:
                print(f"  Industry: {case.industry}")
            if case.judge_name:
                print(f"  Judge(s): {', '.join(case.judge_name) if isinstance(case.judge_name, list) else case.judge_name}")
            
            # Check service list if available
            if hasattr(case, 'service_list') and case.service_list:
                print(f"\nService List: {len(case.service_list)} entries")
                for i, entry in enumerate(case.service_list[:3]):
                    print(f"  {i+1}. {entry.name} ({entry.party_type or 'Unknown party type'})")
                if len(case.service_list) > 3:
                    print(f"  ... and {len(case.service_list) - 3} more")
            
            print("\nCASE SUMMARY TEST: SUCCESS")
            success = True
            
    except Exception as e:
        print(f"ERROR: Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if driver:
            print("Closing WebDriver...")
            driver.quit()
        
        print(f"Case summary test {'succeeded' if success else 'failed'}")
        
    return success

def main():
    """Run the case summary scraping test."""
    print("=== TESTING ILLINOIS ICC CASE SUMMARY SCRAPING ===")
    success = test_case_summary_scraping()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main()) 
