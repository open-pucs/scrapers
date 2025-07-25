import csv
import sqlite3

# Connect to the SQLite database
db = sqlite3.connect("wells.db")
cursor = db.cursor()


# Also it would be helpful if you could add a column into the sqlite file that would calculate the total amount of carbon emitted by each well. It should be something like :
# (({Cumulative
# Oil
# (Barrels)} * 0.43) + ({Cumulative
# Natural Gas
# (MCF)} * 0.055))


# "API Well Number","Operator","Well Name","Well Status","Well Type","Coalbed
# Methane
# Well?","Cumulative
# Oil
# (Barrels)","Cumulative
# Natural Gas
# (MCF)","Cumulative
# Water
# (Barrels)","Field Name","Surface
# Ownership","Mineral
# Lease","County","Qtr/Qtr","Section","Township-Range","FNL/FSL","FEL/FWL","UTM
# Eastings","UTM
# Northings","Latitude","Longitude","Elev .GR","Elev. DF","Elev. KB","Slant","TD","PBTD","Confidential"
# "4300130001","Bridger Petroleum Corp","Federal 1","Plugged & Abandoned","Dry Hole","N","0","0","0","WILDCAT                  ","Federal","Federal","BEAVER","C-SE","15","26S-17W","1320 S","1320 E","261573.0","4269690.0","38.543694","-113.73574","5205.0","","","Directional","8540.0","","N"
# "4300130003","Husky Oil Company","Federal 6-12","Location Abandoned - APD rescinded","Oil Well","N","0","0","0","WILDCAT                  ","Federal","Federal","BEAVER","SENW","12","26S-17W","1980 N","1980 W","264233.0","4271825.0","38.56362","-113.70597","5168.0","","","","","","N"
# "4300130004","Husky Oil Company","Federal 10-13","Plugged & Abandoned","Dry Hole","N","0","0","0","WILDCAT                  ","Federal","Federal","BEAVER","NWSE","13","26S-17W","1980 S","1980 E","264585.0","4269803.0","38.545513","-113.701256","5194.0","","","","7048.0","","N"
# "4300130005","Badger Oil Corporation","Lulu State 1","Plugged & Abandoned","Dry Hole","N","0","0","0","WILDCAT                  ","Fee","Federal","BEAVER","SENE","2","29S-8W","2158 N","510 E","350050.0","4242422.0","38.317383","-112.71527","5800.0","","","","11367.0","","N"
# "4300130006","Hunt Oil Company","USA 1-25","Plugged & Abandoned","Dry Hole","N","0","0","0","WILDCAT                  ","Federal","Federal","BEAVER","NENW","25","27S-16W","937 N","1975 W","273442.0","4257732.0","38.43914","-113.59582","","","6171.0","","12400.0","","N"
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


# Permit data csv (THE TITLES OF THE CSV DONT MEAN ANYTHING AND ARE MISALIGNED, FIGURE OUT WHAT THINGS SHOULD BE NAMED FROM THE DEFINITIONS)
# API Well Number,Well Name,Operator,Lease / Unit,Log Category,Log Type,Date Posted,PDF
# "4301353839","OTHER","PDF","08/04/2020","7966","13470","3778 KB","Download","SM Energy Company","Fritz 14-24-1S-2W","Oil Well","Producing","BLUEBELL","DUCHESNE","1S-2W","24"
# "4301353839","CEMENT BOND","PDF","08/04/2020","0","14248","10664 KB","Download","SM Energy Company","Fritz 14-24-1S-2W","Oil Well","Producing","BLUEBELL","DUCHESNE","1S-2W","24"
# "4301353839","OTHER","PDF","08/04/2020","8600","14248","2772 KB","Download","SM Energy Company","Fritz 14-24-1S-2W","Oil Well","Producing","BLUEBELL","DUCHESNE","1S-2W","24"
# "4301353839","SONIC","PDF","08/04/2020","8600","14248","2527 KB","Download","SM Energy Company","Fritz 14-24-1S-2W","Oil Well","Producing","BLUEBELL","DUCHESNE","1S-2W","24"
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
