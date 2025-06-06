Take both of these segments of code 
```py
{% if not schemas %}
{{ raise("Schemas content is required but was undefined or empty") }}
{% else %}
{{ schemas }}
{% endif %}
{% if not adapters %}
{{ raise("Adapters content is required but was undefined or empty") }}
{% else %}
{{ adapters }}
{% endif %}
```
and
```py
{% if not scrapers %}
{{ raise("Scrapers content is required but was undefined or empty") }}
{% else %}
{{ scrapers }}
{% endif %}
```
And combine them into a single abstract class following this format 

```py
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
```

The script you output will be directly fed directly outputed and inputed into a .py file to be ran. Try to make sure it works! All the generic cases filings and datatypes as welll as the GenericScraper classwill be imported at the top of the file. In your response you should include properly formatted:
- Scraper Specific Schemas 
- A class instance with all the scraping logic built in.
If any of the methods are missing, make sure to include them as a method that takes in the proper data and just runs a `raise Exception("Not Implemented")`

Your code will be directly fed into a python script with extra import statements at the top so just return the python in a single code block and nothing else.
