import re


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


import asyncio
import aiohttp
import json
import csv
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import time


class PDFScraper:
    """
    Asynchronously scrapes PDFs from Utah URLs and processes them through openscrapers service.
    Processes in batches and writes to CSV as each batch completes, maintaining order.
    """

    def __init__(
        self,
        openscrapers_endpoint: str,
        start_index: int,
        end_index: int,
        batch_size: int = 20,
    ):
        self.openscrapers_endpoint = openscrapers_endpoint
        self.start_index = start_index
        self.end_index = end_index
        self.batch_size = batch_size
        self.backup_dir = Path("backup")
        self.csv_filename = "results.csv"
        self.csv_header = [
            "file_index",
            "hash",
            "url",
            "server_filename",
            "api_number_guess",
            "file_s3_uri",
        ]

    def setup_directories_and_csv(self):
        """Create necessary directories and initialize CSV file with headers if needed."""
        self.backup_dir.mkdir(exist_ok=True)

        csv_exists = Path(self.csv_filename).exists()
        if not csv_exists:
            with open(self.csv_filename, "w", newline="") as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(self.csv_header)

    def create_payload(self, utah_url: str) -> Dict:
        """Create the API payload for a given Utah URL."""
        return {
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
            "wait_for_s3_upload": False,
        }

    async def process_single_request(
        self, session: aiohttp.ClientSession, index: int
    ) -> Tuple[int, Optional[Dict]]:
        """
        Process a single request for the given index.
        Returns tuple of (index, response_data) or (index, None) if failed.
        """
        utah_url = generate_utah_url(index)  # Assuming this function exists
        payload = self.create_payload(utah_url)

        try:
            print(f"Processing index {index} with URL {utah_url}")

            async with session.post(
                self.openscrapers_endpoint,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=60),
            ) as response:
                response.raise_for_status()
                response_data = await response.json()

                # Save backup JSON
                await self.save_backup_json(index, response_data)

                # Prepare CSV row data
                server_filename = response_data.get("server_file_name", "unknown")
                api_guess = transform_filename_to_api_number(
                    server_filename
                )  # Assuming this function exists

                csv_data = {
                    "file_index": index,
                    "hash": response_data.get("hash", ""),
                    "url": utah_url,
                    "server_filename": server_filename,
                    "api_number_guess": api_guess,
                    "file_s3_uri": response_data.get("file_s3_uri", ""),
                }

                print(f"Successfully processed index {index}")
                return index, csv_data

        except asyncio.TimeoutError:
            print(f"Timeout error processing index {index}")
            return index, None

        except aiohttp.ClientError as e:
            print(f"Client error processing index {index}: {e}")
            return index, None

        except json.JSONDecodeError as e:
            print(f"JSON decode error for index {index}: {e}")
            return index, None

        except Exception as e:
            print(f"Unexpected error processing index {index}: {e}")
            return index, None

    async def save_backup_json(self, index: int, response_data: Dict):
        """Save response JSON to backup directory."""
        backup_file = self.backup_dir / f"{index}.json"
        with open(backup_file, "w") as f:
            json.dump(response_data, f, indent=2)

    def write_batch_to_csv(self, batch_results: List[Tuple[int, Optional[Dict]]]):
        """
        Write a batch of results to CSV in order of file_index.
        Only writes successful results (non-None data).
        """
        # Sort batch results by index to maintain order
        batch_results.sort(key=lambda x: x[0])

        # Filter out failed requests and extract successful data
        successful_results = [data for index, data in batch_results if data is not None]

        if not successful_results:
            print(f"No successful results in this batch")
            return 0

        # Write to CSV
        with open(self.csv_filename, "a", newline="") as csvfile:
            writer = csv.writer(csvfile)
            for data in successful_results:
                csv_row = [
                    data["file_index"],
                    data["hash"],
                    data["url"],
                    data["server_filename"],
                    data["api_number_guess"],
                    data["file_s3_uri"],
                ]
                writer.writerow(csv_row)
            csvfile.flush()  # Ensure data is written to disk immediately

        success_count = len(successful_results)
        print(f"Wrote {success_count} successful results to CSV")
        return success_count

    def create_batches(self) -> List[List[int]]:
        """Create batches of indices to process."""
        all_indices = list(range(self.start_index, self.end_index))
        batches = []

        for i in range(0, len(all_indices), self.batch_size):
            batch = all_indices[i : i + self.batch_size]
            batches.append(batch)

        return batches

    async def run_async_scraping(self):
        """
        Main async function to process all indices in batches.
        Writes results to CSV as each batch completes, maintaining order within each batch.
        """
        self.setup_directories_and_csv()

        # Create batches of indices
        batches = self.create_batches()
        total_indices = self.end_index - self.start_index
        total_successful = 0

        print(
            f"Processing {total_indices} indices in {len(batches)} batches of {self.batch_size}"
        )

        # Create connector with appropriate limits
        connector = aiohttp.TCPConnector(limit=30, limit_per_host=20)

        async with aiohttp.ClientSession(connector=connector) as session:
            start_time = time.time()

            for batch_num, batch_indices in enumerate(batches, 1):
                print(
                    f"\n--- Processing Batch {batch_num}/{len(batches)} (indices {batch_indices[0]} to {batch_indices[-1]}) ---"
                )
                batch_start_time = time.time()

                # Create tasks for current batch
                batch_tasks = [
                    self.process_single_request(session, index)
                    for index in batch_indices
                ]

                # Wait for all tasks in this batch to complete
                batch_results = await asyncio.gather(
                    *batch_tasks, return_exceptions=True
                )

                # Handle any exceptions that were returned
                clean_batch_results = []
                for result in batch_results:
                    if isinstance(result, Exception):
                        print(
                            f"Task in batch {batch_num} failed with exception: {result}"
                        )
                        # Add a placeholder for failed task to maintain indexing
                        clean_batch_results.append((0, None))  # Will be filtered out
                    else:
                        clean_batch_results.append(result)

                # Write this batch's results to CSV immediately
                batch_successful = self.write_batch_to_csv(clean_batch_results)
                total_successful += batch_successful

                batch_end_time = time.time()
                batch_duration = batch_end_time - batch_start_time
                print(f"Batch {batch_num} completed in {batch_duration:.2f} seconds")

                # Brief pause between batches to be nice to the server
                if batch_num < len(batches):
                    await asyncio.sleep(1)

            end_time = time.time()
            total_duration = end_time - start_time

            print("\n=== Processing Complete ===")
            print(f"Total time: {total_duration:.2f} seconds")
            print(f"Successfully processed: {total_successful}/{total_indices} indices")
            print(
                f"Average time per request: {total_duration / total_indices:.2f} seconds"
            )


def main():
    """
    Main function to run the async PDF scraper.
    """
    start_index = 1180
    end_index = 40000
    # These would need to be defined or passed as parameters
    openscrapers_endpoint = (
        "http://localhost:33399/admin/direct_file_attachment_process"
    )
    batch_size = 5  # 20 was waaay to agressive

    scraper = PDFScraper(openscrapers_endpoint, start_index, end_index, batch_size)

    # Run the async scraping
    asyncio.run(scraper.run_async_scraping())


if __name__ == "__main__":
    main()
