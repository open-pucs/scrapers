from datetime import datetime


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


defaultDriver = webdriver.Chrome()

pageData = {}


class DocketInfo(BaseModel):
    docket_id: str  # 24-C-0663
    matter_type: str  # Complaint
    matter_subtype: str  # Appeal of an Informal Hearing Decision
    industry_affected: str
    title: str  # In the Matter of the Rules and Regulations of the Public Service
    organization: str  # Individual
    date_filed: str  # 12/13/2022


async def verify_docket_id(docket: DocketInfo):
    obj = {
        "docket_gov_id": docket.docket_id,
        "state": "ny",
        "name": docket.title,
        "description": "",
        "matter_type": docket.matter_type,
        "industry_type": docket.industry_affected,
        "metadata": str(docket.model_dump_json()),
        "extra": "",
        "date_published": datetime.strptime(docket.date_filed, "%m/%d/%Y").strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
    }
    api_url = "http://localhost/v2/public/conversations/verify"

    print(f"Verifying docket ID {docket.docket_id}")
    async with aiohttp.ClientSession() as session:
        async with session.post(api_url, json=obj) as response:
            if response.status != 200:
                print(f"Failed verification for docket ID {docket.docket_id}")
                raise Exception(
                    f"Failed to verify docket ID. Status code: {response.status}\nResponse:\n{await response.text()}"
                )

            print(
                f"Successfully verified docket ID {docket.docket_id}: \n Response: {await response.text()}\n"
            )
            return await response.json()


async def verify_all_docket_ids(filename: str):
    with open(filename, "r") as f:
        initial_file_list = json.load(f)
    promises = []
    batch_size = 100

    for i in range(0, len(initial_file_list), batch_size):
        batch = initial_file_list[i : i + batch_size]
        batch_promises = []

        for obj in batch:
            try:
                docket = DocketInfo.model_validate(obj)
                batch_promises.append(verify_docket_id(docket))
            except Exception as e:
                print(
                    f"Error verifying docket ID: {obj['docket_id']} encountered: {e}\n"
                )

        await asyncio.gather(*batch_promises)


if __name__ == "__main__":
    asyncio.run(verify_all_docket_ids("all_dockets.json"))
    # extract_all_recovered_filing_objects()
