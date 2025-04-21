"""
Test script specifically for the schedule at https://www.icc.illinois.gov/docket/P2025-0274/schedule
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

def analyze_schedule_page():
    """
    Analyze the schedule page structure and extract the schedule information.
    """
    url = "https://www.icc.illinois.gov/docket/P2025-0274/schedule"
    print(f"Analyzing schedule page: {url}")
    
    driver = None
    
    try:
        # Set up WebDriver
        print("Initializing WebDriver...")
        driver = get_driver()
        
        # Navigate to the page
        print(f"Navigating to {url}")
        driver.get(url)
        
        # Wait for page to load
        print("Waiting for page to load...")
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.TAG_NAME, "h1"))
        )
        print("Page loaded successfully")
        
        # Get the page HTML
        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        
        # Check page title first
        title = soup.find('h1')
        if title:
            print(f"Page title: {title.text.strip()}")
        
        # Look for the schedule elements
        print("\nAnalyzing schedule elements...")
        
        # Try to find the schedule container or any elements that might contain schedule data
        # Examine all possible container types based on page structure
        containers = [
            ('article', {}),
            ('div', {'class': 'row'}),
            ('section', {}),
            ('table', {}),
            ('ul', {}),
            ('ol', {}),
            ('dl', {})
        ]
        
        for tag, attrs in containers:
            found = soup.find_all(tag, attrs)
            if found:
                print(f"Found {len(found)} <{tag}> elements")
                
                # Check each container for schedule-related content
                for i, container in enumerate(found):
                    text = container.get_text().strip()
                    if 'schedule' in text.lower() or 'deadline' in text.lower() or 'june' in text.lower():
                        print(f"\nFound potential schedule container ({tag} #{i+1}):")
                        print("-" * 50)
                        print(text[:200] + "..." if len(text) > 200 else text)
                        print("-" * 50)
        
        # Look for specific date and time patterns
        print("\nLooking for date and time patterns...")
        date_elements = soup.find_all(text=lambda text: text and ('2025' in text or 'June' in text or 'PM' in text))
        if date_elements:
            print(f"Found {len(date_elements)} elements containing date/time information:")
            for i, elem in enumerate(date_elements[:5]):
                print(f"{i+1}. {elem.strip()}")
                
                # Look at the parent elements to understand structure
                parent = elem.parent
                if parent:
                    print(f"   Parent tag: <{parent.name}>")
                    if parent.name == 'time':
                        print(f"   Parent datetime attribute: {parent.get('datetime')}")
                    
                    # Look at siblings and surrounding elements
                    for sibling in parent.next_siblings:
                        if sibling.name and sibling.string and sibling.string.strip():
                            print(f"   Next sibling: <{sibling.name}> {sibling.string.strip()}")
                            break
                    
                    grandparent = parent.parent
                    if grandparent and grandparent.name:
                        print(f"   Grandparent tag: <{grandparent.name}>")
        
        # Examine all h2, h3, h4 headings as they often structure sections
        headings = soup.find_all(['h2', 'h3', 'h4'])
        if headings:
            print(f"\nFound {len(headings)} heading elements:")
            for i, heading in enumerate(headings):
                print(f"{i+1}. <{heading.name}> {heading.text.strip()}")
                next_elem = heading.find_next()
                if next_elem:
                    print(f"   Next element: <{next_elem.name}>")
        
        # Let's develop a custom schedule detection algorithm based on our findings
        print("\nAttempting to extract schedule with custom algorithm...")
        
        # Look for month names (like "Jun" or "June") and year references (like "2025")
        month_containing_elements = soup.find_all(
            lambda tag: tag.string and tag.string.strip() and 
            any(month in tag.string.lower() for month in ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'])
        )
        
        found_entries = []
        for elem in month_containing_elements:
            date_text = elem.string.strip() if elem.string else ""
            
            # Try to find associated time
            time_elem = elem.find_next(lambda tag: tag.string and ('am' in tag.string.lower() or 'pm' in tag.string.lower()))
            time_text = time_elem.string.strip() if time_elem and time_elem.string else ""
            
            # Try to find description or type
            desc_elem = time_elem.find_next('p') if time_elem else elem.find_next('p')
            desc_text = desc_elem.text.strip() if desc_elem else ""
            
            if not desc_text:
                # Try to find a nearby heading as a possible description
                nearby_heading = elem.find_previous(['h2', 'h3', 'h4', 'h5'])
                if nearby_heading:
                    desc_text = nearby_heading.text.strip()
            
            if date_text:
                entry = {
                    'date': date_text,
                    'time': time_text,
                    'description': desc_text
                }
                found_entries.append(entry)
                print(f"Found schedule entry: {entry}")
        
        # Print the full HTML for detailed analysis
        print("\nFull HTML for schedule section:")
        schedule_section = soup.find('section', {'id': 'schedule'}) or soup.find('div', {'class': 'container'})
        if schedule_section:
            print(schedule_section.prettify()[:1000])  # First 1000 chars to avoid flooding
        else:
            print("Could not identify a specific schedule section")
            
        return True
    
    except Exception as e:
        print(f"ERROR: Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if driver:
            print("Closing WebDriver...")
            driver.quit()

def main():
    """Run the schedule page analysis."""
    print("=== ANALYZING ILLINOIS ICC SCHEDULE PAGE ===")
    success = analyze_schedule_page()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main()) 