import csv
import os
import psycopg2
import psycopg2.extras
from datetime import datetime
import io

example_csv_schema = """file_index,hash,url,server_filename,api_number_guess,file_s3_uri
1,kiHB-wVuRzu-13izjC7ZoxXVum8FVN1aZz97xp6qLO8=,https://dataexplorer.ogm.utah.gov/api/Files?fileName=wellfile|1,007\4300730039.pdf,4300730039,https://openscrapers.sfo3.digitaloceanspaces.com/raw/file/kiHB-wVuRzu-13izjC7ZoxXVum8FVN1aZz97xp6qLO8=
2,T3De42JNsHsxUBtdS_iZ9mta9bNhMKX6o7JCUib24XM=,https://dataexplorer.ogm.utah.gov/api/Files?fileName=wellfile|2,007\4300711153.pdf,4300711153,https://openscrapers.sfo3.digitaloceanspaces.com/raw/file/T3De42JNsHsxUBtdS_iZ9mta9bNhMKX6o7JCUib24XM=
3,mSqcH_xhutW10t7ibTagfZW7iLW20CakECRrLNjOIzU=,https://dataexplorer.ogm.utah.gov/api/Files?fileName=wellfile|3,007\4300730037.pdf,4300730037,https://openscrapers.sfo3.digitaloceanspaces.com/raw/file/mSqcH_xhutW10t7ibTagfZW7iLW20CakECRrLNjOIzU=
4,3pUJyYeTket6S_Qejdt4AmURYPdD6AMKJCyzvD4hwuA=,https://dataexplorer.ogm.utah.gov/api/Files?fileName=wellfile|4,007\4300730033.pdf,4300730033,https://openscrapers.sfo3.digitaloceanspaces.com/raw/file/3pUJyYeTket6S_Qejdt4AmURYPdD6AMKJCyzvD4hwuA=
"""


def main():
    """
    Connects to the postgres instance, creates tables, and ingests CSV data.
    """
    conn_string = os.environ.get("PARENT_UT_POSTGRES_CONNECTION_STRING")
    if not conn_string:
        raise ValueError(
            "PARENT_UT_POSTGRES_CONNECTION_STRING environment variable not set"
        )

    conn = None
    try:
        conn = psycopg2.connect(conn_string)
        with conn.cursor() as cur:
            # Create schema and set search path
            cur.execute("CREATE SCHEMA IF NOT EXISTS ut_dogm;")
            cur.execute("SET search_path TO ut_dogm;")

            # Create tables
            cur.execute("""
                CREATE TABLE IF NOT EXISTS api_well_number_repository (
                    api_well_number TEXT PRIMARY KEY
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS raw_well_attachment_storage (
                    file_index INTEGER PRIMARY KEY,
                    hash TEXT,
                    url TEXT,
                    server_filename TEXT,
                    api_number_guess TEXT,
                    file_s3_uri TEXT,
                    FOREIGN KEY (api_number_guess) REFERENCES api_well_number_repository(api_well_number)
                );
            """)
            conn.commit()

            # Ingest data from the example CSV
            # Ingest data from the example CSV
            csv_file_path = "/home/nicole/Documents/mycorrhiza/scrapers/openscraper_processing/results.csv"
            with open(csv_file_path, "r") as f:
                csv_reader = csv.DictReader(f)
                rows = list(csv_reader)

                # Insert unique api_number_guess into api_well_number_repository
                api_numbers = set(row["api_number_guess"] for row in rows)
                if api_numbers:
                    api_values = [(number,) for number in api_numbers]
                    psycopg2.extras.execute_values(
                        cur,
                        "INSERT INTO api_well_number_repository (api_well_number) VALUES %s ON CONFLICT (api_well_number) DO NOTHING;",
                        api_values,
                    )
                    conn.commit()

                # Insert data into raw_well_attachment_storage
                if rows:
                    psycopg2.extras.execute_values(
                        cur,
                        """
                        INSERT INTO raw_well_attachment_storage (file_index, hash, url, server_filename, api_number_guess, file_s3_uri)
                        VALUES %s
                        ON CONFLICT (file_index) DO NOTHING;
                        """,
                        [tuple(row.values()) for row in rows],
                    )
                    conn.commit()

            print("Successfully ingested data.")

    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    main()

