from abc import ABC, abstractmethod
import json
from pathlib import Path
from typing import Any, Dict, Generic, TypeVar, List, Type
from datetime import date, datetime, timezone
from pydantic import BaseModel

from openpuc_scrapers.models.filing import GenericFiling as GenericFilingData
from openpuc_scrapers.models.case import GenericCase as GenericCaseData
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
def into_generic_case_data(self, state_data: StateCaseData) -> GenericCaseData:
def into_generic_filing_data(self, state_data: StateFilingData) -> GenericFilingData:
```


The intermediate objects must be JSON-serializable (Dict[str,Any]). Each intermediate output must be parsable by its corresponding from_intermediate method:

- universal_caselist_intermediate() → universal_caselist_from_intermediate()
- filing_data_intermediate() → filing_data_from_intermediate()
- updated_cases_since_date_intermediate() → updated_cases_since_date_from_intermediate()
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
