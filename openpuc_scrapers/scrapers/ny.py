from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By

from pydantic import BaseModel

from typing import List, Union

import time
from datetime import datetime


from bs4 import BeautifulSoup


class NYPUCFileData(BaseModel):
    serial: str
    date_filed: str
    nypuc_doctype: str
    name: str
    url: str
    organization: str
    itemNo: str
    file_name: str
    docket_id: str

    def __str__(self):
        return f"\n(\n\tSerial: {self.serial}\n\tDate Filed: {self.date_filed}\
        \n\tNY PUC Doc Type: {self.nypuc_doctype}\n\tName: {self.name}\n\tURL: \
        {self.url}\nOrganization: {self.organization}\n\tItem No: {self.itemNo}\n\
        \tFile Name: {self.file_name}\n)\n"

    def __repr__(self):
        return self.__str__()


class NYPUCDocketInfo(BaseModel):
    docket_id: str  # 24-C-0663
    matter_type: str  # Complaint
    matter_subtype: str  # Appeal of an Informal Hearing Decision
    title: str  # In the Matter of the Rules and Regulations of the Public Service
    organization: str  # Individual
    date_filed: str
    industry_affected: str


def get_all_dockets() -> List[NYPUCDocketInfo]:
    """
    Scrape docket information for all industry types (1-10)
    Returns sorted list of all dockets
    """
    driver = webdriver.Chrome()
    all_dockets: List[NYPUCDocketInfo] = []

    try:
        # Try industry affected numbers 1-10
        for industry_num in range(1, 11):
            url = f"https://documents.dps.ny.gov/public/Common/SearchResults.aspx?MC=1&IA={industry_num}&MT=&MST=&CN=&C=&M=&CO=0"
            driver.get(url)

            try:
                # Wait for the industry affected label to be present
                wait = WebDriverWait(driver, 300)
                industry_elem = wait.until(
                    EC.presence_of_element_located(
                        (By.ID, "GridPlaceHolder_lblSearchCriteriaValue")
                    )
                )

                # Extract industry affected value
                industry_text = industry_elem.text
                industry_affected = industry_text.replace(
                    "Industry Affected:", ""
                ).strip()
                time.sleep(30)

                # Wait for table to load
                table_elem = wait.until(
                    EC.presence_of_element_located(
                        (
                            By.CSS_SELECTOR,
                            "#tblSearchedMatterExternal > tbody:nth-child(3)",
                        )
                    )
                )

                # Get table HTML and extract docket info
                table_html = table_elem.get_attribute("outerHTML")
                if table_html is None:
                    table_html = ""
                if table_html == "":
                    print(
                        "SOMETHING WENT SERIOUSLY WRONG AND THE TABLE IS EMPTY!!!!!\n"
                    )
                dockets = extract_docket_info(table_html, industry_affected)
                all_dockets.extend(dockets)

            except TimeoutException:
                print(f"Timeout waiting for industry {industry_num}")
                continue
            except Exception as e:
                print(f"Error processing industry {industry_num}: {e}")
                continue

            # Brief pause between requests
            time.sleep(2)

    finally:
        driver.quit()

    # Sort by date filed
    return sorted(
        all_dockets,
        key=lambda x: datetime.strptime(x.date_filed, "%m/%d/%Y"),
        reverse=True,
    )


def extract_docket_info(
    html_content: str, industry_affected: str
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
                serial=cells[0].get_text(strip=True),
                date_filed=cells[1].get_text(strip=True),
                nypuc_doctype=cells[2].get_text(strip=True),
                docket_id=case,
                name=link.get_text(strip=True),
                url=link["href"],
                organization=cells[4].get_text(strip=True),
                itemNo=cells[5].get_text(strip=True),
                file_name=cells[6].get_text(strip=True),
            )
            filing_data.append(filing_item)
        except Exception as e:
            print(f"Error processing row: {e}\nRow content: {row.prettify()}")

    return filing_data


default_driver = webdriver.Chrome()


def extract_docket(nypuc_docket_id: Union[str, NYPUCDocketInfo]) -> List[NYPUCFileData]:
    """Main function to retrieve and parse case documents."""
    case_id = (
        nypuc_docket_id.docket_id
        if isinstance(nypuc_docket_id, NYPUCDocketInfo)
        else nypuc_docket_id
    )
    url = f"https://documents.dps.ny.gov/public/MatterManagement/CaseMaster.aspx?MatterCaseNo={case_id}"

    def wait_for_load(driver):
        """Wait for the data grid to finish loading."""
        for _ in range(60):
            overlay = driver.find_element(By.ID, "GridPlaceHolder_upUpdatePanelGrd")
            if overlay.get_attribute("style") == "display: none;":
                return True
            time.sleep(1)
        raise TimeoutError("Page load timed out")

    try:
        default_driver.get(url)
        wait_for_load(default_driver)

        # Extract table HTML as string
        table_element = default_driver.find_element(By.ID, "tblPubDoc")
        table_html = table_element.get_attribute("outerHTML")

        return extract_rows(table_html, case_id)

    except Exception as e:
        print(f"Error in extract_docket: {e}")
        raise
