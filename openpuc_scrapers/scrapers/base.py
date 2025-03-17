from abc import ABC, abstractmethod

from ..models.case import GenericCase


class AbstractScraper(ABC):
    """Abstract base class for state PUC scrapers.

    This class defines the required methods for any scraper implementation to interact
    with state Public Utility Commission (PUC) websites and retrieve case information.

    Methods:
        get_all_cases() -> list[Case]:
            Retrieve a list of all available cases.
        get_case_details(case: GenericCase) -> GenericCase:
            Retrieve detailed information for a specific case, including filings and
            attachments.
    """

    @abstractmethod
    def get_all_cases(self) -> list[Case]:
        """Retrieve a list of all available cases.

        Returns:
            list[Case]: A list of all cases.
        """
        pass

    @abstractmethod
    def get_case_details(self, case: GenericCase) -> GenericCase:
        """Retrieve details for a specific case, including filings and attachments.

        Modifies the case object in place with the details retrieved from the website.

        Args:
            case (Case): The case object to retrieve details for.

        Returns:
            - The detailed case object with all fields populated, including filings and
              attachments.

        Raises:
            requests.HTTPError: If the request to the website fails.
        """
        pass
