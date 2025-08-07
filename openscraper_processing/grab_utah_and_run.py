import re

start_index = 0
end_endex = 40000


def transform_filename_to_api_number(file_name: str) -> str:
    # Remove everything that is not a digit.
    digits = re.sub(r"\D", "", file_name)

    # Locate the first occurrence of the prefix "430".
    start = digits.find("430")
    if start == -1:
        return "unknown"

    # Extract exactly 10 digits starting at that point.
    api = digits[start : start + 10]

    # Validate length.
    if len(api) != 10:
        return "unknown"
    return api


openscrapers_endpoint = "http://localhost:33399/admin/direct_file_attachment_process"
# Send it to this endpoint with this schema
# {
#     "extension": "pdf",
#     "fetch_info": {
#         "decode_method": "None",
#         "request_type": "Get",
#         "url": "https://www.cte.iup.edu/cte/Resources/PDF_TestPage.pdf",
#     },
#     "jurisdiction_info": {
#         "country": "unknown",
#         "jurisdiction": "unknown",
#         "state": "unknown",
#     },
#     "process_text_before_upload": false,
#     "wait_for_s3_upload": true,
# }
# and this is the return schema
# {
#   "attachment": {
#     "hash": "-rKlk-TDNF_F8bK_yvSj3MB7PcEF7hD3LoIEL9KdIyI=",
#     "jurisdiction_info": {
#       "country": "unknown",
#       "state": "unknown",
#       "jurisdiction": "unknown"
#     },
#     "name": "PDF_TestPage.pdf",
#     "url": "https://www.cte.iup.edu/cte/Resources/PDF_TestPage.pdf",
#     "extension": "pdf",
#     "text_objects": [],
#     "date_added": "2025-08-07T12:42:03.241348333Z",
#     "date_updated": "2025-08-07T12:42:03.241349796Z",
#     "extra_metadata": {
#       "server_filename": "PDF_TestPage.pdf"
#     }
#   },
#   "hash": "-rKlk-TDNF_F8bK_yvSj3MB7PcEF7hD3LoIEL9KdIyI=",
#   "server_file_name": "PDF_TestPage.pdf",
#   "file_s3_uri": "https://openscrapers.sfo3.digitaloceanspaces.com/raw/file/-rKlk-TDNF_F8bK_yvSj3MB7PcEF7hD3LoIEL9KdIyI=",
#   "object_s3_uri": "https://openscrapers.sfo3.digitaloceanspaces.com/raw/metadata/-rKlk-TDNF_F8bK_yvSj3MB7PcEF7hD3LoIEL9KdIyI=.json"
# }


def generate_utah_url(number: int) -> str:
    return f"https://dataexplorer.ogm.utah.gov/api/Files?fileName=wellfile|{number}"


import requests
import json
import os
import csv
from pathlib import Path
import time


def main():
    """
    Main function to iterate through a range of file indices, fetch them from a URL,
    and process them through the openscrapers service.
    """
    # Create backup directory if it doesn't exist
    backup_dir = Path("backup")
    backup_dir.mkdir(exist_ok=True)

    # Setup CSV file
    csv_filename = "results.csv"
    csv_file_exists = Path(csv_filename).exists()
    csv_header = [
        "file_index",
        "hash",
        "url",
        "server_filename",
        "api_number_guess",
        "file_s3_uri",
    ]

    with open(csv_filename, "a", newline="") as csvfile:
        writer = csv.writer(csvfile)
        if not csv_file_exists:
            writer.writerow(csv_header)

        for i in range(start_index, end_endex):
            utah_url = generate_utah_url(i)
            payload = {
                "extension": "pdf",
                "fetch_info": {
                    "decode_method": "None",
                    "request_type": "Get",
                    "url": utah_url,
                },
                "jurisdiction_info": {
                    "country": "usa",
                    "jurisdiction": "ut_dogm",
                    "state": "ut",
                },
                "process_text_before_upload": False,
                "wait_for_s3_upload": True,
            }

            try:
                print(f"Processing index {i} with URL {utah_url}")
                response = requests.post(
                    openscrapers_endpoint, json=payload, timeout=60
                )
                response.raise_for_status()  # Raise an exception for bad status codes

                response_data = response.json()

                # Save response JSON
                with open(backup_dir / f"{i}.json", "w") as f:
                    json.dump(response_data, f, indent=2)

                # Append to CSV
                server_filename = response_data.get("server_file_name", "unknown")
                api_guess = transform_filename_to_api_number(server_filename)
                csv_row = [
                    i,
                    response_data.get("hash", ""),
                    utah_url,
                    server_filename,
                    api_guess,
                    response_data.get("file_s3_uri", ""),
                ]
                writer.writerow(csv_row)
                csvfile.flush()  # Make sure it's written to disk
                print(f"Successfully processed index {i}")

            except requests.exceptions.RequestException as e:
                print(f"Error processing index {i}: {e}")
                # Optional: add a small delay before retrying or moving to the next
                time.sleep(5)
            except json.JSONDecodeError:
                print(f"Error decoding JSON for index {i}, response: {response.text}")


if __name__ == "__main__":
    main()
