
import * as fs from 'fs';
import * as Papa from 'papaparse';
import * as sqlite from 'better-sqlite3';

const db = new sqlite('wells.db');

// Create tables
db.exec(`
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
`);

db.exec(`
  CREATE TABLE IF NOT EXISTS permits (
    permit_id INTEGER PRIMARY KEY AUTOINCREMENT,
    api_well_number TEXT,
    log_category TEXT,
    log_type TEXT,
    date_posted TEXT,
    pdf_link TEXT,
    FOREIGN KEY (api_well_number) REFERENCES wells(api_well_number)
  );
`);

// Load and insert wells data
const wellsCsv = fs.readFileSync('/home/nicole/Documents/mycorrhiza/scrapers/js_scrapers/cypress/downloads/well_data_both_options.csv', 'utf8');
const wellsData = Papa.parse(wellsCsv, { header: true }).data;

const insertWell = db.prepare(`
  INSERT OR IGNORE INTO wells (
    api_well_number,
    well_name,
    operator,
    lease_number,
    well_status,
    well_type,
    field,
    county,
    sec,
    twp,
    rng,
    mer,
    surf_own,
    cum_o,
    cum_g,
    cum_w,
    lat,
    long,
    location,
    spud_date,
    comp_date,
    first_prod_date,
    gis_link,
    well_file_link
  ) VALUES (
    @api_well_number,
    @well_name,
    @operator,
    @lease_number,
    @well_status,
    @well_type,
    @field,
    @county,
    @sec,
    @twp,
    @rng,
    @mer,
    @surf_own,
    @cum_o,
    @cum_g,
    @cum_w,
    @lat,
    @long,
    @location,
    @spud_date,
    @comp_date,
    @first_prod_date,
    @gis_link,
    @well_file_link
  )
`);

db.transaction((wells) => {
  for (const well of wells) {
    insertWell.run({
      api_well_number: well['API Well Number'],
      well_name: well['Well Name'],
      operator: well['Operator'],
      lease_number: well['Lease / Unit'],
      well_status: well['Well Status'],
      well_type: well['Well Type'],
      field: well['Field'],
      county: well['County'],
      sec: well['Sec'],
      twp: well['Twp'],
      rng: well['Rng'],
      mer: well['Mer'],
      surf_own: well['Surf-Own'],
      cum_o: well['Cum O'],
      cum_g: well['Cum G'],
      cum_w: well['Cum W'],
      lat: well['Lat'],
      long: well['Long'],
      location: well['Location'],
      spud_date: well['Spud'],
      comp_date: well['Comp'],
      first_prod_date: well['First Prod'],
      gis_link: well['GIS'],
      well_file_link: well['Well File']
    });
  }
})(wellsData);

// Load and insert permits data
const permitsCsv = fs.readFileSync('/home/nicole/Documents/mycorrhiza/scrapers/js_scrapers/cypress/downloads/utah-file-data-backup.csv', 'utf8');
const permitsData = Papa.parse(permitsCsv, { header: true }).data;

const insertPermit = db.prepare(`
  INSERT INTO permits (
    api_well_number,
    log_category,
    log_type,
    date_posted,
    pdf_link
  ) VALUES (
    @api_well_number,
    @log_category,
    @log_type,
    @date_posted,
    @pdf_link
  )
`);

db.transaction((permits) => {
  for (const permit of permits) {
    insertPermit.run({
      api_well_number: permit['API Well Number'],
      log_category: permit['Log Category'],
      log_type: permit['Log Type'],
      date_posted: permit['Date Posted'],
      pdf_link: permit['PDF']
    });
  }
})(permitsData);

console.log('Data loaded successfully!');
db.close();
