from datetime import date, datetime, timedelta
import time
import sys
from openpuc_scrapers.scrapers.il import build_icc_search_url

def test_build_url():
    """Test URL builder with and without date filter"""
    # Test without date
    url1 = build_icc_search_url(service_types=["Electric"])
    print(f"URL without date: {url1}")
    
    # Test with date
    test_date = date.today() - timedelta(days=90)  # 90 days ago
    url2 = build_icc_search_url(service_types=["Electric"], after_date=test_date)
    print(f"URL with date ({test_date}): {url2}")
    
    # Verify date format in URL
    date_str = test_date.strftime("%m/%d/%Y")
    assert f"filedAfter={date_str}" in url2, "Date parameter not in URL"
    print("URL builder test passed")

if __name__ == "__main__":
    print("Testing Illinois ICC Scraper implementation...")
    print("=" * 50)
    
    print("\nTest 1: URL Builder")
    test_build_url()
    
    print("\nAll tests completed.") 