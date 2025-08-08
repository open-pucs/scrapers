import csv
import os
import psycopg2
import psycopg2.extras
from datetime import datetime

# Connect to the database
conn_string = os.environ.get("PARENT_UT_POSTGRES_CONNECTION_STRING")
if not conn_string:
    raise ValueError(
        "PARENT_UT_POSTGRES_CONNECTION_STRING environment variable not set"
    )

conn = psycopg2.connect(conn_string)
cur = conn.cursor()

# Create schema
cur.execute("CREATE SCHEMA IF NOT EXISTS ut_dogm;")
conn.commit()

# Set search path to ut_dogm
cur.execute("SET search_path TO ut_dogm;")
conn.commit()

# Drop tables if they exist to ensure schema updates
cur.execute("DROP TABLE IF EXISTS wells CASCADE;")
cur.execute("DROP TABLE IF EXISTS permit_file_data CASCADE;")
cur.execute("DROP TABLE IF EXISTS wells_rtree CASCADE;")
cur.execute("DROP TABLE IF EXISTS application_for_permit_drilling_granted CASCADE;")
cur.execute("DROP TABLE IF EXISTS historical_well_metadata CASCADE;")
cur.execute("DROP TABLE IF EXISTS apd_permit_expiry CASCADE;")
conn.commit()


# Create tables
cur.execute("""
    CREATE TABLE IF NOT EXISTS api_well_number_repository (
        api_well_number TEXT UNIQUE PRIMARY KEY
    );
""")
cur.execute("""
    CREATE TABLE IF NOT EXISTS wells (
        api_well_number TEXT UNIQUE PRIMARY KEY,
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
""")
cur.execute("""
    CREATE TABLE IF NOT EXISTS permit_file_data (
        permit_id SERIAL UNIQUE PRIMARY KEY,
        api_well_number TEXT,
        log_category TEXT,
        log_type TEXT,
        date_posted DATE,
        pdf_link TEXT,
        operator TEXT,
        well_status TEXT,
        FOREIGN KEY (api_well_number) REFERENCES api_well_number_repository(api_well_number)
    );
""")
cur.execute("""
    CREATE TABLE IF NOT EXISTS application_for_permit_drilling_granted (
        date_posted_to_web DATE,
        date_approved DATE,
        apd_number INTEGER,
        county TEXT,
        operator TEXT,
        well_name TEXT,
        api_number TEXT UNIQUE PRIMARY KEY,
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
""")
cur.execute("""
    CREATE TABLE IF NOT EXISTS historical_well_metadata (
        api_well_number TEXT UNIQUE PRIMARY KEY,
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
""")
cur.execute("""
    CREATE TABLE IF NOT EXISTS apd_permit_expiry (
        operator TEXT,
        api_number TEXT UNIQUE PRIMARY KEY,
        well_name TEXT,
        work_type TEXT,
        date_approved DATE,
        date_permit_will_expire DATE,
        FOREIGN KEY (api_number) REFERENCES api_well_number_repository(api_well_number)
    );
""")
conn.commit()


# Load and insert wells data
api_well_numbers = set()
with open(
    "/home/nicole/Documents/mycorrhiza/scrapers/js_scrapers/raw_data/utah_dogm_well_metadata.csv",
    "r",
    encoding="utf-8",
) as wells_file:
    wells_reader = csv.DictReader(wells_file)
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
        api_well_number_statements.append((api_well_number,))

psycopg2.extras.execute_batch(
    cur,
    "INSERT INTO api_well_number_repository (api_well_number) VALUES (%s) ON CONFLICT (api_well_number) DO NOTHING",
    api_well_number_statements,
)
conn.commit()


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
            (
                well.get("API Well Number"),
                well.get("Operator"),
                well.get("Well Name"),
                well.get("Well Status"),
                well.get("Well Type"),
                well.get("Coalbed\nMethane\nWell?"),
                cum_oil,
                cum_gas,
                float(well.get("Cumulative\nWater\n(Barrels)", 0) or 0),
                well.get("Field Name"),
                well.get("Surface\nOwnership"),
                well.get("Mineral\nLease"),
                well.get("County"),
                well.get("Qtr/Qtr"),
                well.get("Section"),
                well.get("Township-Range"),
                well.get("FNL/FSL"),
                well.get("FEL/FWL"),
                float(well.get("Elev .GR", 0) or 0),
                float(well.get("Elev. DF", 0) or 0),
                float(well.get("Elev. KB", 0) or 0),
                well.get("Slant"),
                float(well.get("TD", 0) or 0),
                float(well.get("PBTD", 0) or 0),
                well.get("Confidential"),
                total_carbon_emissions,
            )
        )

    psycopg2.extras.execute_batch(
        cur,
        """
        INSERT INTO wells (
            api_well_number, operator, well_name, well_status, well_type,
            coalbed_methane_well, cumulative_oil_barrels, cumulative_natural_gas_mcf,
            cumulative_water_barrels, field_name, surface_ownership, mineral_lease,
            county, qtr_qtr, section, township_range, fnl_fsl, fel_fwl,
            elev_gr, elev_df, elev_kb, slant, td, pbtd, confidential, total_carbon_emissions
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (api_well_number) DO NOTHING
    """,
        well_statements,
    )
    psycopg2.extras.execute_batch(
        cur,
        """
        INSERT INTO wells_rtree (id, min_lon, max_lon, min_lat, max_lat)
        VALUES (%s, %s, %s, %s, %s)
    """,
        rtree_statements,
    )
    conn.commit()


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
            if len(permit_row) > 3 and permit_row[3]
            else None
        )
        permit_statements.append(
            (
                permit_row[0],
                permit_row[1],
                permit_row[2],
                date_posted.isoformat() if date_posted else None,
                permit_row[7],
                permit_row[8],
                permit_row[11],
            )
        )
    psycopg2.extras.execute_batch(
        cur,
        """
        INSERT INTO permit_file_data (
            api_well_number, log_category, log_type, date_posted, pdf_link, operator, well_status
        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
    """,
        permit_statements,
    )
    conn.commit()


def parse_date(date_string):
    if not date_string:
        return None
    for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(date_string, fmt).date().isoformat()
        except ValueError:
            pass
    return None


def load_application_for_permit_drilling_granted(cur, conn):
    with open(
        "/home/nicole/Documents/mycorrhiza/scrapers/js_scrapers/raw_data/permits_approved_all_raw_data.csv",
        "r",
        encoding="utf-8",
    ) as f:
        reader = csv.DictReader(f)
        statements = []
        for row in reader:
            statements.append(
                (
                    parse_date(row.get("Date\nPosted to Web")),
                    parse_date(row.get("Date\nApproved")),
                    int(row.get("APD\nNumber", 0) or 0),
                    row.get("County"),
                    row.get("Operator"),
                    row.get("Well Name"),
                    row.get("API\nNumber"),
                    row.get("Work\nType"),
                    row.get("Well\nType"),
                    row.get("Current\nStatus"),
                    row.get("Field"),
                    row.get("Surface Location"),
                    row.get("Qtr Qtr"),
                    row.get("Section"),
                    row.get("Township"),
                    row.get("Range"),
                    float(row.get("UTM\nNorthings", 0) or 0),
                    float(row.get("UTM\nEastings", 0) or 0),
                    float(row.get("Latitude", 0) or 0),
                    float(row.get("Longitude", 0) or 0),
                    float(row.get("Elevation", 0) or 0),
                    int(row.get("Planned\nDepth (MD)", 0) or 0),
                    row.get("Proposed\nZone"),
                    row.get("Directional/\nHorizontal"),
                    row.get("Confidential\nWell?"),
                )
            )
        psycopg2.extras.execute_batch(
            cur,
            """
            INSERT INTO application_for_permit_drilling_granted (
                date_posted_to_web, date_approved, apd_number, county, operator, well_name,
                api_number, work_type, well_type, current_status, field, surface_location,
                qtr_qtr, section, township, range, utm_northings, utm_eastings, latitude,
                longitude, elevation, planned_depth_md, proposed_zone, directional_horizontal,
                confidential_well
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (api_number) DO NOTHING
        """,
            statements,
        )
        conn.commit()


def load_historical_well_metadata(cur, conn):
    with open(
        "/home/nicole/Documents/mycorrhiza/scrapers/js_scrapers/raw_data/well_history_all.csv",
        "r",
        encoding="utf-8",
    ) as f:
        reader = csv.DictReader(f)
        statements = []
        for row in reader:
            statements.append(
                (
                    row.get("API Well Number"),
                    row.get("Event <br /> Work Type"),
                    parse_date(row.get("APD <br /> Approval")),
                    parse_date(row.get("Spud Date <br /> Dry")),
                    parse_date(row.get("Spud Date <br /> Rotary")),
                    parse_date(row.get("Completion <br /> Date")),
                    row.get("Sundry of <br /> Intent"),
                    row.get("Sundry Work <br /> Complete"),
                    row.get("First <br /> Production"),
                    row.get("Historical Well Status"),
                    row.get("Well Type"),
                    row.get("Producing <br /> Zone"),
                    float(row.get("TD- <br /> MD", 0) or 0),
                    float(row.get("TD- <br /> TVD", 0) or 0),
                    float(row.get("PBTD- <br /> MD", 0) or 0),
                    float(row.get("PBTD- <br /> TVD", 0) or 0),
                    row.get("Production <br /> Test Method"),
                    row.get("Oil <br /> 24hr Test"),
                    row.get("Gas <br /> 24hr Test"),
                    row.get("Water <br /> 24hr Test"),
                    row.get("Choke"),
                    row.get("Tubing  <br /> Pressure"),
                    row.get("Casing  <br /> Pressure"),
                    row.get("Dir. <br /> Survey"),
                    row.get("Cored"),
                    row.get("DST"),
                    row.get("Completion <br /> Type"),
                    row.get("Directional"),
                    int(row.get("Horiz. <br /> Laterals", 0) or 0),
                    row.get("Confidential?"),
                )
            )
        psycopg2.extras.execute_batch(
            cur,
            """
            INSERT INTO historical_well_metadata (
                api_well_number, event_work_type, apd_approval, spud_date_dry, spud_date_rotary,
                completion_date, sundry_of_intent, sundry_work_complete, first_production,
                historical_well_status, well_type, producing_zone, td_md, td_tvd, pbtd_md,
                pbtd_tvd, production_test_method, oil_24hr_test, gas_24hr_test, water_24hr_test,
                choke, tubing_pressure, casing_pressure, dir_survey, cored, dst, completion_type,
                directional, horiz_laterals, confidential
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (api_well_number) DO NOTHING
        """,
            statements,
        )
        conn.commit()


def load_apd_permit_expiry(cur, conn):
    with open(
        "/home/nicole/Documents/mycorrhiza/scrapers/js_scrapers/raw_data/all_permit_expiry_dates.csv",
        "r",
        encoding="utf-8",
    ) as f:
        reader = csv.DictReader(f)
        statements = []
        for row in reader:
            statements.append(
                (
                    row.get("Operator"),
                    row.get("API\nNumber"),
                    row.get("Well Name"),
                    row.get("Work\nType"),
                    parse_date(row.get("Date\nApproved")),
                    parse_date(row.get("Date\nPermit Will\nExpire")),
                )
            )
        psycopg2.extras.execute_batch(
            cur,
            """
            INSERT INTO apd_permit_expiry (
                operator, api_number, well_name, work_type, date_approved, date_permit_will_expire
            ) VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (api_number) DO NOTHING
        """,
            statements,
        )
        conn.commit()


load_application_for_permit_drilling_granted(cur, conn)
load_historical_well_metadata(cur, conn)
load_apd_permit_expiry(cur, conn)

cur.close()
conn.close()

print("Data loaded successfully into PostgreSQL!")
