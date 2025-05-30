import logging
from pathlib import Path
from annotated_types import doc
from openpuc_scrapers.db.s3_wrapper import rand_string
from openpuc_scrapers.models.attachment import GenericAttachment
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from pydantic import BaseModel, HttpUrl
from typing import Any, Dict, List, Tuple
import time
from datetime import datetime
from bs4 import BeautifulSoup

from openpuc_scrapers.models.case import GenericCase
from openpuc_scrapers.models.filing import GenericFiling
from openpuc_scrapers.models.timestamp import RFC3339Time, date_to_rfctime
from openpuc_scrapers.scrapers.base import GenericScraper


default_logger = logging.getLogger(__name__)


class UTDOGMAttachment(BaseModel):
    document_title: str = ""
    url: str
    file_format: str = ""
    document_extension: str = ""
    file_name: str = ""


class UTDOGMFiling(BaseModel):
    attachments: List[UTDOGMAttachment] = []
    filing_type: str = ""
    case_number: str = ""
    date_filed: str = ""
    filing_on_behalf_of: str = ""
    description_of_filing: str = ""
    filing_no: str = ""
    filed_by: str = ""
    response_to: str = ""


class UTDOGMDocket(BaseModel):
    case_number: str  # 24-C-0663
    matter_type: str  # Complaint
    matter_subtype: str  # Appeal of an Informal Hearing Decision
    case_title: str  # In the Matter of the Rules and Regulations of the Public Service
    organization: str  # Individual
    date_filed: str
    industry_affected: str
    related_cases: List["UTDOGMDocket"] = []
    party_list: List[str] = []  # List of organizations/parties


class UTDOGMScraper(GenericScraper[UTDOGMDocket, UTDOGMFiling]):
    state: str = "ut"
    jurisdiction_name: str = "ut_dogm"

    def universal_caselist_intermediate(self) -> Dict[str, Any]:
        pass
        # from selenium import webdriver
        # from selenium.webdriver.chrome.options import Options
        #
        # user_data_dir = Path("/tmp/", "selenium-userdir-" + rand_string())
        # user_data_dir.mkdir(parents=True, exist_ok=True)
        #
        # chrome_options = Options()
        # chrome_options.add_argument(f"--user-data-dir={user_data_dir}")
        # chrome_options.add_argument("--headless=new")  # Add headless mode
        # chrome_options.add_argument("--disable-gpu")
        # chrome_options.add_argument("--no-sandbox")
        #
        # def process_industry(industry_num: int) -> Dict[str, Any]:
        #     """Task to process a single industry number and return its dockets"""
        #
        #     driver = webdriver.Chrome(options=chrome_options)
        #
        #     try:
        #         url = f"https://documents.dps.ny.gov/public/Common/SearchResults.aspx?MC=1&IA={industry_num}"
        #         driver.get(url)
        #
        #         wait = WebDriverWait(driver, 300)
        #         industry_elem = wait.until(
        #             EC.presence_of_element_located(
        #                 (By.ID, "GridPlaceHolder_lblSearchCriteriaValue")
        #             )
        #         )
        #         industry_affected = industry_elem.text.replace(
        #             "Industry Affected:", ""
        #         ).strip()
        #         time.sleep(40)
        #
        #         table_elem = wait.until(
        #             EC.presence_of_element_located(
        #                 (By.CSS_SELECTOR, "#tblSearchedMatterExternal > tbody")
        #             )
        #         )
        #         table_html = table_elem.get_attribute("outerHTML") or ""
        #
        #         # Use existing helper function
        #         return {"html": table_html, "industry": industry_affected}
        #
        #     except TimeoutException as e:
        #         print(f"Timeout waiting for industry {industry_num}")
        #         raise e
        #     except Exception as e:
        #         print(f"Error processing industry {industry_num}: {e}")
        #         raise e
        #     finally:
        #         driver.quit()
        #
        # nums = list(range(1, 10))  # Industries end after industry 10: Water.
        # docket_intermediate_lists = [
        #     process_industry(industry_num) for industry_num in nums
        # ]
        # return {"industry_intermediates": docket_intermediate_lists}

    def universal_caselist_from_intermediate(
        self, intermediate: Dict[str, Any]
    ) -> List[UTDOGMDocket]:
        # intermediate_list = intermediate["industry_intermediates"]
        # caselist: List[NYPUCDocket] = []
        # for industry_intermediate in intermediate_list:
        #     assert isinstance(
        #         industry_intermediate, dict
        #     ), f"Industry intermediate must be a dictionary, got {type(industry_intermediate)}"
        #     assert (
        #         "html" in industry_intermediate
        #     ), "Missing 'html' key in industry intermediate"
        #     assert (
        #         "industry" in industry_intermediate
        #     ), "Missing 'industry' key in industry intermediate"
        #     assert isinstance(
        #         industry_intermediate["html"], str
        #     ), "HTML content must be a string"
        #     assert industry_intermediate["html"] != "", "HTML content cannot be empty"
        #     assert isinstance(
        #         industry_intermediate["industry"], str
        #     ), "Industry name must be a string"
        #     assert (
        #         industry_intermediate["industry"] != ""
        #     ), "Industry name cannot be empty"
        #     docket_info = extract_docket_info_from_caselisthtml(industry_intermediate)
        #     caselist.extend(docket_info)
        # return caselist

    def filing_data_intermediate(self, data: UTDOGMDocket) -> Dict[str, Any]:
        """Get HTML content for a docket's filings"""
        return {"docket_id": data.case_number, "html": process_docket(data)}

    def filing_data_from_intermediate(
        self, intermediate: Dict[str, Any]
    ) -> List[UTDOGMFiling]:
        """Convert docket HTML to filing data"""
        assert all(
            key in intermediate for key in ("docket_id", "html")
        ), "Missing required keys in intermediate"
        assert isinstance(intermediate["docket_id"], str), "docket_id must be a string"
        assert isinstance(intermediate["html"], str), "html must be a string"

        docket_id = intermediate["docket_id"]
        html = intermediate["html"]
        return extract_filings_from_dockethtml(html, docket_id)

    def updated_cases_since_date_intermediate(
        self, after_date: RFC3339Time
    ) -> Dict[str, Any]:
        raise Exception("Not Impelemented")

    def updated_cases_since_date_from_intermediate(
        self, intermediate: Dict[str, Any], after_date: RFC3339Time
    ) -> List[UTDOGMDocket]:
        raise Exception("Not Impelemented")

    def into_generic_case_data(self, state_data: UTDOGMDocket) -> GenericCase:
        """Convert to generic case format"""
        return GenericCase(
            case_number=state_data.case_number,
            case_type=f"{state_data.matter_type} - {state_data.matter_subtype}",
            description=state_data.case_title,
            industry=state_data.industry_affected,
            petitioner=state_data.organization,
            opened_date=date_to_rfctime(
                datetime.strptime(state_data.date_filed, "%m/%d/%Y").date()
            ),
            extra_metadata={
                "matter_type": state_data.matter_type,
                "matter_subtype": state_data.matter_subtype,
            },
        )

    def into_generic_filing_data(self, state_data: UTDOGMFiling) -> GenericFiling:
        """Convert NYPUCFiling to a generic Filing object."""

        filed_date_obj = datetime.strptime(state_data.date_filed, "%m/%d/%Y").date()

        attachments = [
            GenericAttachment(
                name=att.document_title,
                url=att.url,
                document_extension=att.document_extension,
            )
            for att in state_data.attachments
        ]

        return GenericFiling(
            # case_number=self.docket_id,
            filed_date=date_to_rfctime(filed_date_obj),
            party_name=state_data.filing_on_behalf_of,
            filing_type=state_data.filing_type,
            description=state_data.description_of_filing,
            attachments=attachments,
            extra_metadata={},
        )

    def enrich_filing_data_intermediate(
        self, filing_data: UTDOGMFiling
    ) -> Dict[str, Any]:
        return {}

    def enrich_filing_data_from_intermediate_intermediate(
        self, filing_data: UTDOGMFiling, intermediate: Dict[str, Any]
    ) -> UTDOGMFiling:
        return filing_data
