from typing import Any, Dict, List
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import unicodedata

from openpuc_scrapers.models.timestamp import (
    RFC3339Time,
    date_to_rfctime,
    to_rfc339_time,
)
from openpuc_scrapers.scrapers.base import GenericScraper


from ..models import GenericCase, GenericFiling, GenericAttachment


class MassachusettsDPUScraper(GenericScraper[GenericCase, GenericFiling]):
    state: str = "ma"
    jurisdiction_name: str = "ma_puc"
    """Interface for interacting with and parsing Massachusetts DPU data."""

    def universal_caselist_intermediate(self) -> Dict[str, Any]:
        """Capture industry page HTML as intermediate data"""
        intermediates = {}
        for industry in self.INDUSTRIES:
            response = requests.get(self._get_case_list_url(industry))
            response.raise_for_status()
            intermediates[industry] = response.text
        return intermediates

    def universal_caselist_from_intermediate(
        self, intermediate: Dict[str, Any]
    ) -> List[GenericCase]:
        """Convert HTML intermediates to GenericCase objects"""
        cases = []
        for industry, html in intermediate.items():
            soup = BeautifulSoup(html, "html.parser")
            cases.extend(self._parse_case_list(soup, industry))
        return cases

    def filing_data_intermediate(self, data: GenericCase) -> Dict[str, Any]:
        """Capture case details HTML as intermediate"""
        response = requests.get(self._get_case_details_url(data.docket_govid))
        response.raise_for_status()
        return {
            "docket_govid": data.docket_govid,
            "html": response.text,
            "existing_case": data.model_dump(),
        }

    def filing_data_from_intermediate(
        self, intermediate: Dict[str, Any]
    ) -> List[GenericFiling]:
        """Convert HTML intermediate to GenericFiling objects"""
        soup = BeautifulSoup(intermediate["html"], "html.parser")
        return self._parse_filings(soup, GenericCase(**intermediate["existing_case"]))

    def updated_cases_since_date_intermediate(
        self, after_date: RFC3339Time
    ) -> Dict[str, Any]:
        raise NotImplementedError(
            "Massachusetts DPU website doesn't support date-based filtering"
        )

    def updated_cases_since_date_from_intermediate(
        self, intermediate: Dict[str, Any], after_date: RFC3339Time
    ) -> List[GenericCase]:
        raise NotImplementedError(
            "Massachusetts DPU website doesn't support date-based filtering"
        )

    def enrich_filing_data_intermediate(
        self, filing_data: GenericFiling
    ) -> Dict[str, Any]:
        """No enrichment needed - filings contain all data upfront"""
        return {}

    def enrich_filing_data_from_intermediate_intermediate(
        self, filing_data: GenericFiling, intermediate: Dict[str, Any]
    ) -> GenericFiling:
        """No enrichment needed - return original data"""
        return filing_data

    def into_generic_case_data(self, state_data: GenericCase) -> GenericCase:
        """Identity converter since we already use GenericCase"""
        return state_data

    def into_generic_filing_data(self, state_data: GenericFiling) -> GenericFiling:
        """Identity converter since we already use GenericFiling"""
        return state_data

    INDUSTRIES = [
        "CONS ADJ",
        "Dig Safe",
        "EFSB",
        "Electric",
        "FERC",
        "Gas",
        "PIPELINE",
        "RATES",
        "RULEMAKING",
        "Siting/DTE",
        "Transportation",
        "Water",
    ]

    def get_all_cases(self) -> List[GenericCase]:
        """Retrieve a list of all available cases.

        Returns:
            List[GenericCase]: A list of all cases.
        """
        cases = []
        for industry in self.INDUSTRIES:
            cases.extend(self._get_all_cases_for_industry(industry))

        return cases

    def _get_all_cases_for_industry(self, industry: str) -> List[GenericCase]:
        """Retrieve a list of all available cases for a specific industry.

        Args:
            industry (str): The industry to retrieve cases for.

        Returns:
            List[GenericCase]: A list of all cases for the specified industry.
        """
        # Query the website for the case list
        request_url = self._get_case_list_url(industry)
        response = requests.get(request_url)
        response.raise_for_status()

        # Parse the webpage
        soup = BeautifulSoup(response.text, "html.parser")

        return self._parse_case_list(soup)

    def _get_case_list_url(self, industry: str):
        """Get the URL for a case.

        Args:
            docket_govid (str): The case number.

        Returns:
            str: The URL for the case.
        """
        return f"https://eeaonline.eea.state.ma.us/DPU/Fileroom//Dockets/GetByIndustry/?type={industry}"

    def _parse_case_list(self, soup: BeautifulSoup) -> List[GenericCase]:
        """Parse the case list from the webpage.

        Args:
            soup (BeautifulSoup): The parsed webpage.

        Returns:
            - A list of cases.
        """
        cases: List[GenericCase] = []
        table = soup.find("table", class_="DocketList")
        if not table:
            return cases

        # Skip header row
        for row in table.find_all("tr")[1:]:  # type: ignore
            cells = row.find_all("td")
            if len(cells) < 7:
                continue

            # Extract date if present
            date_str = cells[6].get_text(strip=True)
            opened_date = None
            if date_str:
                try:
                    opened_date = datetime.strptime(date_str, "%m/%d/%Y").date()
                except ValueError:
                    opened_date = None
            if opened_date is not None:
                opened_date = date_to_rfctime(opened_date)

            case = GenericCase(
                docket_govid=cells[0].get_text(strip=True),
                case_type=cells[1].get_text(strip=True) or None,
                industry=cells[2].get_text(strip=True) or None,
                petitioner=cells[4].get_text(strip=True) or None,
                description=" ".join(cells[5].get_text(strip=True).split()) or None,
                opened_date=opened_date,
                closed_date=None,  # Not provided in the table
                hearing_officer=None,  # Not provided in the table
                filings=[],  # Empty list as specified
            )
            cases.append(case)

        return cases

    def get_case_details(self, case: GenericCase) -> GenericCase:
        """Retrieve details for a specific case, including filings and attachments.

        Modifies the case object in place with the details retrieved from the website.

        Args:
            case (Case): The case object to retrieve details for.

        Returns:
            - The case object with all fields populated, including filings and
              attachments.

        Raises:
            requests.HTTPError: If the request to the website fails.
        """
        # Query the website for the case details
        request_url = self._get_case_details_url(case.docket_govid)
        response = requests.get(request_url)
        response.raise_for_status()

        # Parse the webpage
        soup = BeautifulSoup(response.text, "html.parser")

        # Extract case details from the response
        case = self._parse_case_details(soup, case)

        # Get all filings for the case based on the parsed webpage
        case.filings = self._parse_filings(soup, case)

        return case

    def _get_case_details_url(self, docket_govid: str):
        """Get the URL for a case.

        Args:
            docket_govid (str): The case number.

        Returns:
            str: The URL for the case.
        """
        return f"https://eeaonline.eea.state.ma.us/DPU/Fileroom/dockets/get/?number={docket_govid}&edit=false"

    def _parse_case_details(
        self, soup: BeautifulSoup, case: GenericCase
    ) -> GenericCase:
        """Parse the case details from the webpage and update the case object.

        Modifies the case object in place with the details from the parsed webpage.

        Args:
            soup (BeautifulSoup): The parsed webpage.
            case (Case): The case object to update.
        """
        case_type = soup.find("input", {"id": "CaseType"})["value"]  # type: ignore
        industry = soup.find("input", {"id": "Industry"})["value"]  # type: ignore
        description = soup.find("textarea", {"id": "CaseCaption"}).text  # type: ignore
        petitioner = soup.find("input", {"id": "Petitioner"})["value"]  # type: ignore
        hearing_officer = soup.find("input", {"id": "HearingOfficer_DisplayName"})[  # type: ignore
            "value"
        ]
        opened_date = soup.find("input", {"id": "DateFiled"})["value"]  # type: ignore
        closed_date = soup.find("input", {"id": "DateClosed"})["value"]  # type: ignore

        # Sanitize some inputs
        description = " ".join(description.split())

        # Update the case in the database with the details
        case.case_type = case_type
        case.industry = industry
        case.description = description
        case.petitioner = petitioner
        case.hearing_officer = hearing_officer
        if opened_date != "":
            case.opened_date = datetime.strptime(opened_date, "%m/%d/%Y").date()
        if closed_date != "":
            case.closed_date = datetime.strptime(closed_date, "%m/%d/%Y").date()

        return case

    def _parse_filings(
        self, soup: BeautifulSoup, case: GenericCase
    ) -> list[GenericFiling]:
        """Parse the filings from the webpage.

        Args:
            soup (BeautifulSoup): The parsed webpage.
            case (Case): The case object to associate the filings with.

        Returns:
            - A list of filings.
        """
        # Find all divGridRow elements within the div with ID filingsTab
        filing_divs = soup.find("div", id="filingsTab").find_all(  # type: ignore
            "div", class_="divGridRow"
        )

        # Create new filings and attachments for each filing
        filings = []
        for filing_div in filing_divs:
            created = filing_div.find("span", class_="created").text.strip()
            filer = filing_div.find("span", class_="filer").text.strip()
            filing_type = filing_div.find("span", class_="filingtype").text.strip()
            description = filing_div.find("div", class_="description").text.strip()

            # Remove line breaks in the fields (any newline followed by spaces
            # should be replaced with a single space)
            description = " ".join(description.split())
            filer = " ".join(filer.split())
            filing_type = " ".join(filing_type.split())

            # Parse date
            filed_date = datetime.strptime(created, "%m/%d/%Y").date()

            # Sanitize the description field
            description = unicodedata.normalize("NFKD", description)

            # Switch fancy apostrophes for normal ones
            description = description.replace("’", "'")

            # Create the filing if it doesn't already exist
            filing = GenericFiling(
                filed_date=date_to_rfctime(filed_date),
                party_name=filer,
                filing_type=filing_type,
                description=description,
            )

            # Parse and create all associated file objects
            # (leave the full text blank for now)

            # Collect all links
            attachment_div = filing_div.find(
                "div", id=lambda x: x and x.startswith("files_")
            )
            attachment_data = [
                {"name": a.text.strip(), "url": a["href"]}
                for a in attachment_div.find_all("a")
            ]
            filing.attachments = []
            for attachment in attachment_data:
                filing.attachments.append(
                    GenericAttachment(
                        name=attachment["name"],
                        url=attachment["url"],
                    )
                )

            # Add the filing to the case
            filings.append(filing)

        return filings
