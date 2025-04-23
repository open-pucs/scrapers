import time
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

from bs4 import BeautifulSoup
from pydantic import BaseModel

# Selenium Imports (Ensure these are installed: pip install selenium webdriver-manager)


# Project Imports
from openpuc_scrapers.models.case import GenericCase
from openpuc_scrapers.models.filing import GenericFiling

# Import scraper base class
from openpuc_scrapers.models.timestamp import date_to_rfctime
from openpuc_scrapers.scrapers.base import GenericScraper

# --- Illinois Specific Models ---


class ILICCAttachmentDetail(BaseModel):
    """Model for Illinois ICC attachment details"""

    url: str
    description: str
    file_size: Optional[str] = None
    file_type: Optional[str] = None


class ILICCServiceListEntry(BaseModel):
    """Model for Illinois ICC service list entries"""

    name: str
    role: Optional[str] = None
    organization: Optional[str] = None
    address: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    party_type: Optional[str] = None
    party_status: Optional[str] = None


class ILICCScheduleEntry(BaseModel):
    """Model for Illinois ICC schedule entries"""

    date: str
    time: Optional[str] = None
    type: str
    description: str
    location: Optional[str] = None


class ILICCDocketSheetEntry(BaseModel):
    """Model for Illinois ICC docket sheet entries"""

    action_date: str
    title: str
    description: str


class ILICCCaseDetails(BaseModel):
    """Model for Illinois ICC case details"""

    title: str
    category: Optional[str] = None
    status: Optional[str] = None
    filing_date: Optional[str] = None
    judge_names: List[str] = []


class ILICCDocument(BaseModel):
    """Model for Illinois ICC documents"""

    url: str
    type: str
    filed_by: Optional[str] = None
    filed_for: Optional[str] = None
    date_filed: Optional[str] = None
    means_received: Optional[str] = None
    description: Optional[str] = None
    attachments: List[ILICCAttachmentDetail] = []


class ILICCCaseData(BaseModel):
    """Model for Illinois ICC case data"""

    case_url: str
    case_number: str
    category: Optional[str] = None
    case_details: Optional[ILICCCaseDetails] = None
    docket_sheet: List[ILICCDocketSheetEntry] = []
    service_list: List[ILICCServiceListEntry] = []
    schedule: List[ILICCScheduleEntry] = []
    documents: List[ILICCDocument] = []


class ILICCFilingData(BaseModel):
    """Model for Illinois ICC filing data"""

    case_id: str
    filing_date: str
    filing_type: str
    filing_party: str
    filing_description: str
    filing_documents: List[ILICCDocument]


# --- Service Type Configuration ---

SERVICE_TYPE_MAP = {
    "9-1-1 Authority": "26",
    "9-1-1 System Provider": "23",
    "Administrative Law Judge Designation": "15",
    "Agents, Brokers and Consultants (ABC)": "21",
    "Airport Matter": "1",
    "Alternative Gas Supplier (AGS)": "17",
    "Alternative Retail Electric Supplier (ARES)": "2",
    "Cable/Video Franchise": "20",
    "Cellular/Mobile Telephone": "3",
    "Competitive Access Provider": "4",
    "Customer Owned Pay Phone (COPTS)": "5",
    "Distributed Generation": "24",
    "Electric": "7",
    "Electric Cooperative": "6",
    "Electric Vehicle Charging Stations": "25",
    "Energy Efficiency Installers": "28",
    "Gas": "8",
    "Interconnected VoIP Service Provider": "22",
    "Inter-Exchange Carrier (IXC)": "9",
    "Local Exchange Carrier (LEC)": "10",
    "Meter Service Provider (MSP)": "16",
    "Pipeline": "11",
    "Prepaid Calling Service Provider": "19",
    "Railroad": "14",
    "Sewer": "12",
    "Transmission Utility": "18",
    "Utility-Scale Solar Installers": "29",
    "Water": "13",
}

# Invert map for easy lookup by number if needed
SERVICE_VALUE_MAP = {v: k for k, v in SERVICE_TYPE_MAP.items()}


def build_icc_search_url(
    service_types: str | List[str] = "all", after_date: Optional[date] = None
) -> str:
    """Builds the ICC search results URL based on selected service types and date.

    Args:
        service_types: Either the string "all" to include all types, or a list
                       containing service type names (str) or their corresponding
                       value numbers (str or int).
        after_date: Optional date to filter cases filed after this date.

    Returns:
        The constructed URL for the ICC search results page.

    Raises:
        ValueError: If an invalid service type name or number is provided.
    """
    base_results_url = "https://www.icc.illinois.gov/docket/search/cases/results"
    selected_st_values = []

    if service_types == "all":
        selected_st_values = list(SERVICE_TYPE_MAP.values())
    elif isinstance(service_types, list):
        for st_input in service_types:
            st_input_str = str(st_input).strip()
            if st_input_str in SERVICE_VALUE_MAP:  # Input is a number (string or int)
                selected_st_values.append(st_input_str)
            elif st_input_str in SERVICE_TYPE_MAP:  # Input is a name
                selected_st_values.append(SERVICE_TYPE_MAP[st_input_str])
            else:
                raise ValueError(f"Invalid service type provided: {st_input}")
    else:
        raise TypeError("service_types must be 'all' or a list of strings/numbers.")

    selected_st_values = sorted(list(set(selected_st_values)))

    if not selected_st_values:
        raise ValueError("No valid service types selected.")

    # Build the base URL with service types
    st_params = "&".join([f"st={val}" for val in selected_st_values])
    target_url = f"{base_results_url}?{st_params}&o=False"

    # Add date filter if provided
    if after_date:
        # Format date as MM/DD/YYYY
        date_str = after_date.strftime("%m/%d/%Y")
        target_url += f"&filedAfter={date_str}"

    return target_url


# --- Scraper Class ---


class IllinoisICCScraper(GenericScraper[ILICCCaseData, ILICCFilingData]):
    """Scraper for Illinois ICC website."""

    state: str = "il"
    jurisdiction_name: str = "il_puc"

    def __init__(self):
        """Initialize the scraper."""

        # from selenium import webdriver

        # self.driver = webdriver.Chrome()
        # self.driver.implicitly_wait(10)

    # def __del__(self):
    #     """Clean up resources."""
    #     if hasattr(self, "driver"):
    #         self.driver.quit()

    BASE_URL = "https://www.icc.illinois.gov"

    # Configuration options
    MAX_PAGES = 1  # Maximum number of pages to scrape for case list
    MAX_DOCUMENTS = 10  # Maximum number of documents to fetch per case

    def _get_driver(self):

        from selenium import webdriver

        options = webdriver.ChromeOptions()
        # Add common useful options
        if "--headless" not in str(options.arguments):
            # Only add these if not already set in driver_options
            options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--log-level=3")
            options.add_argument("--disable-extensions")
            options.add_argument("--disable-infobars")

        try:
            # Consider using webdriver-manager for easier driver setup
            # from selenium.webdriver.chrome.service import Service
            # driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
            driver = webdriver.Chrome(
                options=options
            )  # Assumes chromedriver is in PATH or managed by Selenium Manager
            driver.set_page_load_timeout(60)  # Set default timeout to 60 seconds
            return driver
        except Exception as e:
            print(f"Error initializing WebDriver: {e}")
            print(
                "Ensure chromedriver is installed and in your PATH, or use webdriver-manager."
            )
            raise

    def _close_driver(self, driver):
        if driver:
            try:
                driver.quit()
            except Exception as e:
                print(f"Error closing WebDriver: {e}")

    def universal_caselist_intermediate(
        self,
        service_types: str | List[str] = "all",
        stop_at_case_identifier: Optional[str] = None,
        after_date: Optional[date] = None,
    ) -> Dict[str, Any]:

        from selenium.common.exceptions import TimeoutException
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.support.ui import WebDriverWait

        """
        Constructs search URL, navigates, handles pagination, and extracts
        (case_url, case_number) tuples directly using Selenium until
        stop_at_case_identifier is found (if provided).
        Returns a dictionary containing the list of extracted tuples.

        Args:
            service_types: Types of services to filter by
            stop_at_case_identifier: Optional identifier to stop at
            after_date: Optional date to filter cases filed after

        Returns:
            Dictionary containing extracted cases and other metadata
        """
        target_url = build_icc_search_url(service_types, after_date)
        print(f"Constructed target URL: {target_url}")
        if stop_at_case_identifier:
            print(
                f"Will stop scraping if identifier '{stop_at_case_identifier}' is found."
            )

        driver = self._get_driver()
        extracted_cases: List[Tuple[str, str]] = (
            []
        )  # List to store (URL, Number) tuples
        processed_case_urls = (
            set()
        )  # To handle potential duplicates across pages if pagination glitches
        stop_processing = False  # Flag to break outer loop

        try:
            print("Navigating directly to search results URL...")
            driver.get(target_url)
            wait = WebDriverWait(driver, 30)
            list_item_selector = "li.soi-icc-card-list-item"
            print(
                f"Waiting for initial case list items ({list_item_selector}) to load..."
            )

            # Add better error handling for the initial page load
            try:
                wait.until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, list_item_selector)
                    )
                )
                print("Initial search results loaded.")
            except TimeoutException:
                print(
                    "Timeout waiting for search results to load. Checking if any content loaded..."
                )
                # Try to see what's on the page
                try:
                    body = driver.find_element(By.TAG_NAME, "body")
                    print(f"Page title: {driver.title}")
                    print(f"Body text length: {len(body.text)}")
                    if "Error" in driver.title or "Error" in body.text:
                        print(
                            "Error page detected. URL might be invalid or site is down."
                        )
                    return {
                        "error": "Timeout during search init",
                        "extracted_cases": [],
                    }
                except:
                    print(
                        "Could not even find body element. Page likely didn't load at all."
                    )
                    return {
                        "error": "Failed to load search page",
                        "extracted_cases": [],
                    }

            current_page = 1
            while True:  # Pagination loop
                print(f"Extracting data from results page {current_page}...")
                time.sleep(1)
                case_link_selector = (
                    "li.soi-icc-card-list-item h3 > a[href*='/docket/']"
                )

                try:
                    wait.until(
                        EC.presence_of_element_located(
                            (By.CSS_SELECTOR, case_link_selector)
                        )
                    )
                    link_elements = driver.find_elements(
                        By.CSS_SELECTOR, case_link_selector
                    )
                    print(
                        f"Found {len(link_elements)} case links on page {current_page}."
                    )

                    page_cases_added = 0
                    for link_tag_element in link_elements:  # Loop through cases on page
                        try:
                            relative_url = link_tag_element.get_attribute("href")
                            case_number = link_tag_element.text.strip()

                            if not relative_url or not case_number:
                                continue

                            case_url = (
                                f"{self.BASE_URL}{relative_url}"
                                if relative_url.startswith("/")
                                else relative_url
                            )
                            case_url = case_url.split("?")[0]

                            # --- Check against stop identifier ---
                            # Decide whether to use URL or number as the identifier
                            identifier_to_check = case_number
                            if (
                                stop_at_case_identifier
                                and identifier_to_check == stop_at_case_identifier
                            ):
                                print(
                                    f"Found stop case identifier: {identifier_to_check}. Stopping extraction."
                                )
                                # Add the anchor case to the list before stopping
                                if case_url not in processed_case_urls:
                                    extracted_cases.append((case_url, case_number))
                                    processed_case_urls.add(case_url)
                                    page_cases_added += 1
                                stop_processing = True
                                break  # Stop processing links on this page
                            # --- End check ---

                            if case_url not in processed_case_urls:
                                extracted_cases.append((case_url, case_number))
                                processed_case_urls.add(case_url)
                                page_cases_added += 1

                        except Exception as e_inner:
                            print(
                                f"Error processing a link element on page {current_page}: {e_inner}"
                            )

                    print(
                        f"Added {page_cases_added} new cases from page {current_page}."
                    )

                    # If we broke from inner loop due to stop_identifier, break outer loop too
                    if stop_processing:
                        print("Stopping pagination due to found stop case identifier.")
                        break  # Break pagination loop

                except TimeoutException:  # ...
                    print(
                        f"Warning: Timeout waiting for case links ({case_link_selector}) on page {current_page}. Might be empty or loading issue."
                    )
                    break
                except Exception as e:  # ...
                    print(
                        f"Error finding or processing link elements on page {current_page}: {e}"
                    )
                    break

                # --- Pagination ---
                # If we already decided to stop, don't try to paginate
                if stop_processing:
                    break

                try:
                    # Simplified pagination with disabled class check
                    next_button_selector = "li.PagedList-skipToNext:not(.disabled) > a"
                    next_buttons = driver.find_elements(
                        By.CSS_SELECTOR, next_button_selector
                    )

                    if not next_buttons:
                        print(
                            "No 'Next' button found or it's disabled. End pagination."
                        )
                        break

                    print(f"Clicking Next for page {current_page + 1}...")
                    driver.execute_script("arguments[0].click();", next_buttons[0])

                    # Simpler wait with sleep
                    time.sleep(3)  # Simple but effective wait
                    current_page += 1

                except Exception as e:
                    print(f"Error during pagination: {e}")
                    break

            print(
                f"Finished extraction. Total unique cases extracted: {len(extracted_cases)}"
            )
            return {"extracted_cases": extracted_cases, "search_url": target_url}
        except TimeoutException:  # ...
            print("Timeout occurred during initial navigation...")
            return {
                "error": "Timeout during search init",
                "html_on_error": driver.page_source if driver else None,
            }
        except Exception as e:  # ...
            print(f"An error occurred during universal_caselist_intermediate: {e}")
            return {
                "error": str(e),
                "html_on_error": driver.page_source if driver else None,
            }
        finally:  # ...
            self._close_driver(driver)

    def universal_caselist_from_intermediate(
        self, intermediate: Dict[str, Any]
    ) -> List[ILICCCaseData]:
        """
        Converts the list of (case_url, case_number) tuples from the intermediate
        dictionary into a list of ILICCCaseData objects.
        """
        if intermediate.get("error"):
            print(
                f"Skipping case conversion due to error in intermediate step: {intermediate['error']}"
            )
            return []

        extracted_cases = intermediate.get("extracted_cases", [])
        if not extracted_cases:
            print("No extracted cases found in intermediate data.")
            return []

        cases: List[ILICCCaseData] = []
        search_url = intermediate.get("search_url", "")
        # TODO: Add logic to determine category based on search_url if necessary
        category = "UnknownCategory"  # Placeholder - needs update if category matters

        print(
            f"Converting {len(extracted_cases)} extracted tuples to ILICCCaseData objects..."
        )
        for case_url, case_number in extracted_cases:
            try:
                case_data = ILICCCaseData(
                    case_url=case_url,
                    case_number=case_number,
                    category=category,  # Use determined category
                )
                cases.append(case_data)
            except Exception as e:
                # Handle potential Pydantic validation errors or other issues
                print(
                    f"Error creating ILICCCaseData for URL {case_url}, Number {case_number}: {e}"
                )

        print(f"Successfully created {len(cases)} ILICCCaseData objects.")
        return cases

    def filing_data_intermediate(self, data: ILICCCaseData) -> Dict[str, Any]:

        from selenium.common.exceptions import TimeoutException
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.support.ui import WebDriverWait

        driver = self._get_driver()
        intermediate_result = data.model_dump()  # Start with existing data
        try:
            # First visit the main case details page
            print(f"Visiting case page: {data.case_url}")
            driver.get(str(data.case_url))
            wait = WebDriverWait(driver, 20)

            # Wait for main page to load
            case_title_xpath = "//h1"
            wait.until(EC.presence_of_element_located((By.XPATH, case_title_xpath)))

            # Store the main case page HTML
            intermediate_result["raw_case_page_html"] = driver.page_source
            main_soup = BeautifulSoup(driver.page_source, "html.parser")

            # Now navigate to the Docket Sheet page
            docket_sheet_url = f"{data.case_url}/docket-sheet"
            print(f"Navigating to docket sheet: {docket_sheet_url}")
            driver.get(docket_sheet_url)

            try:
                # Wait for docket sheet page to load
                wait.until(EC.presence_of_element_located((By.XPATH, case_title_xpath)))
                # Store the docket sheet HTML
                intermediate_result["raw_docket_sheet_html"] = driver.page_source
            except TimeoutException:
                print(
                    f"Warning: Timeout while loading docket sheet page: {docket_sheet_url}"
                )

            # Navigate to Documents tab to get document URLs
            documents_url = f"{data.case_url}/documents"
            print(f"Navigating to documents page: {documents_url}")
            driver.get(documents_url)

            try:
                # Wait for documents page to load
                wait.until(EC.presence_of_element_located((By.XPATH, case_title_xpath)))
                documents_soup = BeautifulSoup(driver.page_source, "html.parser")

                # Extract Document Detail URLs
                document_urls = []

                # Find the document list container
                doc_list = documents_soup.find("ul", class_="soi-icc-card-list")

                if not doc_list:
                    print("Warning: Could not find document list container")

                    # As a fallback, try to find all document links on the page
                    all_links = documents_soup.find_all(
                        "a", href=lambda href: href and "/documents/" in href
                    )
                    if all_links:
                        print(
                            f"Found {len(all_links)} document links using fallback method"
                        )

                        for link in all_links:
                            href = link.get("href")
                            if href:
                                doc_url = (
                                    f"{self.BASE_URL}{href}"
                                    if href.startswith("/")
                                    else href
                                )
                                document_urls.append(doc_url)
                else:
                    # Find all list items with document links
                    doc_items = doc_list.find_all("li", class_="soi-icc-card-list-item")
                    print(f"Found {len(doc_items)} document items in the list")

                    for item in doc_items:
                        # Find the link within the card body
                        link = item.find("h4").find("a") if item.find("h4") else None

                        if link and link.get("href"):
                            href = link.get("href")
                            doc_url = (
                                f"{self.BASE_URL}{href}"
                                if href.startswith("/")
                                else href
                            )
                            document_urls.append(doc_url)

                intermediate_result["document_detail_urls"] = list(set(document_urls))
                print(
                    f"Found {len(intermediate_result['document_detail_urls'])} document URLs for {data.case_number}."
                )
            except TimeoutException:
                print(f"Warning: Timeout while loading documents page: {documents_url}")

            # Navigate to Service List page
            service_list_url = f"{data.case_url}/service-list"
            print(f"Navigating to service list page: {service_list_url}")
            driver.get(service_list_url)

            try:
                # Wait for service list page to load
                wait.until(EC.presence_of_element_located((By.XPATH, case_title_xpath)))
                # Store the service list HTML
                intermediate_result["raw_service_list_html"] = driver.page_source
            except TimeoutException:
                print(
                    f"Warning: Timeout while loading service list page: {service_list_url}"
                )

            # Navigate to Schedule page
            schedule_url = f"{data.case_url}/schedule"
            print(f"Navigating to schedule page: {schedule_url}")
            driver.get(schedule_url)

            try:
                # Wait for schedule page to load
                wait.until(EC.presence_of_element_located((By.XPATH, case_title_xpath)))
                # Store the schedule HTML
                intermediate_result["raw_schedule_html"] = driver.page_source
            except TimeoutException:
                print(f"Warning: Timeout while loading schedule page: {schedule_url}")

            return intermediate_result

        except Exception as e:
            print(f"Error during filing_data_intermediate: {e}")
            return {"error": str(e)}
        finally:
            self._close_driver(driver)

    def filing_data_from_intermediate(
        self, intermediate: Dict[str, Any]
    ) -> List[ILICCFilingData]:
        """Convert intermediate data to filing data objects."""
        if "error" in intermediate:
            print(f"Error in intermediate data: {intermediate['error']}")
            return []

        filings: List[ILICCFilingData] = []

        # Process the case details
        if "raw_case_page_html" in intermediate:
            case_soup = BeautifulSoup(intermediate["raw_case_page_html"], "html.parser")
            case_details = self._parse_case_details_from_soup(case_soup, intermediate)
            if case_details:
                intermediate["case_details"] = case_details

        # Process the docket sheet
        if "raw_docket_sheet_html" in intermediate:
            docket_soup = BeautifulSoup(
                intermediate["raw_docket_sheet_html"], "html.parser"
            )
            docket_entries = self._parse_docket_sheet_from_soup(docket_soup)
            intermediate["docket_sheet"] = docket_entries

        # Process the service list
        if "raw_service_list_html" in intermediate:
            service_soup = BeautifulSoup(
                intermediate["raw_service_list_html"], "html.parser"
            )
            service_entries = self._parse_service_list_from_soup(service_soup)
            intermediate["service_list"] = service_entries

        # Process the schedule
        if "raw_schedule_html" in intermediate:
            schedule_soup = BeautifulSoup(
                intermediate["raw_schedule_html"], "html.parser"
            )
            schedule_entries = self._parse_schedule_from_soup(schedule_soup)
            intermediate["schedule"] = schedule_entries

        # Process document detail URLs if available
        if (
            "document_detail_urls" in intermediate
            and intermediate["document_detail_urls"]
        ):
            document_urls = intermediate["document_detail_urls"]
            print(f"Processing {len(document_urls)} document URLs")

            # Get a driver for document scraping
            driver = self._get_driver()
            try:
                documents = []
                from selenium.webdriver.common.by import By
                from selenium.webdriver.support import expected_conditions as EC
                from selenium.webdriver.support.ui import WebDriverWait

                # Process a limited number of documents if MAX_DOCUMENTS is set
                if self.MAX_DOCUMENTS > 0:
                    document_urls = document_urls[: self.MAX_DOCUMENTS]
                    print(f"Limiting to {self.MAX_DOCUMENTS} documents")

                for doc_url in document_urls:
                    try:
                        print(f"Retrieving document page: {doc_url}")
                        driver.get(doc_url)
                        wait = WebDriverWait(driver, 20)

                        # Wait for document page to load
                        wait.until(EC.presence_of_element_located((By.XPATH, "//h1")))

                        # Parse document details
                        doc_soup = BeautifulSoup(driver.page_source, "html.parser")
                        doc_data = self._parse_document_details_from_soup(
                            doc_soup, doc_url
                        )

                        if doc_data:
                            documents.append(doc_data)

                    except Exception as e:
                        print(f"Error processing document {doc_url}: {e}")
                        continue

                intermediate["documents"] = documents

            except Exception as e:
                print(f"Error during document processing: {e}")
            finally:
                self._close_driver(driver)

        # Convert intermediate data to filing data objects
        for doc in intermediate.get("documents", []):
            filing = ILICCFilingData(
                case_id=intermediate["case_id"],
                filing_date=doc.get("date_filed", ""),
                filing_type=doc.get("type", ""),
                filing_party=doc.get("filed_by", ""),
                filing_description=doc.get("description", ""),
                filing_documents=[doc],
            )
            filings.append(filing)

        return filings

    def updated_cases_since_date_intermediate(self, after_date: date) -> Dict[str, Any]:
        """Get intermediate data for cases updated after the given date.

        Args:
            after_date: Date to filter cases filed after

        Returns:
            Dict containing intermediate data for cases filed after the given date
        """
        # Use the existing universal_caselist_intermediate method with date filtering
        return self.universal_caselist_intermediate(
            service_types="all", after_date=after_date
        )

    def updated_cases_since_date_from_intermediate(
        self, intermediate: Dict[str, Any], after_date: date
    ) -> List[ILICCCaseData]:
        """Convert intermediate data to case data objects for updated cases.

        Args:
            intermediate: Intermediate data containing case information
            after_date: Date to filter cases filed after

        Returns:
            List of case data objects for cases filed after the given date
        """
        # Use the existing universal_caselist_from_intermediate method
        cases = self.universal_caselist_from_intermediate(intermediate)

        # Filter cases to ensure they're after the given date
        filtered_cases = []
        for case in cases:
            if case.case_details and case.case_details.filing_date:
                try:
                    case_date = datetime.strptime(
                        case.case_details.filing_date, "%m/%d/%Y"
                    ).date()
                    if case_date >= after_date:
                        filtered_cases.append(case)
                except ValueError:
                    # Skip cases with invalid dates
                    continue

        return filtered_cases

    def into_generic_case_data(self, state_data: ILICCCaseData) -> GenericCase:
        """Convert Illinois case data to generic case format."""
        extra_metadata = {
            "illinois_specific": {
                "case_category": state_data.category,
                "service_list": [
                    entry.model_dump() for entry in state_data.service_list
                ],
                "schedule": [entry.model_dump() for entry in state_data.schedule],
                "documents": [doc.model_dump() for doc in state_data.documents],
                "docket_sheet": [
                    entry.model_dump() for entry in state_data.docket_sheet
                ],
            }
        }

        if state_data.case_details:
            extra_metadata["illinois_specific"].update(
                {
                    "case_status": state_data.case_details.status,
                    "judge_names": state_data.case_details.judge_names,
                    "filing_date": state_data.case_details.filing_date,
                }
            )

        parsed_beginning_date = None
        if state_data.case_details is not None:
            intermediate_date = self._parse_date(state_data.case_details.filing_date)
            if intermediate_date is not None:
                parsed_beginning_date = date_to_rfctime(intermediate_date)

        return GenericCase(
            case_number=state_data.case_number,
            case_name=(
                state_data.case_details.title if state_data.case_details else None
            )
            or "",
            case_url=state_data.case_url,
            opened_date=parsed_beginning_date,
            extra_metadata=extra_metadata,
        )

    def into_generic_filing_data(self, state_data: ILICCFilingData) -> GenericFiling:
        """Convert Illinois filing data to generic filing format."""
        extra_metadata = {
            "illinois_specific": {
                "filing_documents": [
                    doc.model_dump() for doc in state_data.filing_documents
                ],
                "document_url": (
                    state_data.filing_documents[0].url
                    if state_data.filing_documents
                    else None
                ),
            }
        }

        return GenericFiling(
            case_number=state_data.case_id,
            filed_date=self._parse_date(state_data.filing_date),
            party_name=state_data.filing_party,
            filing_type=state_data.filing_type,
            description=state_data.filing_description,
            attachments=[],  # Maintain empty list for base model compliance
            extra_metadata=extra_metadata,
        )

    def enrich_filing_data_intermediate(
        self, filing_data: ILICCFilingData
    ) -> Dict[str, Any]:
        """Get additional data for a filing if needed.

        Note: This is primarily used for filings that need to fetch attachments
        from a separate page. For Illinois, this data is already included in the
        filing_data_intermediate method.

        Args:
            filing_data: Filing data to enrich

        Returns:
            Dictionary containing additional data for the filing
        """
        # For Illinois, we already fetch document details in filing_data_intermediate
        # so this method just returns an empty dict
        return {}

    def enrich_filing_data_from_intermediate_intermediate(
        self, filing_data: ILICCFilingData, intermediate: Dict[str, Any]
    ) -> ILICCFilingData:
        """Process additional filing data from intermediate representation.

        Note: Since we don't need to enrich Illinois filings with additional data,
        this method simply returns the original filing data.

        Args:
            filing_data: Original filing data
            intermediate: Intermediate data from enrich_filing_data_intermediate

        Returns:
            Enriched filing data or original if no enrichment needed
        """
        # For Illinois, we don't need to enrich the filing data
        return filing_data

    def _parse_date(self, date_str: str) -> Optional[date]:
        """Parse date string into date object."""
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str, "%m/%d/%Y").date()
        except ValueError:
            return None

    # ... (rest of the helper methods remain unchanged)
