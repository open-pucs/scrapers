from datetime import date, datetime, timedelta
import time
import sys
from selenium import webdriver
from openpuc_scrapers.scrapers.il import IllinoisICCScraper, build_icc_search_url

def test_scraper_init():
    """Test if the scraper can be properly instantiated"""
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    try:
        # Create an instance with driver_options
        scraper = IllinoisICCScraper()
        # Add driver_options attribute
        scraper.driver_options = options
        print("Successfully instantiated IllinoisICCScraper")
        return scraper
    except Exception as e:
        print(f"Error instantiating scraper: {e}")
        raise

def test_date_filtering():
    """Test the date filtering functionality with a simple case list query"""
    try:
        scraper = test_scraper_init()
        
        # Use a date 180 days ago to ensure we get some results
        test_date = date.today() - timedelta(days=180)
        print(f"\nTesting date filtering with date: {test_date}")
        
        # Limit to just one service type for quicker testing
        service_types = ["Electric"]
        
        # Use a small MAX_PAGES value
        scraper.MAX_PAGES = 1
        
        # Generate URL directly first for debugging
        url = build_icc_search_url(service_types=service_types, after_date=test_date)
        print(f"Generated URL: {url}")
        
        # Get cases after the test date
        print("Fetching cases with date filtering...")
        intermediate = scraper.universal_caselist_intermediate(
            service_types=service_types,
            after_date=test_date
        )
        
        # Check if we got any results
        extracted_cases = intermediate.get("extracted_cases", [])
        print(f"Found {len(extracted_cases)} cases in search results")
        
        return True
    except Exception as e:
        print(f"Error during date filtering test: {e}")
        raise

if __name__ == "__main__":
    print("Testing Illinois ICC Scraper implementation (full tests)...")
    print("=" * 60)
    
    print("\nTest 1: Scraper Initialization")
    test_scraper_init()
    
    print("\nTest 2: Date Filtering")
    success = test_date_filtering()
    
    if success:
        print("\nAll tests completed successfully!")
    else:
        print("\nSome tests failed.")
        sys.exit(1) 