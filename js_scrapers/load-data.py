import csv
import sqlite3

# Connect to the SQLite database
db = sqlite3.connect("wells.db")
cursor = db.cursor()

# Create tables
cursor.execute("""
  CREATE TABLE IF NOT EXISTS wells (
    api_well_number TEXT PRIMARY KEY,
    well_name TEXT,
    operator TEXT,
    lease_number TEXT,
    well_status TEXT,
    well_type TEXT,
    field TEXT,
    county TEXT,
    sec TEXT,
    twp TEXT,
    rng TEXT,
    mer TEXT,
    surf_own TEXT,
    cum_o REAL,
    cum_g REAL,
    cum_w REAL,
    lat REAL,
    long REAL,
    location TEXT,
    spud_date TEXT,
    comp_date TEXT,
    first_prod_date TEXT,
    gis_link TEXT,
    well_file_link TEXT
  );
""")

cursor.execute("""
  CREATE TABLE IF NOT EXISTS permits (
    permit_id INTEGER PRIMARY KEY AUTOINCREMENT,
    api_well_number TEXT,
    log_category TEXT,
    log_type TEXT,
    date_posted TEXT,
    pdf_link TEXT,
    FOREIGN KEY (api_well_number) REFERENCES wells(api_well_number)
  );
""")

# Load and insert wells data
with open(
    "/home/nicole/Documents/mycorrhiza/scrapers/js_scrapers/cypress/downloads/well_data_both_options.csv",
    "r",
    encoding="utf-8",
) as wells_file:
    wells_reader = csv.DictReader(wells_file)
    for well in wells_reader:
        cursor.execute(
            """
            INSERT OR IGNORE INTO wells (
                api_well_number, well_name, operator, lease_number, well_status,
                well_type, field, county, sec, twp, rng, mer, surf_own, cum_o,
                cum_g, cum_w, lat, long, location, spud_date, comp_date,
                first_prod_date, gis_link, well_file_link
            ) VALUES (
                :api_well_number, :well_name, :operator, :lease_number, :well_status,
                :well_type, :field, :county, :sec, :twp, :rng, :mer, :surf_own, :cum_o,
                :cum_g, :cum_w, :lat, :long, :location, :spud_date, :comp_date,
                :first_prod_date, :gis_link, :well_file_link
            )
        """,
            {
                "api_well_number": well.get("API Well Number"),
                "well_name": well.get("Well Name"),
                "operator": well.get("Operator"),
                "lease_number": well.get("Lease / Unit"),
                "well_status": well.get("Well Status"),
                "well_type": well.get("Well Type"),
                "field": well.get("Field"),
                "county": well.get("County"),
                "sec": well.get("Sec"),
                "twp": well.get("Twp"),
                "rng": well.get("Rng"),
                "mer": well.get("Mer"),
                "surf_own": well.get("Surf-Own"),
                "cum_o": well.get("Cum O"),
                "cum_g": well.get("Cum G"),
                "cum_w": well.get("Cum W"),
                "lat": well.get("Lat"),
                "long": well.get("Long"),
                "location": well.get("Location"),
                "spud_date": well.get("Spud"),
                "comp_date": well.get("Comp"),
                "first_prod_date": well.get("First Prod"),
                "gis_link": well.get("GIS"),
                "well_file_link": well.get("Well File"),
            },
        )

# Load and insert permits data
with open(
    "/home/nicole/Documents/mycorrhiza/scrapers/js_scrapers/cypress/downloads/utah-file-data-backup.csv",
    "r",
    encoding="utf-8",
) as permits_file:
    permits_reader = csv.DictReader(permits_file)
    for permit in permits_reader:
        cursor.execute(
            """
            INSERT INTO permits (
                api_well_number, log_category, log_type, date_posted, pdf_link
            ) VALUES (
                :api_well_number, :log_category, :log_type, :date_posted, :pdf_link
            )
        """,
            {
                "api_well_number": permit.get("API Well Number"),
                "log_category": permit.get("Log Category"),
                "log_type": permit.get("Log Type"),
                "date_posted": permit.get("Date Posted"),
                "pdf_link": permit.get("PDF"),
            },
        )

# Commit changes and close the connection
db.commit()
db.close()

print("Data loaded successfully!")
