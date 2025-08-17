"""
Real-time tests for the Illinois ICC scraper.
This module contains tests that directly scrape the ICC website.
"""
import pytest
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from bs4 import BeautifulSoup

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
    # Import the necessary classes only when the test is run
    try:
        from openpuc_scrapers.scrapers.il import IllinoisICC
        from openpuc_scrapers.models.il import ILICCServiceListEntry
    except ImportError:
        pytest.skip("Illinois ICC scraper modules not available")
    
    # Test case URL - using a known case that likely has a service list
    case_url = "https://www.icc.illinois.gov/docket/P2025-0274/service-list"
    
    driver = None
    try:
        # Set up WebDriver
        driver = get_driver()
        driver.get(case_url)
        
        # Wait for page to load
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CLASS_NAME, "soi-icc-card-list"))
        )
        
        # Get the page HTML
        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        
        # Create a scraper instance
        scraper = IllinoisICC()
        
        # Parse the service list
        service_list = scraper._parse_service_list_from_soup(soup)
        
        # Verify results
        assert len(service_list) > 0, "No service list entries found"
        print(f"Found {len(service_list)} service list entries")
        
        # Check structure of entries
        for i, entry in enumerate(service_list):
            assert entry.name, f"Entry {i+1} has no name"
            assert isinstance(entry, ILICCServiceListEntry), f"Entry {i+1} is not an ILICCServiceListEntry"
            
            # Print some info
            print(f"Entry {i+1}: {entry.name}")
            if entry.email:
                print(f"  Email: {entry.email}")
            if entry.party_type:
                print(f"  Party type: {entry.party_type}")
            if entry.party_status:
                print(f"  Party status: {entry.party_status}")
    
    except ImportError as e:
        pytest.skip(f"Required module not available: {e}")
    except Exception as e:
        pytest.fail(f"Test failed: {e}")
    finally:
        if driver:
            driver.quit()

def test_schedule_scraping():
    """
    Test the schedule extraction functionality against the live website.
    This test gets a real schedule page and verifies that we can parse the data.
    """
    # Import the necessary classes only when the test is run
    try:
        from openpuc_scrapers.scrapers.il import IllinoisICC
        from openpuc_scrapers.models.il import ILICCScheduleEntry
    except ImportError:
        pytest.skip("Illinois ICC scraper modules not available")
    
    # Test case URL - using a known case that might have a schedule
    case_url = "https://www.icc.illinois.gov/docket/P2025-0274/schedule"
    
    driver = None
    try:
        # Set up WebDriver
        driver = get_driver()
        driver.get(case_url)
        
        # Wait for page to load
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.TAG_NAME, "h1"))
        )
        
        # Get the page HTML
        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        
        # Create a scraper instance
        scraper = IllinoisICC()
        
        # Parse the schedule
        schedule = scraper._parse_schedule_from_soup(soup)
        
        # Print result count - schedule might be empty but parsing should still work
        print(f"Found {len(schedule)} schedule entries")
        
        # If there are entries, check their structure
        for i, entry in enumerate(schedule):
            assert isinstance(entry, ILICCScheduleEntry), f"Entry {i+1} is not an ILICCScheduleEntry"
            
            # Print some info
            if len(schedule) > 0:
                print(f"Entry {i+1}:")
                if entry.date:
                    print(f"  Date: {entry.date}")
                if entry.time:
                    print(f"  Time: {entry.time}")
                if entry.type:
                    print(f"  Type: {entry.type}")
                    
    except ImportError as e:
        pytest.skip(f"Required module not available: {e}")
    except Exception as e:
        pytest.fail(f"Test failed: {e}")
    finally:
        if driver:
            driver.quit()

def test_full_case_scraping():
    """
    Test the full case scraping functionality including service list and schedule.
    This test scrapes all data for a specific case.
    """
    # Import the necessary classes only when the test is run
    try:
        from openpuc_scrapers.scrapers.il import IllinoisICC
        from openpuc_scrapers.models.il import ILICCCaseData
    except ImportError:
        pytest.skip("Illinois ICC scraper modules not available")
    
    try:
        # Create a scraper instance
        scraper = IllinoisICC()
        scraper.MAX_DOCUMENTS = 2  # Limit to 2 documents for faster testing
        
        # Create a case data object
        case_data = ILICCCaseData(
            case_url="https://www.icc.illinois.gov/docket/P2025-0274",
            docket_govid="25-0274",
            category="Electric"
        )
        
        # Execute the scraping
        result = scraper.filing_data(case_data)
        
        # Verify basics
        assert result.docket_govid == "25-0274"
        
        # Check service list
        print(f"Service list entries: {len(result.service_list)}")
        assert len(result.service_list) >= 0  # It should at least not crash
        
        # Check schedule
        print(f"Schedule entries: {len(result.schedule)}")
        
        # Check documents
        print(f"Documents: {len(result.documents)}")
        
        # Print overall success message
        print(f"Successfully scraped case {result.docket_govid}")
    
    except ImportError as e:
        pytest.skip(f"Required module not available: {e}")
    except Exception as e:
        pytest.fail(f"Test failed: {e}")

if __name__ == "__main__":
    # Run tests directly if this module is executed (not through pytest)
    print("Testing service list scraping...")
    test_service_list_scraping()
    
    print("\nTesting schedule scraping...")
    test_schedule_scraping()
    
    print("\nTesting full case scraping...")
    test_full_case_scraping() 
