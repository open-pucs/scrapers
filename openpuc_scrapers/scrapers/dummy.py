from datetime import date, datetime
from typing import Any, Dict, List
from pydantic import BaseModel
from random import randint, choice
from faker import Faker
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from openpuc_scrapers.models.attachment import GenericAttachment
from openpuc_scrapers.models.case import GenericCase
from openpuc_scrapers.models.filing import GenericFiling
from openpuc_scrapers.models.timestamp import RFC3339Time, date_to_rfctime
from openpuc_scrapers.scrapers.base import GenericScraper

fake = Faker()


class DummyAttachment(BaseModel):
    document_title: str
    url: str
    file_format: str = "pdf"
    document_extension: str = "filing"


class DummyFilingData(BaseModel):
    filing_id: str
    case_number: str
    date_filed: RFC3339Time
    description: str
    attachments: List[DummyAttachment] = []
    filing_type: str = "test_filing"


class DummyCaseData(BaseModel):
    case_number: str
    description: str
    opened_date: RFC3339Time
    status: str = "open"
    industry: str = "utilities"


def test_selenium_connection() -> bool:
    """Test Selenium connectivity with enhanced error handling"""
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--remote-debugging-port=9222")

    try:
        driver = webdriver.Chrome(options=options)
        driver.get("https://www.google.com")
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "q")))
        driver.quit()
        return True
    except Exception as e:
        print(f"Selenium error: {str(e)}")
        try:
            driver.quit()
        except Exception:
            pass
        return False


class DummyScraper(GenericScraper[DummyCaseData, DummyFilingData]):
    state: str = "dummy"
    jurisdiction_name: str = "dummy_puc"

    def _generate_dummy_case(self) -> DummyCaseData:
        return DummyCaseData(
            case_number=f"DUMMY-{randint(1000, 9999)}",
            description=fake.sentence(),
            opened_date=date_to_rfctime(fake.date_this_decade()),
        )

    def _generate_dummy_filing(self, case: DummyCaseData) -> DummyFilingData:
        return DummyFilingData(
            filing_id=f"FILING-{randint(10000, 99999)}",
            case_number=case.case_number,
            date_filed=date_to_rfctime(fake.date_this_year()),
            description=fake.sentence(),
            attachments=[
                DummyAttachment(
                    document_title=fake.catch_phrase(),
                    # url=f"https://dummy.com/docs/{randint(1000,9999)}.pdf",
                    url="https://www.adobe.com/support/products/enterprise/knowledgecenter/media/c4611_sample_explain.pdf",
                    document_extension="pdf",
                ),
            ],
        )

    def universal_caselist_intermediate(self) -> Dict[str, Any]:
        """Include Selenium connectivity test results with dummy data"""
        selenium_works = test_selenium_connection()
        # selenium_works = False
        return {
            "cases": [self._generate_dummy_case().model_dump() for _ in range(10)],
            "selenium_test": {
                "success": selenium_works,
                "message": (
                    "Successfully connected to google.com"
                    if selenium_works
                    else "Failed Selenium connection test"
                ),
            },
        }

    def universal_caselist_from_intermediate(
        self, intermediate: Dict[str, Any]
    ) -> List[DummyCaseData]:
        return [DummyCaseData(**c) for c in intermediate["cases"]]

    def filing_data_intermediate(self, data: DummyCaseData) -> Dict[str, Any]:
        return {
            "case": data.model_dump(),
            "filings": [
                self._generate_dummy_filing(data).model_dump()
                for _ in range(randint(1, 5))
            ],
        }

    def filing_data_from_intermediate(
        self, intermediate: Dict[str, Any]
    ) -> List[DummyFilingData]:
        return [DummyFilingData(**f) for f in intermediate["filings"]]

    def updated_cases_since_date_intermediate(self, after_date: date) -> Dict[str, Any]:
        return self.universal_caselist_intermediate()

    def updated_cases_since_date_from_intermediate(
        self, intermediate: Dict[str, Any], after_date: date
    ) -> List[DummyCaseData]:
        return [
            c
            for c in self.universal_caselist_from_intermediate(intermediate)
            if c.opened_date > after_date
        ]

    def enrich_filing_data_intermediate(
        self, filing_data: DummyFilingData
    ) -> Dict[str, Any]:
        return {}

    def enrich_filing_data_from_intermediate_intermediate(
        self, filing_data: DummyFilingData, intermediate: Dict[str, Any]
    ) -> DummyFilingData:
        return filing_data

    def into_generic_case_data(self, state_data: DummyCaseData) -> GenericCase:
        return GenericCase(
            case_number=state_data.case_number,
            case_type="dummy_case",
            description=state_data.description,
            industry=state_data.industry,
            opened_date=date_to_rfctime(state_data.opened_date),
            extra_metadata={"status": state_data.status},
        )

    def into_generic_filing_data(self, state_data: DummyFilingData) -> GenericFiling:
        return GenericFiling(
            party_name="",
            filed_date=date_to_rfctime(state_data.date_filed),
            filing_type=state_data.filing_type,
            description=state_data.description,
            attachments=[
                GenericAttachment(
                    name=a.document_title,
                    url=a.url,
                    document_extension=a.document_extension,
                )
                for a in state_data.attachments
            ],
            extra_metadata={"filing_id": state_data.filing_id},
        )
