Implementing new PUC scrapers
=============================

This guide explains how to implement a new scraper for collecting public utility commission case data using the ``AbstractScraper`` base class.

Base Class Overview
---------------------

All scrapers must inherit from ``AbstractScraper`` and implement two required methods:

1. ``get_all_cases()`` - Retrieves a list of all available cases
2. ``get_case_details(case)`` - Retrieves detailed information for a specific case

Scrapers should use the data models provided in the ``openpuc_scrapers.models`` module to represent cases, filings, and attachments. See the :doc:`datamodels` documentation for more details.

Implementation Requirements
----------------------------

To create a new scraper:

1. Create a new class inheriting from ``AbstractScraper``::

    from .base import AbstractScraper
    from ..models import Case, Filing, Attachment

    class NewStatePUC(AbstractScraper):
        """Interface for interacting with and parsing {State} PUC data."""

2. Implement the required abstract methods::

    def get_all_cases(self) -> list[Case]:
        """Retrieve a list of all available cases."""
        # Implementation here
        
    def get_case_details(self, case: Case) -> Case:
        """Retrieve details for a specific case."""
        # Implementation here


Example Implementation
-----------------------

Here's a simplified example showing the key components of a scraper implementation::

    class NewStatePUC(AbstractScraper):
        def get_all_cases(self) -> list[Case]:
            # Fetch list of cases from website
            response = requests.get(self._get_cases_url())
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "html.parser")
            cases = []
            
            for case_element in soup.find_all("div", class_="case"):
                case = Case(
                    case_number=case_element.find("span", class_="number").text,
                    description=case_element.find("span", class_="description").text
                )
                cases.append(case)
                
            return cases
            
        def get_case_details(self, case: Case) -> Case:
            # Fetch case details
            response = requests.get(self._get_case_url(case.case_number))
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Update case details
            case = self._parse_case_details(soup, case)
            
            # Get filings
            case.filings = self._parse_filings(soup, case)
            
            return case
            
        def _get_case_url(self, case_number: str) -> str:
            return f"https://example.com/cases/{case_number}"
            
        def _parse_case_details(self, soup: BeautifulSoup, case: Case) -> Case:
            # Extract and clean case details
            # WARNING: you'll probably need to do some data santization first!
            case.case_type = soup.find("input", id="type")["value"]
            case.description = " ".join(
                soup.find("textarea", id="description").text.split()
            )
            return case
            
        def _parse_filings(self, soup: BeautifulSoup, case: Case) -> list[Filing]:
            filings = []
            for filing_div in soup.find_all("div", class_="filing"):
                # WARNING: you'll probably need to do some data santization first!
                filing = Filing(
                    filed_date=datetime.strptime(
                        filing_div.find("span", class_="date").text,
                        "%m/%d/%Y"
                    ).date(),
                    party_name=filing_div.find("span", class_="party").text,
                    filing_type=filing_div.find("span", class_="type").text,
                    description=filing_div.find("div", class_="description").text
                )
                filings.append(filing)
            return filings

Testing Your Implementation
---------------------------

When implementing a new scraper:

1. Test the ``get_all_cases()`` method to ensure it returns valid Case objects
2. Test the ``get_case_details()`` method with various case numbers
3. Verify all required fields are properly populated
4. Check data sanitization and normalization
5. Verify proper error handling for invalid cases or network issues
6. Test handling of edge cases (empty fields, unusual characters, etc.)

Common Challenges
------------------

- **Website Structure Changes**: Design your parsing code to be resilient to minor HTML changes
- **Inconsistent Data**: Handle variations in date formats, field names, and data quality
- **Error Handling**: Implement robust error handling for network issues and invalid data
- **Data Sanitization**: Clean and normalize data to ensure consistency and accuracy
- **Pagination**: Implement pagination support if cases are spread across multiple pages
- **Rate Limiting**: Respect website rate limits and implement appropriate delays
