from flytekit import task, workflow
from openpuc_scrapers.models.attachment import Attachment
from openpuc_scrapers.models.filing import Filing, IntoFiling
from openpuc_scrapers.models.misc import send_castables_to_kessler
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium import webdriver
from selenium.webdriver.common.by import By
from pydantic import BaseModel, HttpUrl
from typing import List
import time
from datetime import date, datetime
from bs4 import BeautifulSoup


class NYPUCAttachmentData(BaseModel):
    name: str
    url: str
    file_name: str


class NYPUCFileData(BaseModel, IntoFiling):
    attachements: List[NYPUCAttachmentData]
    serial: str
    date_filed: str
    nypuc_doctype: str
    name: str
    organization: str
    itemNo: str
    docket_id: str

    def into_filing(self) -> Filing:
        """Convert NYPUCFileData to a generic Filing object."""
        # Convert string date to date object
        filed_date_obj = datetime.strptime(self.date_filed, "%m/%d/%Y").date()

        # Convert NYPUCAttachmentData to generic Attachment objects
        attachments = [
            Attachment(name=att.name, url=HttpUrl(att.url)) for att in self.attachements
        ]

        return Filing(
            # case_number=self.docket_id,
            filed_date=filed_date_obj,
            party_name=self.organization,
            filing_type=self.nypuc_doctype,
            description=self.name,
            attachments=attachments,
            extra_metadata={},
        )


class NYPUCDocketInfo(BaseModel):
    docket_id: str  # 24-C-0663
    matter_type: str  # Complaint
    matter_subtype: str  # Appeal of an Informal Hearing Decision
    title: str  # In the Matter of the Rules and Regulations of the Public Service
    organization: str  # Individual
    date_filed: str
    industry_affected: str


@task
def process_industry(industry_num: int) -> List[NYPUCDocketInfo]:
    """Task to process a single industry number and return its dockets"""
    driver = webdriver.Chrome()
    all_dockets = []

    try:
        url = f"https://documents.dps.ny.gov/public/Common/SearchResults.aspx?MC=1&IA={industry_num}"
        driver.get(url)

        wait = WebDriverWait(driver, 300)
        industry_elem = wait.until(
            EC.presence_of_element_located(
                (By.ID, "GridPlaceHolder_lblSearchCriteriaValue")
            )
        )
        industry_affected = industry_elem.text.replace("Industry Affected:", "").strip()
        time.sleep(2)  # Reduced from 30 for demonstration

        table_elem = wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "#tblSearchedMatterExternal > tbody")
            )
        )
        table_html = table_elem.get_attribute("outerHTML") or ""

        # Use existing helper function
        return extract_docket_info(table_html, industry_affected)

    except TimeoutException:
        print(f"Timeout waiting for industry {industry_num}")
        return []
    except Exception as e:
        print(f"Error processing industry {industry_num}: {e}")
        return []
    finally:
        driver.quit()


@task
def combine_dockets(docket_lists: List[List[NYPUCDocketInfo]]) -> List[NYPUCDocketInfo]:
    """Combine and sort dockets from all industries"""
    all_dockets = [d for sublist in docket_lists for d in sublist]
    return sorted(
        all_dockets,
        key=lambda x: datetime.strptime(x.date_filed, "%m/%d/%Y"),
        reverse=True,
    )


@task
def process_docket(docket: NYPUCDocketInfo) -> str:
    """Task to process a single docket and return its files"""
    driver = webdriver.Chrome()
    try:
        url = f"https://documents.dps.ny.gov/public/MatterManagement/CaseMaster.aspx?MatterCaseNo={docket.docket_id}"
        driver.get(url)

        # Custom wait logic
        for _ in range(10):  # Reduced from 60 for demonstration
            overlay = driver.find_element(By.ID, "GridPlaceHolder_upUpdatePanelGrd")
            if overlay.get_attribute("style") == "display: none;":
                break
            time.sleep(1)
        else:
            raise TimeoutError("Page load timed out")

        table_element = driver.find_element(By.ID, "tblPubDoc")
        return table_element.get_attribute("outerHTML")

    except Exception as e:
        print(f"Error processing docket {docket.docket_id}: {e}")
        raise e
    finally:
        driver.quit()


@workflow
async def full_scraping_workflow() -> List[List[NYPUCFileData]]:
    """Main workflow that coordinates all scraping tasks"""
    # Process all industries in parallel
    industries = list(range(1, 11))
    industry_results = list(map(process_industry, industries))

    # Combine results from all industries
    combined_dockets = combine_dockets(docket_lists=industry_results)

    result_filedata: List[List[NYPUCFileData]] = []
    for docket in combined_dockets:
        # Flyte Task that downloads the html
        html = process_docket(docket)
        # Flyte Task that extracts the data from the html
        results = extract_rows(html, docket)
        result_filedata.append(results)
        print(f"Processed Doc rows for {docket.docket_id}")

    return result_filedata


@workflow
def test_small_workflow() -> List[NYPUCFileData]:
    """Main workflow that coordinates all scraping tasks"""
    docket = NYPUCDocketInfo(
        docket_id="18-G-0736",
        matter_type="Complaint",
        matter_subtype="Formal Non-Consumer Related",
        title="Complaint and Formal Dispute Resolution Request For Expedited Resolution of East Coast Power & Gas, LLC Regarding Annual Reconciliation Charges of KeySpan Gas East Corporation d/b/a National Grid for January - April 2018",
        organization="East Coast Power & Gas, LLC",
        date_filed="12/05/2018",
        industry_affected="Gas",  # This field wasn't provided in the comments
    )
    # Flyte Task that downloads the html
    html = process_docket(docket)
    # Flyte Task that extracts the data from the html
    results = extract_rows(html, docket)
    print(f"Processed Doc rows for {docket.docket_id}")

    send_castables_to_kessler(results)

    return results


@task
def extract_docket_info(
    html_content: str, docket_info: NYPUCDocketInfo
) -> List[NYPUCDocketInfo]:
    """
    Extract complete docket information from HTML table rows

    Args:
        html_content (str): HTML string containing the table

    Returns:
        List[NYPUCDocketInfo]: List of NYPUCDocketInfo objects containing details for each docket
    """
    soup = BeautifulSoup(html_content, "html.parser")
    rows = soup.find_all("tr", role="row")

    docket_infos: List[NYPUCDocketInfo] = []
    industry_affected = docket_info.industry_affected.strip()

    for row in rows:
        # Get all cells in the row
        cells = row.find_all("td")
        if len(cells) >= 6:  # Ensure we have all required cells
            try:
                docket_info = NYPUCDocketInfo(
                    docket_id=cells[0].find("a").text.strip(),
                    matter_type=cells[1].text.strip(),
                    matter_subtype=cells[2].text.strip(),
                    date_filed=cells[3].text.strip(),
                    title=cells[4].text.strip(),
                    organization=cells[5].text.strip(),
                    industry_affected=industry_affected.strip(),
                )
                docket_infos.append(docket_info)
            except Exception as e:
                # Skip malformed rows
                print(f"Error processing row: {e}")
                continue

    return docket_infos


@task
def extract_rows(table_html: str, case: str) -> List[NYPUCFileData]:
    """Parse table HTML with BeautifulSoup and extract filing data."""
    soup = BeautifulSoup(table_html, "html.parser")
    table = soup.find("table", id="tblPubDoc")

    if not table:
        return []

    body = table.find("tbody")
    rows = body.find_all("tr") if body else []
    filing_data = []

    for row in rows:
        try:
            cells = row.find_all("td")
            if len(cells) < 7:
                continue  # Skip rows with insufficient cells

            link = cells[3].find("a")
            if not link:
                continue  # Skip rows without links

            filing_item = NYPUCFileData(
                attachment=NYPUCAttachmentData(
                    name=link.get_text(strip=True),
                    url=link["href"],
                ),
                serial=cells[0].get_text(strip=True),
                date_filed=cells[1].get_text(strip=True),
                nypuc_doctype=cells[2].get_text(strip=True),
                docket_id=case,
                organization=cells[4].get_text(strip=True),
                itemNo=cells[5].get_text(strip=True),
                file_name=cells[6].get_text(strip=True),
            )
            filing_data.append(filing_item)
        except Exception as e:
            print(f"Error processing row: {e}\nRow content: {row.prettify()}")

    deduped_data = deduplicate_individual_attachments_into_files(filing_data)
    return deduped_data


def deduplicate_individual_attachments_into_files(
    raw_files: List[NYPUCFileData],
) -> List[NYPUCFileData]:
    dict_nypuc = {}

    def make_dedupe_string(file: NYPUCFileData) -> str:
        return f"itemnum-{file.itemNo}-caseid-{file.docket_id}"

    for file in raw_files:
        dedupestr = make_dedupe_string(file)
        if dict_nypuc.get(dedupestr) is not None:
            dict_nypuc[dedupestr].attachements.append(file.attachements)
    return_vals = dict_nypuc.values()
    return list(return_vals)


if __name__ == "__main__":
    # For local testing
    print("Running scraping workflow...")
    results = full_scraping_workflow()
    print(f"Scraped {len(results)} dockets with files")
