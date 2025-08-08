import os

import psycopg2


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
