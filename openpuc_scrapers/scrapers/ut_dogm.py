import logging
from pathlib import Path
from openpuc_scrapers.models.utils import rand_string
from openpuc_scrapers.models.attachment import GenericAttachment
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from pydantic import BaseModel, HttpUrl
from typing import Any, Dict, List
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
    docket_govid: str = ""
    date_filed: str = ""
    filing_on_behalf_of: str = ""
    description_of_filing: str = ""
    filing_no: str = ""
    filed_by: str = ""
    response_to: str = ""


class UTDOGMDocket(BaseModel):
    docket_govid: str
    matter_type: str
    matter_subtype: str
    case_title: str
    organization: str
    date_filed: str
    industry_affected: str
    related_cases: List["UTDOGMDocket"] = []
    party_list: List[str] = []


def combine_dockets(docket_lists: List[List[UTDOGMDocket]]) -> List[UTDOGMDocket]:
    all_dockets = [d for sublist in docket_lists for d in sublist]
    return sorted(
        all_dockets,
        key=lambda x: datetime.strptime(x.date_filed, "%m/%d/%Y"),
        reverse=True,
    )


def process_docket(docket: UTDOGMDocket) -> str:
    default_logger.info(
        f"Processing docket {docket.docket_govid} from {docket.date_filed}"
    )
    default_logger.debug(f"Docket metadata: {docket.model_dump_json()}")

    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options

    assert docket.docket_govid, "Docket case number cannot be empty"
    assert len(docket.docket_govid) >= 6, (
        f"Invalid case number format: {docket.docket_govid}"
    )

    user_data_dir = Path("/tmp/", "selenium-userdir-" + rand_string())
    user_data_dir.mkdir(parents=True, exist_ok=True)

    chrome_options = Options()
    chrome_options.add_argument(f"--user-data-dir={user_data_dir}")
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")

    driver = webdriver.Chrome(options=chrome_options)
    try:
        url = f"https://ogm.utah.gov/cgi-bin/cfms/index.cfm?action=docket&docket_number={docket.docket_govid}"
        default_logger.debug(f"Navigating to docket URL: {url}")
        driver.get(url)
        default_logger.info(f"Loaded docket page for {docket.docket_govid}")

        default_logger.debug("Waiting for page overlay to clear")
        for attempt in range(20):
            overlay = driver.find_element(By.ID, "GridPlaceHolder_upUpdatePanelGrd")
            current_style = overlay.get_attribute("style")
            default_logger.debug(
                f"Overlay status attempt {attempt + 1}: {current_style}"
            )

            if current_style == "display: none;":
                default_logger.info("Page overlay cleared successfully")
                break
            time.sleep(1)
        else:
            raise TimeoutError("Page load timed out")

        table_element = driver.find_element(By.ID, "tblPubDoc")
        outer_html_table = table_element.get_attribute("outerHTML")
        assert outer_html_table is not None, "Failed to retrieve table HTML content"
        assert len(outer_html_table) > 1000, (
            f"Unexpectedly small table HTML: {len(outer_html_table)} bytes"
        )

        default_logger.info(
            f"Successfully retrieved table data for {docket.docket_govid} "
            f"({len(outer_html_table)} bytes)"
        )
        driver.quit()
        return outer_html_table

    except Exception as e:
        default_logger.error(f"Error processing docket {docket.docket_govid}: {e}")
        raise e
    finally:
        driver.quit()


def partialutdogm_to_universal_url(url: str) -> str:
    removed_dots = url.removeprefix("../")
    unvalidated_url = f"https://ogm.utah.gov/public/{removed_dots}"
    return str(HttpUrl(unvalidated_url))


def extract_docket_info_from_caselisthtml(
    intermediate: Dict[str, Any],
) -> List[UTDOGMDocket]:
    default_logger.info("Beginning docket info extraction from caselist")
    assert intermediate, "Empty intermediate input"
    assert "html" in intermediate, "Missing HTML content in intermediate"
    assert "industry" in intermediate, "Missing industry info in intermediate"

    html_content = intermediate["html"]
    assert html_content, "Empty HTML content received"
    default_logger.info("Begin Processing docket.")
    html_content = intermediate["html"]
    soup = BeautifulSoup(html_content, "html.parser")
    rows = soup.find_all("tr", role="row")
    default_logger.info(f"Found {len(rows)} table rows to process")
    if len(rows) == 0:
        default_logger.error(
            "Found zero dockets in list, not sure whats causing this, I swear I will investigate this later. Ignoring for now - nic"
        )
        return []

    docket_infos: List[UTDOGMDocket] = []

    for row in rows:
        cells = row.find_all("td")
        default_logger.debug(f"Processing row with {len(cells)} cells")
        assert len(cells) >= 6, f"Row only has {len(cells)} cells (needs 6)"
        try:
            docket_govid = cells[0].find("a").text.strip()
            assert docket_govid, "Empty case number in row"

            docket_info = UTDOGMDocket(
                docket_govid=cells[0].find("a").text.strip(),
                matter_type=cells[1].text.strip(),
                matter_subtype=cells[2].text.strip(),
                date_filed=cells[3].text.strip(),
                case_title=cells[4].text.strip(),
                organization=cells[5].text.strip(),
                industry_affected=intermediate["industry"].strip(),
                party_list=[cells[5].text.strip()],
            )
            docket_infos.append(docket_info)
        except Exception as e:
            default_logger.error(f"Error processing row: {e}")

    return docket_infos


def extract_filings_from_dockethtml(table_html: str, case: str) -> List[UTDOGMFiling]:
    default_logger.info(f"Extracting rows for case {case}")
    assert table_html, "Empty table HTML input"
    assert case, "Empty case number provided"
    soup = BeautifulSoup(table_html, "html.parser")

    body = soup.find("tbody")
    if not body:
        default_logger.error("No Tablebody found in html")
        default_logger.error(table_html)
        return []
    else:
        default_logger.info("Found Tablebody.")
    rows = body.find_all("tr") if body else []
    filing_data = []

    for row in rows:
        try:
            cells = row.find_all("td")
            if len(cells) < 7:
                continue

            link = cells[3].find("a")
            if not link:
                continue

            filing_item = UTDOGMFiling(
                attachments=[
                    UTDOGMAttachment(
                        document_title=link.get_text(strip=True),
                        url=partialutdogm_to_universal_url(link["href"]),
                        file_name=cells[6].get_text(strip=True),
                        document_extension=(
                            cells[6].get_text(strip=True).split(".")[-1]
                            if cells[6].get_text(strip=True)
                            else ""
                        ),
                    )
                ],
                filing_type=cells[2].get_text(strip=True),
                docket_govid=case,
                date_filed=cells[1].get_text(strip=True),
                filing_on_behalf_of=cells[4].get_text(strip=True),
                description_of_filing=link.get_text(strip=True),
                filing_no=cells[5].get_text(strip=True),
                filed_by=cells[4].get_text(strip=True),
            )
            filing_data.append(filing_item)
        except Exception as e:
            print(f"Error processing row: {e}\nRow content: {row.prettify()}")

    deduped_data = deduplicate_individual_attachments_into_files(filing_data)
    return deduped_data


def deduplicate_individual_attachments_into_files(
    raw_files: List[UTDOGMFiling],
) -> List[UTDOGMFiling]:
    assert raw_files, "Empty raw_files input"
    assert len(raw_files) != 0, "No Raw Files to deduplicate"

    dict_utdogm = {}

    def make_dedupe_string(file: UTDOGMFiling) -> str:
        return f"filing-{file.filing_no}-case-{file.docket_govid}"

    for file in raw_files:
        assert file.filing_no, "Filing missing filing_no"
        assert file.docket_govid, "Filing missing docket_govid"
        assert file.attachments, "Filing has no attachments"

        dedupestr = make_dedupe_string(file)
        default_logger.debug(f"Processing dedupe key: {dedupestr}")

        if dict_utdogm.get(dedupestr) is not None:
            default_logger.debug(f"Merging attachments for existing key {dedupestr}")
            dict_utdogm[dedupestr].attachments.extend(file.attachments)
        else:
            dict_utdogm[dedupestr] = file
    return_vals = list(dict_utdogm.values())
    assert len(return_vals) != 0, (
        "Somehow came in with multiple files and deduplicated them down to no files."
    )
    default_logger.info(
        f"Deduplicated {len(raw_files)} raw filings into {len(return_vals)} final files."
    )

    return return_vals


class UTDOGMScraper(GenericScraper[UTDOGMDocket, UTDOGMFiling]):
    state: str = "ut"
    jurisdiction_name: str = "ut_dogm"
    """Concrete implementation of GenericScraper for UTDOGM"""

    def universal_caselist_intermediate(self) -> Dict[str, Any]:
        """Return industry numbers to process"""
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options

        user_data_dir = Path("/tmp/", "selenium-userdir-" + rand_string())
        user_data_dir.mkdir(parents=True, exist_ok=True)

        chrome_options = Options()
        chrome_options.add_argument(f"--user-data-dir={user_data_dir}")
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")

        def process_industry(industry_num: int) -> Dict[str, Any]:
            """Task to process a single industry number and return its dockets"""

            driver = webdriver.Chrome(options=chrome_options)

            try:
                url = f"https://ogm.utah.gov/cgi-bin/cfms/index.cfm?action=docket&industry={industry_num}"
                driver.get(url)

                wait = WebDriverWait(driver, 300)
                industry_elem = wait.until(
                    EC.presence_of_element_located(
                        (By.ID, "GridPlaceHolder_lblSearchCriteriaValue")
                    )
                )
                industry_affected = industry_elem.text.replace(
                    "Industry Affected:", ""
                ).strip()
                time.sleep(40)

                table_elem = wait.until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "#tblSearchedMatterExternal > tbody")
                    )
                )
                table_html = table_elem.get_attribute("outerHTML") or ""

                return {"html": table_html, "industry": industry_affected}

            except TimeoutException as e:
                print(f"Timeout waiting for industry {industry_num}")
                raise e
            except Exception as e:
                print(f"Error processing industry {industry_num}: {e}")
                raise e
            finally:
                driver.quit()

        nums = list(range(1, 10))
        docket_intermediate_lists = [
            process_industry(industry_num) for industry_num in nums
        ]
        return {"industry_intermediates": docket_intermediate_lists}

    def universal_caselist_from_intermediate(
        self, intermediate: Dict[str, Any]
    ) -> List[UTDOGMDocket]:
        intermediate_list = intermediate["industry_intermediates"]
        caselist: List[UTDOGMDocket] = []
        for industry_intermediate in intermediate_list:
            assert isinstance(industry_intermediate, dict)
            assert "html" in industry_intermediate
            assert "industry" in industry_intermediate
            assert isinstance(industry_intermediate["html"], str)
            assert industry_intermediate["html"] != ""
            assert isinstance(industry_intermediate["industry"], str)
            assert industry_intermediate["industry"] != ""
            docket_info = extract_docket_info_from_caselisthtml(industry_intermediate)
            caselist.extend(docket_info)
        return caselist

    def filing_data_intermediate(self, data: UTDOGMDocket) -> Dict[str, Any]:
        return {"docket_id": data.docket_govid, "html": process_docket(data)}

    def filing_data_from_intermediate(
        self, intermediate: Dict[str, Any]
    ) -> List[UTDOGMFiling]:
        assert all(key in intermediate for key in ("docket_id", "html"))
        assert isinstance(intermediate["docket_id"], str)
        assert isinstance(intermediate["html"], str)

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
        return GenericCase(
            docket_govid=state_data.docket_govid,
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
