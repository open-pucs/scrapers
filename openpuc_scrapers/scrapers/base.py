from abc import ABC, abstractmethod
import json
from pathlib import Path
from typing import Any, Dict, Generic, TypeVar, List, Type
from datetime import date, datetime, timezone
from pydantic import BaseModel

from openpuc_scrapers.models.filing import GenericFiling
from openpuc_scrapers.models.case import GenericCase
from openpuc_scrapers.models.misc import (
    RequestData,
    post_list_to_endpoint_split,
)


"""
To create a New State Specific Scraper.

1. Go ahead and define two types related to the data you want to scrape. StateCaseData, StateFilingData.

2. Create a new class with name <StateName>Scraper

To create a New State Specific Scraper, implement three main functionalities:

1. Universal Case List: Get a list of all cases in the system
2. Filing Data: Get detailed filing data for a specific case
3. Updated Cases: Get cases that have been updated since a given date

Each functionality requires two steps due to saving JSON-serializable intermediates to disk:

1. Universal Case List Steps:
   ```python
   def universal_caselist_intermediate(self) -> Dict[str, Any]:
   def universal_caselist_from_intermediate(self, intermediate: Dict[str, Any]) -> List[StateCaseData]:
   ```

2. Filing Data Steps:
   ```python
   def filing_data_intermediate(self, data: StateCaseData) -> Dict[str, Any]:
   def filing_data_from_intermediate(self, intermediate: Dict[str, Any]) -> List[StateFilingData]:
   ```

3. Updated Cases Steps:
   ```python
   def updated_cases_since_date_intermediate(self, after_date: date) -> Dict[str, Any]:
   
   def updated_cases_since_date_from_intermediate(self, intermediate: Dict[str, Any], after_date: date) -> List[StateCaseData]:
   ```

Additionally, implement conversion methods to transform state-specific types into generic types:

```python
def into_generic_case_data(self, state_data: StateCaseData) -> GenericCase:
def into_generic_filing_data(self, state_data: StateFilingData) -> GenericFiling:
```


The intermediate objects must be JSON-serializable (Dict[str,Any]). Each intermediate output must be parsable by its corresponding from_intermediate method:

- universal_caselist_intermediate() → universal_caselist_from_intermediate()
- filing_data_intermediate() → filing_data_from_intermediate()
- updated_cases_since_date_intermediate() → updated_cases_since_date_from_intermediate()

# Extra Steps to Support Attachment Fetching 

Typically these PUC's and other goverment websites will have two different methodologies for dealing with dockets either:

1. Displaying a list of all attachments, and having the combined filing be accesible through a single "filing_id" field.
2. Display a list of all filings, and give each filing a subpage. 

If you have a docket in case 1 for example NY, CO and CA, then 

- Implement deduplication in the filing_data_from_intermediate() method, and only return a list of filing data with all the attachments deduplicated. 

Likewise if you have a docket where all attachments are seperate.

- When implementing filing_data_intermediate() method, for each filing return a StateFiling with the attachements as well as any other data missing.
- Implement the two optional methods 
  - enrich_filing_data_intermediate() that will take info from an incomplete filing data, go to the filing page, and get the raw html/json and return it as a Dict[str,Any]
  - enrich_filing_data_from_intermediate_intermediate() that will take that intermediate representation, and the original incomplete filing data, and return a complete one with all the attachments. 

Both of those methods have default definitions that do nothing and just pass the StateFilingData through unchanged, so you can implement these steps in the data pipeline for all cases, and they will only actually be utilized for dockets that need them.
"""


StateCaseData = TypeVar("StateCaseData", bound=BaseModel)
StateFilingData = TypeVar("StateFilingData", bound=BaseModel)


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

    @abstractmethod
    def enrich_filing_data_intermediate(
        self, filing_data: StateFilingData
    ) -> Dict[str, Any]:
        return {}

    @abstractmethod
    def enrich_filing_data_from_intermediate_intermediate(
        self, filing_data: StateFilingData, intermediate: Dict[str, Any]
    ) -> StateFilingData:
        return filing_data

    # Conversion methods to generic types
    @abstractmethod
    def into_generic_case_data(self, state_data: StateCaseData) -> GenericCase:
        """Convert state-specific case data to generic format"""
        pass

    @abstractmethod
    def into_generic_filing_data(self, state_data: StateFilingData) -> GenericFiling:
        """Convert state-specific filing data to generic format"""
        pass
