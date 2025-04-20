from datetime import date, datetime
from typing import Any, Dict, List
from pydantic import BaseModel
from random import randint, choice
from faker import Faker

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
    document_type: str = "filing"


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
                    url=f"https://dummy.com/docs/{randint(1000,9999)}.pdf",
                ),
            ],
        )

    def universal_caselist_intermediate(self) -> Dict[str, Any]:
        return {"cases": [self._generate_dummy_case().model_dump() for _ in range(10)]}

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
                GenericAttachment(name=a.document_title, url=a.url)
                for a in state_data.attachments
            ],
            extra_metadata={"filing_id": state_data.filing_id},
        )
