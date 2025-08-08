import os
import re
import asyncio
import aiohttp
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import time
import psycopg2
import psycopg2.extras


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


def generate_utah_url(number: int) -> str:
    return f"https://dataexplorer.ogm.utah.gov/api/Files?fileName=wellfile|{number}"


class PDFScraper:
    """
    Asynchronously scrapes PDFs from Utah URLs, processes them through openscrapers service,
    and ingests the results into a PostgreSQL database.
    """

    def __init__(
        self,
        openscrapers_endpoint: str,
        start_index: int,
        end_index: int,
        batch_size: int = 20,
        db_conn_string: str = "",
    ):
        self.openscrapers_endpoint = openscrapers_endpoint
        self.start_index = start_index
        self.end_index = end_index
        self.batch_size = batch_size
        self.backup_dir = Path("backup")
        self.db_conn_string = db_conn_string

    def setup_directories_and_db(self):
        """Create necessary directories and initialize database schema."""
        self.backup_dir.mkdir(exist_ok=True)
        self._setup_database()

    def _setup_database(self):
        """Connects to Postgres, creates schema and tables if they don't exist."""
        if not self.db_conn_string:
            raise ValueError("Postgres connection string not provided.")

        try:
            with psycopg2.connect(self.db_conn_string) as conn:
                with conn.cursor() as cur:
                    cur.execute("CREATE SCHEMA IF NOT EXISTS ut_dogm;")
                    cur.execute("SET search_path TO ut_dogm;")
                    cur.execute(
                        """
                        CREATE TABLE IF NOT EXISTS api_well_number_repository (
                            api_well_number TEXT PRIMARY KEY
                        );
                    """
                    )
                    cur.execute(
                        """
                        CREATE TABLE IF NOT EXISTS raw_well_attachment_storage (
                            file_index INTEGER PRIMARY KEY,
                            hash TEXT,
                            url TEXT,
                            server_filename TEXT,
                            api_number_guess TEXT,
                            file_s3_uri TEXT,
                            FOREIGN KEY (api_number_guess) REFERENCES api_well_number_repository(api_well_number)
                        );
                    """
                    )
                    conn.commit()
            print("Database setup complete.")
        except psycopg2.Error as e:
            print(f"Database setup failed: {e}")
            raise

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
        utah_url = generate_utah_url(index)
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

                await self.save_backup_json(index, response_data)

                server_filename = response_data.get("server_file_name", "unknown")
                api_guess = transform_filename_to_api_number(server_filename)

                processed_data = {
                    "file_index": index,
                    "hash": response_data.get("hash", ""),
                    "url": utah_url,
                    "server_filename": server_filename,
                    "api_number_guess": api_guess,
                    "file_s3_uri": response_data.get("file_s3_uri", ""),
                }
                print(f"Successfully processed index {index}")
                return index, processed_data

        except (asyncio.TimeoutError, aiohttp.ClientError, json.JSONDecodeError) as e:
            print(f"Error processing index {index}: {e}")
            return index, None
        except Exception as e:
            print(f"Unexpected error processing index {index}: {e}")
            return index, None

    async def save_backup_json(self, index: int, response_data: Dict):
        """Save response JSON to backup directory."""
        backup_file = self.backup_dir / f"{index:05d}.json"
        with open(backup_file, "w") as f:
            json.dump(response_data, f, indent=2)

    def ingest_to_postgres(self, batch_results: List[Tuple[int, Optional[Dict]]]):
        """Ingest a batch of results into the PostgreSQL database."""
        successful_results = [data for _, data in batch_results if data is not None]
        if not successful_results:
            print("No successful results in this batch to ingest.")
            return 0

        try:
            with psycopg2.connect(self.db_conn_string) as conn:
                with conn.cursor() as cur:
                    cur.execute("SET search_path TO ut_dogm;")

                    # Ingest API numbers
                    api_numbers = set(
                        res["api_number_guess"] for res in successful_results
                    )
                    if api_numbers:
                        api_values = [(number,) for number in api_numbers]
                        psycopg2.extras.execute_values(
                            cur,
                            "INSERT INTO api_well_number_repository (api_well_number) VALUES %s ON CONFLICT (api_well_number) DO NOTHING;",
                            api_values,
                        )

                    # Ingest main data
                    psycopg2.extras.execute_values(
                        cur,
                        """
                        INSERT INTO raw_well_attachment_storage (file_index, hash, url, server_filename, api_number_guess, file_s3_uri)
                        VALUES %s
                        ON CONFLICT (file_index) DO NOTHING;
                        """,
                        [
                            (
                                r["file_index"],
                                r["hash"],
                                r["url"],
                                r["server_filename"],
                                r["api_number_guess"],
                                r["file_s3_uri"],
                            )
                            for r in successful_results
                        ],
                    )
                    conn.commit()
            success_count = len(successful_results)
            print(f"Successfully ingested {success_count} records into Postgres.")
            return success_count
        except psycopg2.Error as e:
            print(f"Failed to ingest batch into Postgres: {e}")
            return 0

    def create_batches(self) -> List[List[int]]:
        """Create batches of indices to process."""
        all_indices = list(range(self.start_index, self.end_index))
        return [
            all_indices[i : i + self.batch_size]
            for i in range(0, len(all_indices), self.batch_size)
        ]

    async def run_async_scraping(self):
        """Main async function to process all indices and ingest to DB."""
        self.setup_directories_and_db()
        batches = self.create_batches()
        total_indices = self.end_index - self.start_index
        total_successful = 0

        print(
            f"Processing {total_indices} indices in {len(batches)} batches of {self.batch_size}"
        )

        connector = aiohttp.TCPConnector(limit=30, limit_per_host=20)
        async with aiohttp.ClientSession(connector=connector) as session:
            start_time = time.time()

            for batch_num, batch_indices in enumerate(batches, 1):
                print(
                    f"--- Processing Batch {batch_num}/{len(batches)} (indices {batch_indices[0]} to {batch_indices[-1]}) ---"
                )
                batch_start_time = time.time()

                tasks = [
                    self.process_single_request(session, index)
                    for index in batch_indices
                ]
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)

                clean_results = []
                for res in batch_results:
                    if isinstance(res, Exception):
                        print(f"Task failed with exception: {res}")
                    else:
                        clean_results.append(res)

                ingested_count = self.ingest_to_postgres(clean_results)
                total_successful += ingested_count

                batch_duration = time.time() - batch_start_time
                print(f"Batch {batch_num} completed in {batch_duration:.2f} seconds")

                if batch_num < len(batches):
                    await asyncio.sleep(1)

            total_duration = time.time() - start_time
            print("=== Processing Complete ===")
            print(f"Total time: {total_duration:.2f} seconds")
            print(
                f"Successfully processed and ingested: {total_successful}/{total_indices} indices"
            )


def main():
    """Main function to run the async PDF scraper and data ingest."""
    start_index = 20560
    end_index = 40000
    openscrapers_endpoint = (
        "http://localhost:33399/admin/direct_file_attachment_process"
    )
    # Make sure to set this environment variable
    batch_size = 5
    db_conn_string = os.environ.get("PARENT_UT_POSTGRES_CONNECTION_STRING") or ""

    scraper = PDFScraper(
        openscrapers_endpoint,
        start_index,
        end_index,
        batch_size,
        db_conn_string,
    )
    asyncio.run(scraper.run_async_scraping())


if __name__ == "__main__":
    main()

