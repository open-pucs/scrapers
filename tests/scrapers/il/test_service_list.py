"""
Test script for Illinois ICC service list scraping.
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

def test_service_list_scraping():
    """
    Test the service list extraction functionality against the live website.
    This test gets a real service list page and verifies that we can parse the data.
    """
    # Import the necessary classes
    try:
        # Import directly from the scraper file
        from openpuc_scrapers.scrapers.il import IllinoisICC, ILICCServiceListEntry
    except ImportError as e:
        print(f"Error importing required modules: {e}")
        print("Ensure the openpuc_scrapers package is installed or in your PYTHONPATH")
        return False
    
    # Test case URL - using a known case that likely has a service list
    case_url = "https://www.icc.illinois.gov/docket/P2025-0274/service-list"
    print(f"Testing service list scraping using URL: {case_url}")
    
    driver = None
    success = False
    
    try:
        # Set up WebDriver
        print("Initializing WebDriver...")
        driver = get_driver()
        
        # Navigate to the service list page
        print(f"Navigating to {case_url}")
        driver.get(case_url)
        
        # Wait for page to load
        print("Waiting for page to load...")
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CLASS_NAME, "soi-icc-card-list"))
        )
        print("Page loaded successfully")
        
        # Get the page HTML
        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        
        # Create a scraper instance
        print("Creating scraper instance...")
        scraper = IllinoisICC()
        
        # Parse the service list
        print("Parsing service list...")
        service_list = scraper._parse_service_list_from_soup(soup)
        
        # Verify results
        if len(service_list) == 0:
            print("ERROR: No service list entries found")
            return False
        
        print(f"Found {len(service_list)} service list entries")
        
        # Check structure of entries and print details
        for i, entry in enumerate(service_list):
            print(f"\nEntry {i+1}: {entry.name}")
            
            if not entry.name:
                print("ERROR: Entry has no name")
                continue
                
            if not isinstance(entry, ILICCServiceListEntry):
                print(f"ERROR: Entry is not an ILICCServiceListEntry")
                continue
            
            # Print details
            if entry.role:
                print(f"  Role: {entry.role}")
            if entry.organization:
                print(f"  Organization: {entry.organization}")
            if entry.email:
                print(f"  Email: {entry.email}")
            if entry.phone:
                print(f"  Phone: {entry.phone}")
            if entry.party_type:
                print(f"  Party type: {entry.party_type}")
            if entry.party_status:
                print(f"  Party status: {entry.party_status}")
        
        print("\nSERVICE LIST SCRAPING TEST: SUCCESS")
        success = True
        return True
        
    except Exception as e:
        print(f"ERROR: Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if driver:
            print("Closing WebDriver...")
            driver.quit()
        
        print(f"Test {'succeeded' if success else 'failed'}")

def main():
    """Run the test."""
    success = test_service_list_scraping()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main()) 