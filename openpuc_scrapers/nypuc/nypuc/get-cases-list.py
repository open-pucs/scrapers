import re
from bs4 import BeautifulSoup
from typing import List, Dict

from pydantic import BaseModel

import json


from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By

import requests
import argparse


from urllib.parse import urlparse, parse_qs

from typing import List, Optional
import time
import json

from pydantic import BaseModel

import os

import aiohttp

import asyncio


from datetime import datetime
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException


class DocketInfo(BaseModel):
    docket_id: str  # 24-C-0663
    matter_type: str  # Complaint
    matter_subtype: str  # Appeal of an Informal Hearing Decision
    title: str  # In the Matter of the Rules and Regulations of the Public Service
    organization: str  # Individual
    date_filed: str
    industry_affected: str


# https://documents.dps.ny.gov/public/Common/SearchResults.aspx?MC=1&IA={industry_affected_number}&MT=&MST=&CN=&C=&M=&CO=0
# For this following script try all numbers between 1 and 10.
# after 30 seconds get the current status of the html on the page, then do the following.
# 1. Look across the entire page for this text <b>Industry Affected: </b>, it should be in something that looks like this
# <span id="GridPlaceHolder_lblSearchCriteriaValue"><b>Industry Affected: </b>Cable</span>
# 2. Then go ahead and get the value, in this case "Cable" and store it in a variable.
# 3. Then go ahead and get the CSS selector for the table (After waiting 30 seconds.)
#  #tblSearchedMatterExternal > tbody:nth-child(3)
# 4. Then go ahead and call this extract docket info function on the resultant html data. passing in the industry_affected variable.
# 5. Then go ahead and get all the 10 different docket lists, combine them into a single list, and then sort them based on the date they were filed.
# 6. Use selineum for all the web data processing.


def get_all_dockets() -> List[DocketInfo]:
    """
    Scrape docket information for all industry types (1-10)
    Returns sorted list of all dockets
    """
    driver = webdriver.Chrome()
    all_dockets: List[DocketInfo] = []

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


def save_dockets_to_json(dockets: List[DocketInfo], output_file: str) -> None:
    """Save docket list to JSON file"""
    docket_dicts = [d.model_dump() for d in dockets]
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(docket_dicts, f, indent=2)


def extract_docket_info(html_content: str, industry_affected: str) -> List[DocketInfo]:
    """
    Extract complete docket information from HTML table rows

    Args:
        html_content (str): HTML string containing the table

    Returns:
        List[DocketInfo]: List of DocketInfo objects containing details for each docket
    """
    soup = BeautifulSoup(html_content, "html.parser")
    rows = soup.find_all("tr", role="row")

    docket_infos: List[DocketInfo] = []

    for row in rows:
        # Get all cells in the row
        cells = row.find_all("td")
        if len(cells) >= 6:  # Ensure we have all required cells
            try:
                docket_info = DocketInfo(
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


# Example usage:
if __name__ == "__main__":
    # Scrape all dockets
    all_dockets = get_all_dockets()

    # Save to JSON file
    save_dockets_to_json(all_dockets, "all_dockets.json")

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


# def process_docket_file(input_path: str, output_path: str) -> None:
#     """
#         Process HTML file to extract complete docket information and save to JSON
#     >>>>>>> Snippet
#
#         Args:
#             input_path (str): Path to input HTML file
#             output_path (str): Path to output JSON file
#     """
#
#     with open(input_path, "r", encoding="utf-8") as f:
#         html_content = f.read()
#
#     docket_infos = extract_docket_info(html_content, "")
#
#     # Convert to list of dictionaries for JSON serialization
#     docket_dicts = [docket.model_dump() for docket in docket_infos]
#
#     with open(output_path, "w", encoding="utf-8") as f:
#         json.dump(docket_dicts, f, indent=2)


# def extract_docket_details(html_content: str) -> List[Dict[str, str]]:
#     """
#     Extract docket IDs and their associated information using BeautifulSoup
#
#     Args:
#         html_content (str): HTML string containing the table
#
#     Returns:
#         List[Dict[str, str]]: List of dictionaries containing docket details
#     """
#     soup = BeautifulSoup(html_content, "html.parser")
#     # docket_links = soup.find_all('a', href=lambda x: x and 'MatterSeq' in x)
#     docket_links = soup.find_all("a")
#
#     docket_details = []
#     for link in docket_links:
#         docket_id = link.text.strip()
#         if re.match(r"\d{2}-[A-Z]-\d{4}", docket_id):
#             # Get the parent tr element
#             row = link.find_parent("tr")
#             if row:
#                 # Extract additional information from the row
#                 details = {
#                     "docket_id": docket_id,
#                     "href": link["href"],
#                     "type": row.find_all("td")[1].text.strip(),
#                     "date": row.find("td", class_="sorting_1").text.strip(),
#                     "description": row.find_all("td")[4].text.strip(),
#                 }
#                 docket_details.append(details)
#
#     return docket_details
