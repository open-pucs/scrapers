"""
Test script for Illinois ICC document scraping.
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

def test_document_listing():
    """
    Test the document listing functionality - getting URLs of document detail pages.
    """
    # Import the necessary classes
    try:
        from openpuc_scrapers.scrapers.il import IllinoisICC
    except ImportError as e:
        print(f"Error importing required modules: {e}")
        print("Ensure the openpuc_scrapers package is installed or in your PYTHONPATH")
        return False
    
    # Test case URL - use a case known to have documents
    case_url = "https://www.icc.illinois.gov/docket/P2021-0858"
    document_url = f"{case_url}/documents"
    print(f"Testing document listing using URL: {document_url}")
    
    driver = None
    success = False
    document_urls = []
    
    try:
        # Set up WebDriver
        print("Initializing WebDriver...")
        driver = get_driver()
        
        # Navigate to the documents page
        print(f"Navigating to {document_url}")
        driver.get(document_url)
        
        # Wait for page to load
        print("Waiting for page to load...")
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.TAG_NAME, "h1"))
        )
        print("Page loaded successfully")
        
        # Get the page HTML
        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        
        # Create a scraper instance
        print("Creating scraper instance...")
        scraper = IllinoisICC()
        
        # Create a mock case data object for intermediate result
        intermediate_result = {
            "case_url": case_url,
            "docket_govid": "21-0858"
        }
        
        # Find document URLs
        print("Extracting document URLs...")
        
        # Find the document list container
        doc_list = soup.find('ul', class_='soi-icc-card-list')
        
        document_urls = []
        
        if not doc_list:
            print("Warning: Could not find document list container")
            
            # As a fallback, try to find all document links on the page
            all_links = soup.find_all('a', href=lambda href: href and '/documents/' in href)
            if all_links:
                print(f"Found {len(all_links)} document links using fallback method")
                
                for link in all_links:
                    href = link.get('href')
                    if href:
                        doc_url = f"{scraper.BASE_URL}{href}" if href.startswith('/') else href
                        document_urls.append(doc_url)
        else:
            # Find all list items with document links
            doc_items = doc_list.find_all('li', class_='soi-icc-card-list-item')
            print(f"Found {len(doc_items)} document items in the list")
            
            for item in doc_items:
                # Find the link within the card body
                link = item.find('h4').find('a') if item.find('h4') else None
                
                if link and link.get('href'):
                    href = link.get('href')
                    doc_url = f"{scraper.BASE_URL}{href}" if href.startswith('/') else href
                    document_urls.append(doc_url)
        
        # Verify results
        if len(document_urls) == 0:
            print("ERROR: No document URLs found")
            return False
        
        # Deduplicate URLs
        document_urls = list(set(document_urls))
        print(f"Found {len(document_urls)} unique document URLs")
        
        # Display sample of URLs
        for i, url in enumerate(document_urls[:5]):
            print(f"{i+1}. {url}")
        
        if len(document_urls) > 5:
            print(f"... and {len(document_urls) - 5} more")
        
        # Test successful
        print("\nDOCUMENT LISTING TEST: SUCCESS")
        success = True
        
        # Return document URLs for the next test
        return document_urls
        
    except Exception as e:
        print(f"ERROR: Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if driver:
            print("Closing WebDriver...")
            driver.quit()
        
        print(f"Document listing test {'succeeded' if success else 'failed'}")

def test_document_details(document_urls=None):
    """
    Test the document details extraction functionality.
    This test gets a real document detail page and verifies that we can parse the data.
    
    Args:
        document_urls: Optional list of document URLs to test. If not provided,
                      will call test_document_listing to get URLs.
    """
    # Import the necessary classes
    try:
        from openpuc_scrapers.scrapers.il import IllinoisICC, ILICCDocument, ILICCAttachmentDetail
    except ImportError as e:
        print(f"Error importing required modules: {e}")
        print("Ensure the openpuc_scrapers package is installed or in your PYTHONPATH")
        return False
        
    # If no document URLs provided, get them from the listing test
    if not document_urls:
        print("No document URLs provided, running document listing test...")
        document_urls = test_document_listing()
        if not document_urls:
            print("Failed to get document URLs")
            return False
    
    # If too many URLs, just test a few
    test_urls = document_urls[:3] if len(document_urls) > 3 else document_urls
    
    driver = None
    success = False
    
    try:
        # Set up WebDriver
        print("\nInitializing WebDriver for document details test...")
        driver = get_driver()
        
        # Create a scraper instance
        print("Creating scraper instance...")
        scraper = IllinoisICC()
        
        # Test each document URL
        successful_docs = 0
        
        for i, doc_url in enumerate(test_urls):
            print(f"\nTesting document details for URL ({i+1}/{len(test_urls)}): {doc_url}")
            
            # Navigate to the document page
            print(f"Navigating to {doc_url}")
            driver.get(doc_url)
            
            # Wait for page to load
            print("Waiting for page to load...")
            title_xpath = "//h1"
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.XPATH, title_xpath))
            )
            print("Page loaded successfully")
            
            # Get the page HTML
            html = driver.page_source
            soup = BeautifulSoup(html, 'html.parser')
            
            # Parse document details
            print("Parsing document details...")
            document = scraper._parse_document_details_from_soup(soup, doc_url)
            
            # Verify results
            if not document:
                print("ERROR: Failed to parse document details")
                continue
            
            if not isinstance(document, ILICCDocument):
                print(f"ERROR: Result is not an ILICCDocument, got {type(document)}")
                continue
            
            # Check document properties
            print("Document details:")
            print(f"  Type: {document.doc_type}")
            print(f"  Filed By: {document.doc_filed_by}")
            print(f"  Filed For: {document.doc_filed_for}")
            print(f"  Date Filed: {document.doc_date_filed}")
            print(f"  Description: {document.doc_description}")
            
            # Check attachments
            print(f"  Attachments: {len(document.doc_attached_documents)}")
            
            for j, attachment in enumerate(document.doc_attached_documents[:3]):
                if not isinstance(attachment, ILICCAttachmentDetail):
                    print(f"  ERROR: Attachment {j+1} is not an ILICCAttachmentDetail")
                    continue
                    
                print(f"    {j+1}. {attachment.name}: {attachment.url}")
            
            if len(document.doc_attached_documents) > 3:
                print(f"    ... and {len(document.doc_attached_documents) - 3} more")
            
            # This document was successful
            successful_docs += 1
        
        # Overall success if at least one document was parsed successfully
        if successful_docs > 0:
            print(f"\nDOCUMENT DETAILS TEST: SUCCESS ({successful_docs}/{len(test_urls)} documents)")
            success = True
        else:
            print("\nDOCUMENT DETAILS TEST: FAILED (0 documents parsed successfully)")
            success = False
        
        return success
        
    except Exception as e:
        print(f"ERROR: Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if driver:
            print("Closing WebDriver...")
            driver.quit()
        
        print(f"Document details test {'succeeded' if success else 'failed'}")

def main():
    """Run the document scraping tests."""
    print("=== TESTING ILLINOIS ICC DOCUMENT SCRAPING ===")
    
    # Test document listing
    print("\n1. Testing document listing...")
    document_urls = test_document_listing()
    if not document_urls:
        print("Document listing test failed, cannot continue")
        return 1
    
    # Test document details
    print("\n2. Testing document details...")
    success = test_document_details(document_urls)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main()) 
