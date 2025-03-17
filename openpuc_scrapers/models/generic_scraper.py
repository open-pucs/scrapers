from abc import ABC, abstractmethod
import json
from pathlib import Path
from typing import Any, Dict, Generic, TypeVar, List, Type
from datetime import date, datetime, timezone
from pydantic import BaseModel

from openpuc_scrapers.models.filing import GenericFiling as GenericFilingData
from openpuc_scrapers.models.case import GenericCase as GenericCaseData

# this is cursed yoooo
StateCaseData = TypeVar("StateCaseData", bound=BaseModel)
StateFilingData = TypeVar("StateFilingData", bound=BaseModel)


"""
With this implementation the intermediate objects are designed to be easily json serializeable with type Dict[str,Any]

And this code should type check everything including StateCaseData, StateFilingData, and the conversion to generics from there, when it comes to the intermediates you still need to guarentee that the intermediate vaugely typed objects line up like so 


(universal_caselist_intermediate) output is parsable by (universal_caselist_from_intermediate)

(filing_data_intermediate) output is parsable by (filing_data_from_intermediate)

and 

(updated_cases_since_date_intermediate) output is parsable by (updated_cases_since_date_from_intermediate)
"""


class GenericScraper(ABC, Generic[StateCaseData, StateFilingData]):
    # Universal case list methods
    @abstractmethod
    def universal_caselist_intermediate(self) -> Dict[str, Any]:
        """Return intermediate representation of case list"""
        pass

    @abstractmethod
    def universal_caselist_from_intermediate(
        self, intermediate: Dict[str, Any]
    ) -> List[StateCaseData]:
        """Convert intermediate to state-specific case data objects"""
        pass

    # GenericFiling data methods
    @abstractmethod
    def filing_data_intermediate(self, data: StateCaseData) -> Dict[str, Any]:
        """Serialize case data to intermediate format"""
        pass

    @abstractmethod
    def filing_data_from_intermediate(
        self, intermediate: Dict[str, Any]
    ) -> List[StateFilingData]:
        """Convert intermediate to state-specific filing data objects"""
        pass

    # Updated cases methods
    @abstractmethod
    def updated_cases_since_date_intermediate(self, after_date: date) -> Dict[str, Any]:
        """Get intermediate for cases updated after given date"""
        pass

    @abstractmethod
    def updated_cases_since_date_from_intermediate(
        self, intermediate: Dict[str, Any], after_date: date
    ) -> List[StateCaseData]:
        """Convert intermediate to updated case data objects"""
        pass

    # Conversion methods to generic types
    @abstractmethod
    def into_generic_case_data(self, state_data: StateCaseData) -> GenericCaseData:
        """Convert state-specific case data to generic format"""
        pass

    @abstractmethod
    def into_generic_filing_data(
        self, state_data: StateFilingData
    ) -> GenericFilingData:
        """Convert state-specific filing data to generic format"""
        pass


# Helper functions
def save_to_disk(path: str, content: str) -> None:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")


# isnt working due to the higher order types sadly
# def save_json(path: str, data: BaseModel | List[BaseModel]) -> None:
def save_json(path: str, data: Any) -> None:
    if isinstance(data, list):
        json_data = [item.model_dump() for item in data]
    else:
        json_data = data.model_dump()
    json_str = json.dumps(json_data, indent=2)
    save_to_disk(path, json_str)


# Processing functions
def process_cases(
    scraper: GenericScraper[StateCaseData, StateFilingData],
    cases: List[StateCaseData],
    base_path: str,
) -> List[GenericCaseData]:
    all_generic_cases = []

    for idx, case in enumerate(cases):
        # Save state-specific case data
        case_path = f"{base_path}/cases/case_{idx}.json"
        save_json(case_path, case)

        # Process filings
        filings_html = scraper.filing_data_intermediate(case)
        filings_path = f"{base_path}/filings/case_{idx}.html"
        save_to_disk(filings_path, filings_html)

        filings = scraper.filing_data_from_intermediate(filings_html)
        filings_json_path = f"{base_path}/filings/case_{idx}.json"
        save_json(filings_json_path, filings)

        # Convert to generic case
        generic_case = scraper.into_generic_case_data(case)
        all_generic_cases.append(generic_case)

    return all_generic_cases


def get_all_new_cases(
    scraper: GenericScraper[StateCaseData, StateFilingData]
) -> List[GenericCaseData]:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    base_path = f"data/{timestamp}"

    # Get and save case list
    caselist_html = scraper.universal_caselist_intermediate()
    caselist_path = f"{base_path}/caselist.html"
    save_to_disk(caselist_path, caselist_html)

    # Process cases
    state_cases = scraper.universal_caselist_from_intermediate(caselist_html)
    return process_cases(scraper, state_cases, base_path)


def get_new_cases_since_date(
    scraper: GenericScraper[StateCaseData, StateFilingData], after_date: date
) -> List[GenericCaseData]:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    base_path = f"data/{timestamp}"

    # Get and save updated cases
    updated_html = scraper.updated_cases_since_date_intermediate(after_date)
    updated_path = f"{base_path}/updated_cases.html"
    save_to_disk(updated_path, updated_html)

    # Process updated cases
    state_cases = scraper.updated_cases_since_date_from_intermediate(
        updated_html, after_date
    )
    return process_cases(scraper, state_cases, base_path)


...
