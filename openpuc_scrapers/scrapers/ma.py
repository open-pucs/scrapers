import requests
from bs4 import BeautifulSoup
from datetime import datetime
import unicodedata

from .base import AbstractScraper
from ..models import Case, Filing, Attachment


class MassachusettsDPU(AbstractScraper):
    """Interface for interacting with and parsing Massachusetts DPU data."""

    def get_all_cases(self) -> list[Case]:
        """Retrieve a list of all available cases.

        Returns:
            list[Case]: A list of all cases.
        """
        raise NotImplementedError

    def get_case_details(self, case: Case) -> Case:
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
        request_url = self._get_case_url(case.case_number)
        response = requests.get(request_url)
        response.raise_for_status()

        # Parse the webpage
        soup = BeautifulSoup(response.text, "html.parser")

        # Extract case details from the response
        case = self._parse_case_details(soup, case)

        # Get all filings for the case based on the parsed webpage
        case.filings = self._parse_filings(soup, case)

        return case

    def _get_case_url(self, case_number: str):
        """Get the URL for a case.

        Args:
            case_number (str): The case number.

        Returns:
            str: The URL for the case.
        """
        return f"https://eeaonline.eea.state.ma.us/DPU/Fileroom/dockets/get/?number={case_number}&edit=false"

    def _parse_case_details(self, soup: BeautifulSoup, case: Case) -> Case:
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

    def _parse_filings(self, soup: BeautifulSoup, case: Case) -> list[Filing]:
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
            filing = Filing(
                filed_date=filed_date,
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
                    Attachment(
                        name=attachment["name"],
                        url=attachment["url"],
                    )
                )

            # Add the filing to the case
            filings.append(filing)

        return filings
