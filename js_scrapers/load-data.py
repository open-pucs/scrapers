import csv
import os
import libsql_client
from datetime import datetime

# Connect to the database
db_url = os.environ.get("TURSO_DATABASE_URL")
auth_token = os.environ.get("TURSO_AUTH_TOKEN")

if db_url:
    # Connect to a remote Turso database
    db = libsql_client.create_client_sync(url=db_url, auth_token=auth_token)
else:
    # Connect to a local database file
    db = libsql_client.create_client_sync(url="file:wells.db")

# Drop tables if they exist to ensure schema updates
db.batch(
    [
        libsql_client.Statement("DROP TABLE IF EXISTS wells;"),
        libsql_client.Statement("DROP TABLE IF EXISTS permit_file_data;"),
        libsql_client.Statement("DROP TABLE IF EXISTS wells_rtree;"),
    ]
)

# Create tables
db.batch(
    [
        libsql_client.Statement("""
      CREATE TABLE IF NOT EXISTS wells (
        api_well_number TEXT PRIMARY KEY,
        operator TEXT,
        well_name TEXT,
        well_status TEXT,
        well_type TEXT,
        coalbed_methane_well TEXT,
        cumulative_oil_barrels REAL,
        cumulative_natural_gas_mcf REAL,
        cumulative_water_barrels REAL,
        field_name TEXT,
        surface_ownership TEXT,
        mineral_lease TEXT,
        county TEXT,
        qtr_qtr TEXT,
        section TEXT,
        township_range TEXT,
        fnl_fsl TEXT,
        fel_fwl TEXT,
        elev_gr REAL,
        elev_df REAL,
        elev_kb REAL,
        slant TEXT,
        td REAL,
        pbtd REAL,
        confidential TEXT,
        total_carbon_emissions REAL
      );
    """),
        libsql_client.Statement("""
      CREATE TABLE IF NOT EXISTS permit_file_data (
        permit_id INTEGER PRIMARY KEY AUTOINCREMENT,
        api_well_number TEXT,
        log_category TEXT,
        log_type TEXT,
        date_posted DATE,
        pdf_link TEXT,
        operator TEXT,
        well_status TEXT,
        FOREIGN KEY (api_well_number) REFERENCES wells(api_well_number)
      );
    """),
        libsql_client.Statement("""
      CREATE VIRTUAL TABLE IF NOT EXISTS wells_rtree USING rtree(
        id,
        min_lon, max_lon,
        min_lat, max_lat
      );
    """),
    ]
)


# Load and insert wells data
with open(
    "/home/nicole/Documents/mycorrhiza/scrapers/js_scrapers/raw_data/utah_dogm_well_metadata.csv",
    "r",
    encoding="utf-8",
) as wells_file:
    wells_reader = csv.DictReader(wells_file)
    well_statements = []
    rtree_statements = []
    for well in wells_reader:
        cum_oil = float(well.get("Cumulative\nOil\n(Barrels)", 0) or 0)
        cum_gas = float(well.get("Cumulative\nNatural Gas\n(MCF)", 0) or 0)
        total_carbon_emissions = (cum_oil * 0.43) + (cum_gas * 0.055)

        well_statements.append(
            libsql_client.Statement(
                """
            INSERT OR IGNORE INTO wells (
                api_well_number, operator, well_name, well_status, well_type,
                coalbed_methane_well, cumulative_oil_barrels, cumulative_natural_gas_mcf,
                cumulative_water_barrels, field_name, surface_ownership, mineral_lease,
                county, qtr_qtr, section, township_range, fnl_fsl, fel_fwl,
                elev_gr, elev_df, elev_kb, slant, td, pbtd, confidential, total_carbon_emissions
            ) VALUES (
                :api_well_number, :operator, :well_name, :well_status, :well_type,
                :coalbed_methane_well, :cumulative_oil_barrels, :cumulative_natural_gas_mcf,
                :cumulative_water_barrels, :field_name, :surface_ownership, :mineral_lease,
                :county, :qtr_qtr, :section, :township_range, :fnl_fsl, :fel_fwl,
                :elev_gr, :elev_df, :elev_kb, :slant, :td, :pbtd, :confidential, :total_carbon_emissions
            )
            """,
                {
                    "api_well_number": well.get("API Well Number"),
                    "operator": well.get("Operator"),
                    "well_name": well.get("Well Name"),
                    "well_status": well.get("Well Status"),
                    "well_type": well.get("Well Type"),
                    "coalbed_methane_well": well.get("Coalbed\nMethane\nWell?"),
                    "cumulative_oil_barrels": cum_oil,
                    "cumulative_natural_gas_mcf": cum_gas,
                    "cumulative_water_barrels": float(
                        well.get("Cumulative\nWater\n(Barrels)", 0) or 0
                    ),
                    "field_name": well.get("Field Name"),
                    "surface_ownership": well.get("Surface\nOwnership"),
                    "mineral_lease": well.get("Mineral\nLease"),
                    "county": well.get("County"),
                    "qtr_qtr": well.get("Qtr/Qtr"),
                    "section": well.get("Section"),
                    "township_range": well.get("Township-Range"),
                    "fnl_fsl": well.get("FNL/FSL"),
                    "fel_fwl": well.get("FEL/FWL"),
                    "elev_gr": float(well.get("Elev .GR", 0) or 0),
                    "elev_df": float(well.get("Elev. DF", 0) or 0),
                    "elev_kb": float(well.get("Elev. KB", 0) or 0),
                    "slant": well.get("Slant"),
                    "td": float(well.get("TD", 0) or 0),
                    "pbtd": float(well.get("PBTD", 0) or 0),
                    "confidential": well.get("Confidential"),
                    "total_carbon_emissions": total_carbon_emissions,
                },
            )
        )
        api_well_number = well.get("API Well Number")
        longitude = float(well.get("Longitude", 0) or 0)
        latitude = float(well.get("Latitude", 0) or 0)

        if api_well_number and longitude and latitude:
            rtree_statements.append(
                libsql_client.Statement(
                    """
                INSERT INTO wells_rtree (id, min_lon, max_lon, min_lat, max_lat)
                VALUES (?, ?, ?, ?, ?)
                """,
                    [
                        int(api_well_number),
                        longitude,
                        longitude,
                        latitude,
                        latitude,
                    ],
                )
            )
    db.batch(well_statements)
    db.batch(rtree_statements)

# Load and insert permits data
new_permit_data_path = "/home/nicole/Documents/mycorrhiza/scrapers/js_scrapers/raw_data/get_all_permit_file_data.csv"

with open(
    new_permit_data_path,
    "r",
    encoding="utf-8",
) as permits_file:
    # Skip the header row as it's misaligned
    permits_reader = csv.reader(permits_file)
    next(permits_reader)  # Skip header row
    permit_statements = []
    for permit_row in permits_reader:
        date_posted = (
            datetime.strptime(permit_row[3], "%m/%d/%Y").date()
            if permit_row[3]
            else None
        )
        permit_statements.append(
            libsql_client.Statement(
                """
            INSERT INTO permit_file_data (
                api_well_number, log_category, log_type, date_posted, pdf_link, operator, well_status
            ) VALUES (
                :api_well_number, :log_category, :log_type, :date_posted, :pdf_link, :operator, :well_status
            )
        """,
                {
                    "api_well_number": permit_row[0],
                    "log_category": permit_row[1],
                    "log_type": permit_row[2],
                    "date_posted": date_posted.isoformat() if date_posted else None,
                    "pdf_link": permit_row[7],
                    "operator": permit_row[8],
                    "well_status": permit_row[11],
                },
            )
        )
    db.batch(permit_statements)

# Create the computed view
db.execute("DROP VIEW IF EXISTS wells_with_permit_summary;")
db.execute("""
CREATE VIEW IF NOT EXISTS wells_with_permit_summary AS
SELECT
  w.*,
  COUNT(p.permit_id) AS permit_count,
  MIN(p.date_posted) AS earliest_permit_date,
  MAX(p.date_posted) AS latest_permit_date
FROM wells w
JOIN permit_file_data p ON w.api_well_number = p.api_well_number
GROUP BY w.api_well_number;
""")

db.close()

print("Data loaded successfully!")
