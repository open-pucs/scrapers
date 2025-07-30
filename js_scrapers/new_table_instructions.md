# Notes about libsql

The following extensions are always-on and available:
Extension Version Description
JSON Built-in Work with JSON data in SQLite.
FTS5 Built-in Full-text search and indexing.
R\*Tree Built-in Indexing and querying spatial data.
SQLean Crypto 0.24.1 Hashing, message digest, encoding, and decoding.
SQLean Fuzzy 0.24.1 Fuzzy string matching and phonetics. A fork of Spellfix1 with improvements.
SQLean Math 0.24.1 Advanced mathematical calculations.
SQLean Stats 0.24.1 Common statistical functions with SQLite.
SQLean Text 0.24.1 String manipulation (reverse, split) with SQLite.
SQLean UUID 0.24.1 Limited support for RFC 4122 compliant UUIDs.

# New Tables:

Could you create new tables with the following data:

- Name: application_for_permit_drilling_granted
- FileName:
  /home/nicole/Documents/mycorrhiza/scrapers/js_scrapers/raw_data/permits_approved_all_raw_data.csv

```csv

"Date
Posted to Web","Date
Approved","APD
Number","County","Operator","Well Name","API
Number","Work
Type","Well
Type","Current
Status","Field","Surface Location","Qtr Qtr","Section","Township","Range","UTM
Northings","UTM
Eastings","Latitude","Longitude","Elevation","Planned
Depth (MD)","Proposed
Zone","Directional/
Horizontal","Confidential
Well?"
"07/22/2025","07/21/2025","16380","UINTAH","Anschutz Exploration Corporation","RAINIER FED 1124-23-35-14 MCH","4304757848","DRILL","Gas Well","Approved Permit","UNDESIGNATED","2179 FNL 2316 FWL","LOT4","23","11S","24E","4412526.0","654040.0","39.848793","-109.19942","6020","20781","MNCS ","HORIZONTAL","Y"
"07/10/2025","07/09/2025","16309","UINTAH","Middle Fork Energy Uinta, LLC","ECHO 9A1-36-622","4304757810","DRILL","Gas Well","Approved Permit","UNDESIGNATED","345 FNL 760 FEL","LOT1","1","7S","22E","4456683.0","637646.0","40.24929","-109.38159","5139","12452","MVRD ","DIRECTIONAL","Y"
"07/10/2025","07/09/2025","16308","UINTAH","Middle Fork Energy Uinta, LLC","ECHO 8D4-36-622","4304757811","DRILL","Gas Well","Approved Permit","UNDESIGNATED","330 FNL 760 FEL","LOT1","1","7S","22E","4456687.0","637646.0","40.24933","-109.38159","5138","12507","MVRD ","DIRECTIONAL","Y"
```

- Name: historical_well_metadata
- FileName:
  /home/nicole/Documents/mycorrhiza/scrapers/js_scrapers/raw_data/well_history_all.csv
-

```csv
"API Well Number","Event <br /> Work Type","APD <br /> Approval","Spud Date <br /> Dry","Spud Date <br /> Rotary","Completion <br /> Date","Sundry of <br /> Intent","Sundry Work <br /> Complete","First <br /> Production","Historical Well Status","Well Type","Producing <br /> Zone","TD- <br /> MD","TD- <br /> TVD","PBTD- <br /> MD","PBTD- <br /> TVD","Production <br /> Test Method","Oil <br /> 24hr Test","Gas <br /> 24hr Test","Water <br /> 24hr Test","Choke","Tubing  <br /> Pressure","Casing  <br /> Pressure","Dir. <br /> Survey","Cored","DST","Completion <br /> Type","Directional","Horiz. <br /> Laterals","Confidential?"
"4300130001","DRILL","12/13/1974","12/28/1974","","03/21/1975","","","","Plugged & Abandoned","","","8540.0","","0.0","0.0","","","","","","","","Y","N","Y","","Directional","0","N"
"4300130003","DRILL","11/24/1980","","","","","","","Location Abandoned - APD rescinded","","","0.0","","0.0","0.0","","","","","","","","N","N","N","","","0","N"
"4300130004","DRILL","11/25/1980","02/02/1981","","03/08/1981","","","","Plugged & Abandoned","","","7048.0","","0.0","0.0","","","","","","","","N","N","N","","Vertical","0","N"
"4300130005","DRILL","01/09/1981","03/31/1981","04/19/1981","07/02/1981","","","","Plugged & Abandoned","","","11367.0","","0.0","0.0","","","","","","","","N","N","N","","Vertical","0","N"
"4300130006","DRILL","02/24/1993","04/19/1993","","02/19/1994","","","","Plugged & Abandoned","","","12400.0","","0.0","0.0","","","","","","","","Y","N","N","","Vertical","0","N"
"4300130007","DRILL","06/10/2008","08/21/2008","09/20/2008","11/22/2008","","","","Plugged & Abandoned","","","11854.0","","0.0","0.0","","","","","","","","N","N","N","","Vertical","0","N"
```

- Name: apd_permit_expiary
- FileName:
  /home/nicole/Documents/mycorrhiza/scrapers/js_scrapers/raw_data/all_permit_expiary_dates.csv

```csv
"Operator","API
Number","Well Name","Work
Type","Date
Approved","Date
Permit Will
Expire"
"A1 Lithium, Inc","4301950095","LCW-1","DRILL","10/15/2021","10/15/2024"
"A1 Lithium, Inc","4301950096","LCW-2","DRILL","10/18/2021","10/15/2024"
"AC Oil, LLC","4304757198","AC-4D","DRILL","02/21/2025","02/21/2026"
"American Helium Operating, LLC","4303750087","Gallant Fox 1","DRILL","03/05/2020","03/05/2024"
"American Helium Operating, LLC","4303750090","Big Indian Fed 24-31B-30-25","DRILL","05/19/2022","05/19/2024"
"American Potash, LLC","4301950111","AP-S-2 Duma Point","DRILL","01/08/2024","01/07/2025"
"American Potash, LLC","4301950112","Ten Mile AP-S-16","DRILL","01/08/2024","01/07/2025"
"American Potash, LLC","4301950113","Mineral Springs AP-S-36 ","DRILL","01/08/2024","01/07/2025"
"American Potash, LLC","4301950114","AP-F-34 Keg Springs","DRILL","01/08/2024","01/07/2025"
"American Potash, LLC","4301950115","AP-F-24 Trail Canyon","DRILL","01/08/2024","01/07/2025"
"American Potash, LLC","4301950116","AP-F-28 Lost World","DRILL","01/08/2024","01/07/2025"
"American Potash, LLC","4301950117","AP-F-12 Hey Joe","DRILL","01/08/2024","01/07/2025"
"Anschutz Exploration Corporation","4304757524","CENTER FORK FED 12-24-17-20-14MCH","DRILL","02/22/2024","02/21/2025"
"Anschutz Exploration Corporation","4304757564","DRUMLIN FED 10-24-30-19-3 MCH","DRILL","10/01/2024","10/01/2025"
"Anschutz Exploration Corporation","4304757566","DRUMLIN FED 10-24-30-5-13 MCH","DRILL","06/25/2024","06/25/2025"
"Anschutz Exploration Corporation","4304757567","DRUMLIN FED 10-24-30-5-14 MCH","DRILL","10/01/2024","10/01/2025"
```
