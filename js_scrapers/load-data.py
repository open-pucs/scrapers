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
        libsql_client.Statement(
            "DROP TABLE IF EXISTS application_for_permit_drilling_granted;"
        ),
        libsql_client.Statement("DROP TABLE IF EXISTS historical_well_metadata;"),
        libsql_client.Statement("DROP TABLE IF EXISTS apd_permit_expiry;"),
        libsql_client.Statement("DROP TABLE IF EXISTS api_well_number_repository;"),
    ]
)


# Create tables
db.batch(
    [
        libsql_client.Statement(
            """
      CREATE TABLE IF NOT EXISTS api_well_number_repository (
        api_well_number TEXT PRIMARY KEY
      );
    """
        ),
        libsql_client.Statement(
            """
      CREATE TABLE IF NOT EXISTS wells (
        api_well_number TEXT,
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
        total_carbon_emissions REAL,
        FOREIGN KEY (api_well_number) REFERENCES api_well_number_repository(api_well_number)
      );
    """
        ),
        libsql_client.Statement(
            """
      CREATE TABLE IF NOT EXISTS permit_file_data (
        permit_id INTEGER PRIMARY KEY AUTOINCREMENT,
        api_well_number TEXT,
        log_category TEXT,
        log_type TEXT,
        date_posted DATE,
        pdf_link TEXT,
        operator TEXT,
        well_status TEXT,
        FOREIGN KEY (api_well_number) REFERENCES api_well_number_repository(api_well_number)
      );
    """
        ),
        libsql_client.Statement(
            """
      CREATE VIRTUAL TABLE IF NOT EXISTS wells_rtree USING rtree(
        id,
        min_lon, max_lon,
        min_lat, max_lat
      );
    """
        ),
        libsql_client.Statement(
            """
        CREATE TABLE IF NOT EXISTS application_for_permit_drilling_granted (
            date_posted_to_web DATE,
            date_approved DATE,
            apd_number INTEGER,
            county TEXT,
            operator TEXT,
            well_name TEXT,
            api_number TEXT,
            work_type TEXT,
            well_type TEXT,
            current_status TEXT,
            field TEXT,
            surface_location TEXT,
            qtr_qtr TEXT,
            section TEXT,
            township TEXT,
            range TEXT,
            utm_northings REAL,
            utm_eastings REAL,
            latitude REAL,
            longitude REAL,
            elevation REAL,
            planned_depth_md INTEGER,
            proposed_zone TEXT,
            directional_horizontal TEXT,
            confidential_well TEXT,
            FOREIGN KEY (api_number) REFERENCES api_well_number_repository(api_well_number)
        );
        """
        ),
        libsql_client.Statement(
            """
        CREATE TABLE IF NOT EXISTS historical_well_metadata (
            api_well_number TEXT,
            event_work_type TEXT,
            apd_approval DATE,
            spud_date_dry DATE,
            spud_date_rotary DATE,
            completion_date DATE,
            sundry_of_intent TEXT,
            sundry_work_complete TEXT,
            first_production TEXT,
            historical_well_status TEXT,
            well_type TEXT,
            producing_zone TEXT,
            td_md REAL,
            td_tvd REAL,
            pbtd_md REAL,
            pbtd_tvd REAL,
            production_test_method TEXT,
            oil_24hr_test TEXT,
            gas_24hr_test TEXT,
            water_24hr_test TEXT,
            choke TEXT,
            tubing_pressure TEXT,
            casing_pressure TEXT,
            dir_survey TEXT,
            cored TEXT,
            dst TEXT,
            completion_type TEXT,
            directional TEXT,
            horiz_laterals INTEGER,
            confidential TEXT,
            FOREIGN KEY (api_well_number) REFERENCES api_well_number_repository(api_well_number)
        );
        """
        ),
        libsql_client.Statement(
            """
        CREATE TABLE IF NOT EXISTS apd_permit_expiry (
            operator TEXT,
            api_number TEXT,
            well_name TEXT,
            work_type TEXT,
            date_approved DATE,
            date_permit_will_expire DATE,
            FOREIGN KEY (api_number) REFERENCES api_well_number_repository(api_well_number)
        );
        """
        ),
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
    api_well_numbers = set()
    for well in wells_reader:
        api_well_numbers.add(well.get("API Well Number"))

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
    for permit_row in permits_reader:
        api_well_numbers.add(permit_row[0])

with open(
    "/home/nicole/Documents/mycorrhiza/scrapers/js_scrapers/raw_data/permits_approved_all_raw_data.csv",
    "r",
    encoding="utf-8",
) as permits_approved_file:
    permits_approved_reader = csv.DictReader(permits_approved_file)
    for row in permits_approved_reader:
        api_well_numbers.add(row.get("API\nNumber"))

with open(
    "/home/nicole/Documents/mycorrhiza/scrapers/js_scrapers/raw_data/well_history_all.csv",
    "r",
    encoding="utf-8",
) as well_history_file:
    well_history_reader = csv.DictReader(well_history_file)
    for row in well_history_reader:
        api_well_numbers.add(row.get("API Well Number"))

with open(
    "/home/nicole/Documents/mycorrhiza/scrapers/js_scrapers/raw_data/all_permit_expiry_dates.csv",
    "r",
    encoding="utf-8",
) as permit_expiry_file:
    permit_expiry_reader = csv.DictReader(permit_expiry_file)
    for row in permit_expiry_reader:
        api_well_numbers.add(row.get("API\nNumber"))

api_well_number_statements = []
for api_well_number in api_well_numbers:
    if api_well_number:
        api_well_number_statements.append(
            libsql_client.Statement(
                "INSERT OR IGNORE INTO api_well_number_repository (api_well_number) VALUES (?)",
                [api_well_number],
            )
        )
db.batch(api_well_number_statements)


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
            if len(permit_row) > 3
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

def parse_date(date_string):
    if not date_string:
        return None
    for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(date_string, fmt).date().isoformat()
        except ValueError:
            pass
    return None

def load_application_for_permit_drilling_granted(db):
    with open(
        "/home/nicole/Documents/mycorrhiza/scrapers/js_scrapers/raw_data/permits_approved_all_raw_data.csv",
        "r",
        encoding="utf-8",
    ) as f:
        reader = csv.DictReader(f)
        statements = []
        for row in reader:
            statements.append(
                libsql_client.Statement(
                    """
                INSERT OR IGNORE INTO application_for_permit_drilling_granted (
                    date_posted_to_web, date_approved, apd_number, county, operator, well_name,
                    api_number, work_type, well_type, current_status, field, surface_location,
                    qtr_qtr, section, township, range, utm_northings, utm_eastings, latitude,
                    longitude, elevation, planned_depth_md, proposed_zone, directional_horizontal,
                    confidential_well
                ) VALUES (
                    :date_posted_to_web, :date_approved, :apd_number, :county, :operator, :well_name,
                    :api_number, :work_type, :well_type, :current_status, :field, :surface_location,
                    :qtr_qtr, :section, :township, :range, :utm_northings, :utm_eastings, :latitude,
                    :longitude, :elevation, :planned_depth_md, :proposed_zone, :directional_horizontal,
                    :confidential_well
                )
                """,
                    {
                        "date_posted_to_web": parse_date(
                            row.get("Date\nPosted to Web")
                        ),
                        "date_approved": parse_date(row.get("Date\nApproved")),
                        "apd_number": int(row.get("APD\nNumber", 0) or 0),
                        "county": row.get("County"),
                        "operator": row.get("Operator"),
                        "well_name": row.get("Well Name"),
                        "api_number": row.get("API\nNumber"),
                        "work_type": row.get("Work\nType"),
                        "well_type": row.get("Well\nType"),
                        "current_status": row.get("Current\nStatus"),
                        "field": row.get("Field"),
                        "surface_location": row.get("Surface Location"),
                        "qtr_qtr": row.get("Qtr Qtr"),
                        "section": row.get("Section"),
                        "township": row.get("Township"),
                        "range": row.get("Range"),
                        "utm_northings": float(row.get("UTM\nNorthings", 0) or 0),
                        "utm_eastings": float(row.get("UTM\nEastings", 0) or 0),
                        "latitude": float(row.get("Latitude", 0) or 0),
                        "longitude": float(row.get("Longitude", 0) or 0),
                        "elevation": float(row.get("Elevation", 0) or 0),
                        "planned_depth_md": int(
                            row.get("Planned\nDepth (MD)", 0) or 0
                        ),
                        "proposed_zone": row.get("Proposed\nZone"),
                        "directional_horizontal": row.get(
                            "Directional/\nHorizontal"
                        ),
                        "confidential_well": row.get("Confidential\nWell?"),
                    },
                )
            )
        db.batch(statements)

def load_historical_well_metadata(db):
    with open(
        "/home/nicole/Documents/mycorrhiza/scrapers/js_scrapers/raw_data/well_history_all.csv",
        "r",
        encoding="utf-8",
    ) as f:
        reader = csv.DictReader(f)
        statements = []
        for row in reader:
            statements.append(
                libsql_client.Statement(
                    """
                INSERT OR IGNORE INTO historical_well_metadata (
                    api_well_number, event_work_type, apd_approval, spud_date_dry, spud_date_rotary,
                    completion_date, sundry_of_intent, sundry_work_complete, first_production,
                    historical_well_status, well_type, producing_zone, td_md, td_tvd, pbtd_md,
                    pbtd_tvd, production_test_method, oil_24hr_test, gas_24hr_test, water_24hr_test,
                    choke, tubing_pressure, casing_pressure, dir_survey, cored, dst, completion_type,
                    directional, horiz_laterals, confidential
                ) VALUES (
                    :api_well_number, :event_work_type, :apd_approval, :spud_date_dry, :spud_date_rotary,
                    :completion_date, :sundry_of_intent, :sundry_work_complete, :first_production,
                    :historical_well_status, :well_type, :producing_zone, :td_md, :td_tvd, :pbtd_md,
                    :pbtd_tvd, :production_test_method, :oil_24hr_test, :gas_24hr_test, :water_24hr_test,
                    :choke, :tubing_pressure, :casing_pressure, :dir_survey, :cored, :dst, :completion_type,
                    :directional, :horiz_laterals, :confidential
                )
                """,
                    {
                        "api_well_number": row.get("API Well Number"),
                        "event_work_type": row.get("Event <br /> Work Type"),
                        "apd_approval": parse_date(row.get("APD <br /> Approval")),
                        "spud_date_dry": parse_date(row.get("Spud Date <br /> Dry")),
                        "spud_date_rotary": parse_date(
                            row.get("Spud Date <br /> Rotary")
                        ),
                        "completion_date": parse_date(row.get("Completion <br /> Date")),
                        "sundry_of_intent": row.get("Sundry of <br /> Intent"),
                        "sundry_work_complete": row.get("Sundry Work <br /> Complete"),
                        "first_production": row.get("First <br /> Production"),
                        "historical_well_status": row.get("Historical Well Status"),
                        "well_type": row.get("Well Type"),
                        "producing_zone": row.get("Producing <br /> Zone"),
                        "td_md": float(row.get("TD- <br /> MD", 0) or 0),
                        "td_tvd": float(row.get("TD- <br /> TVD", 0) or 0),
                        "pbtd_md": float(row.get("PBTD- <br /> MD", 0) or 0),
                        "pbtd_tvd": float(row.get("PBTD- <br /> TVD", 0) or 0),
                        "production_test_method": row.get("Production <br /> Test Method"),
                        "oil_24hr_test": row.get("Oil <br /> 24hr Test"),
                        "gas_24hr_test": row.get("Gas <br /> 24hr Test"),
                        "water_24hr_test": row.get("Water <br /> 24hr Test"),
                        "choke": row.get("Choke"),
                        "tubing_pressure": row.get("Tubing  <br /> Pressure"),
                        "casing_pressure": row.get("Casing  <br /> Pressure"),
                        "dir_survey": row.get("Dir. <br /> Survey"),
                        "cored": row.get("Cored"),
                        "dst": row.get("DST"),
                        "completion_type": row.get("Completion <br /> Type"),
                        "directional": row.get("Directional"),
                        "horiz_laterals": int(row.get("Horiz. <br /> Laterals", 0) or 0),
                        "confidential": row.get("Confidential?"),
                    },
                )
            )
        db.batch(statements)

def load_apd_permit_expiry(db):
    with open(
        "/home/nicole/Documents/mycorrhiza/scrapers/js_scrapers/raw_data/all_permit_expiry_dates.csv",
        "r",
        encoding="utf-8",
    ) as f:
        reader = csv.DictReader(f)
        statements = []
        for row in reader:
            statements.append(
                libsql_client.Statement(
                    """
                INSERT OR IGNORE INTO apd_permit_expiry (
                    operator, api_number, well_name, work_type, date_approved, date_permit_will_expire
                ) VALUES (
                    :operator, :api_number, :well_name, :work_type, :date_approved, :date_permit_will_expire
                )
                """,
                    {
                        "operator": row.get("Operator"),
                        "api_number": row.get("API\nNumber"),
                        "well_name": row.get("Well Name"),
                        "work_type": row.get("Work\nType"),
                        "date_approved": parse_date(row.get("Date\nApproved")),
                        "date_permit_will_expire": parse_date(
                            row.get("Date\nPermit Will\nExpire")
                        ),
                    },
                )
            )
        db.batch(statements)

load_application_for_permit_drilling_granted(db)
load_historical_well_metadata(db)
load_apd_permit_expiry(db)

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
