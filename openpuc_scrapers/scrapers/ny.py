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
import json


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


def extractRows(driver, case) -> List[NYPUCFileData]:
    table = driver.find_element(By.ID, "tblPubDoc")
    body = table.find_element(By.TAG_NAME, "tbody")
    rows = body.find_elements(By.TAG_NAME, "tr")
    filing_data: List[NYPUCFileData] = []
    for row in rows:
        filing_item = None
        try:
            # print(row)
            cells = row.find_elements(By.TAG_NAME, "td")
            linkcell = cells[3]
            link = linkcell.find_element(By.TAG_NAME, "a")
            # print(f"link: {link}")
            name = link.text
            href = link.get_attribute("href")
            # print(f"href: {href}")
            # skip if the filing has already been indexed
            # if graph.pages[href].visited:
            #     continue

            filing_item = NYPUCFileData(
                serial=cells[0].text,
                date_filed=cells[1].text,
                nypuc_doctype=cells[2].text,
                docket_id=case,
                name=name,
                url=href,
                organization=cells[4].text,
                itemNo=cells[5].text,
                file_name=cells[6].text,
            )
            filing_data.append(filing_item)
        except Exception as e:
            print(
                "Encountered a fatal error while processing a row: ",
                row,
                "\nencountering error: ",
                e,
            )
    # print(f"Found filings:\n {filings}")
    # return filings
    # filings = {"case": case, "filings": filing_data}
    return filing_data


defaultDriver = webdriver.Chrome()


def extractDocket(nypuc_docket_id: Union[str, NYPUCDocketInfo]) -> List[NYPUCFileData]:
    def waitForLoad(driver):
        max_wait = 60
        print("waiting for page to load")
        for i in range(max_wait):
            overlay = driver.find_element(By.ID, "GridPlaceHolder_upUpdatePanelGrd")
            display = overlay.get_attribute("style")
            if display == "display: none;":
                print("Page Loaded")
                return True
            time.sleep(1)

        print("pageload took waaaay too long")
        return False

    if isinstance(nypuc_docket_id, NYPUCDocketInfo):
        nypuc_docket_id = nypuc_docket_id.docket_id

    url = f"https://documents.dps.ny.gov/public/MatterManagement/CaseMaster.aspx?MatterCaseNo={nypuc_docket_id}"

    defaultDriver.get(url)
    waitForLoad(defaultDriver)
    try:
        rowData = extractRows(defaultDriver, case=nypuc_docket_id)
    except Exception as e:
        raise e
    return rowData


# Example usage:
if __name__ == "__main__":
    # Scrape all dockets
    all_dockets = get_all_dockets()

    # Save to JSON file

    # Print summary
    print(f"Retrieved {len(all_dockets)} total dockets")
    print(f"Date range: {all_dockets[-1].date_filed} to {all_dockets[0].date_filed}")

    # Print industry breakdown
    industry_counts = {}
    for docket in all_dockets:
        industry_counts[docket.industry_affected] = (
            industry_counts.get(docket.industry_affected, 0) + 1
        )

    print("\nDockets by industry:")
    for industry, count in sorted(industry_counts.items()):
        print(f"{industry}: {count}")
