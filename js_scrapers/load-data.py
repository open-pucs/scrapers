import csv
import sqlite3

# Connect to the SQLite database
db = sqlite3.connect("wells.db")
cursor = db.cursor()

# Drop tables if they exist to ensure schema updates
cursor.execute("DROP TABLE IF EXISTS wells;")
cursor.execute("DROP TABLE IF EXISTS permits;")

# Create tables
cursor.execute("""
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
    utm_eastings REAL,
    utm_northings REAL,
    latitude REAL,
    longitude REAL,
    elev_gr REAL,
    elev_df REAL,
    elev_kb REAL,
    slant TEXT,
    td REAL,
    pbtd REAL,
    confidential TEXT,
    total_carbon_emissions REAL
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
    operator TEXT,
    well_status TEXT,
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
        cum_oil = float(well.get("Cumulative\nOil\n(Barrels)", 0) or 0)
        cum_gas = float(well.get("Cumulative\nNatural Gas\n(MCF)", 0) or 0)
        total_carbon_emissions = (cum_oil * 0.43) + (cum_gas * 0.055)

        cursor.execute(
            """
            INSERT OR IGNORE INTO wells (
                api_well_number, operator, well_name, well_status, well_type,
                coalbed_methane_well, cumulative_oil_barrels, cumulative_natural_gas_mcf,
                cumulative_water_barrels, field_name, surface_ownership, mineral_lease,
                county, qtr_qtr, section, township_range, fnl_fsl, fel_fwl,
                utm_eastings, utm_northings, latitude, longitude, elev_gr, elev_df,
                elev_kb, slant, td, pbtd, confidential, total_carbon_emissions
            ) VALUES (
                :api_well_number, :operator, :well_name, :well_status, :well_type,
                :coalbed_methane_well, :cumulative_oil_barrels, :cumulative_natural_gas_mcf,
                :cumulative_water_barrels, :field_name, :surface_ownership, :mineral_lease,
                :county, :qtr_qtr, :section, :township_range, :fnl_fsl, :fel_fwl,
                :utm_eastings, :utm_northings, :latitude, :longitude, :elev_gr, :elev_df,
                :elev_kb, :slant, :td, :pbtd, :confidential, :total_carbon_emissions
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
                "utm_eastings": float(well.get("UTM\nEastings", 0) or 0),
                "utm_northings": float(well.get("UTM\nNorthings", 0) or 0),
                "latitude": float(well.get("Latitude", 0) or 0),
                "longitude": float(well.get("Longitude", 0) or 0),
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

# Load and insert permits data
old_permit_data_path = "/home/nicole/Documents/mycorrhiza/scrapers/js_scrapers/cypress/downloads/utah_dogm_file_data-round-1.csv"
new_permit_data_path = "/home/nicole/Documents/mycorrhiza/scrapers/js_scrapers/cypress/downloads/get_all_permit_data_ad_hoc.csv"

with open(
    new_permit_data_path,
    "r",
    encoding="utf-8",
) as permits_file:
    # Skip the header row as it's misaligned
    permits_reader = csv.reader(permits_file)
    next(permits_reader)  # Skip header row
    for permit_row in permits_reader:
        cursor.execute(
            """
            INSERT INTO permits (
                api_well_number, log_category, log_type, date_posted, pdf_link, operator, well_status
            ) VALUES (
                :api_well_number, :log_category, :log_type, :date_posted, :pdf_link, :operator, :well_status
            )
        """,
            {
                "api_well_number": permit_row[0],
                "log_category": permit_row[1],
                "log_type": permit_row[2],
                "date_posted": permit_row[3],
                "pdf_link": permit_row[7],
                "operator": permit_row[8],
                "well_status": permit_row[11],
            },
        )

# Commit changes and close the connection
db.commit()
db.close()

print("Data loaded successfully!")
