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
# Create the computed view

cur.execute("DROP VIEW IF EXISTS wells_with_permit_extras;")
cur.execute("""
CREATE VIEW wells_with_permit_extras AS
SELECT
  w.*,
  COUNT(p.permit_id) AS permit_file_submission_count,
  MIN(p.date_posted) AS earliest_permit_file_submission_date,
  MAX(p.date_posted) AS latest_permit_file_submission_date,
  MAX(apd.date_approved) AS apd_approval_date,
  MAX(expiry.date_permit_will_expire) AS apd_expiry_date_if_availible
FROM wells w
INNER JOIN api_well_number_repository apir ON w.api_well_number = apir.api_well_number
INNER JOIN permit_file_data p ON apir.api_well_number = p.api_well_number
LEFT JOIN application_for_permit_drilling_granted apd ON apir.api_well_number = apd.api_number
LEFT JOIN apd_permit_expiry expiry ON apir.api_well_number = expiry.api_number
GROUP BY w.*;
""")
conn.commit()


cur.execute("DROP VIEW IF EXISTS wells_with_permit_extras_all_inclusive;")
cur.execute("""
CREATE VIEW wells_with_permit_extras_all_inclusive AS
SELECT
  w.*,
  COUNT(p.permit_id) AS permit_file_submission_count,
  MIN(p.date_posted) AS earliest_permit_file_submission_date,
  MAX(p.date_posted) AS latest_permit_file_submission_date,
  MAX(apd.date_approved) AS apd_approval_date,
  MAX(expiry.date_permit_will_expire) AS apd_expiry_date_if_availible
FROM wells w
INNER JOIN api_well_number_repository apir ON w.api_well_number = apir.api_well_number
LEFT JOIN permit_file_data p ON apir.api_well_number = p.api_well_number
LEFT JOIN application_for_permit_drilling_granted apd ON apir.api_well_number = apd.api_number
LEFT JOIN apd_permit_expiry expiry ON apir.api_well_number = expiry.api_number
GROUP BY w.*;
""")
conn.commit()


cur.execute("DROP VIEW IF EXISTS historical_wells_with_permit_extras_all_inclusive;")
cur.execute("""
CREATE VIEW historical_wells_with_permit_extras_all_inclusive AS
SELECT
  w.*,
  COUNT(p.permit_id) AS permit_file_submission_count,
  MIN(p.date_posted) AS earliest_permit_file_submission_date,
  MAX(p.date_posted) AS latest_permit_file_submission_date,
  MAX(apd.date_approved) AS apd_approval_date_from_other_data,
  MAX(expiry.date_permit_will_expire) AS apd_expiry_date_if_availible
FROM historical_well_metadata w
INNER JOIN api_well_number_repository apir ON w.api_well_number = apir.api_well_number
LEFT JOIN permit_file_data p ON apir.api_well_number = p.api_well_number
LEFT JOIN application_for_permit_drilling_granted apd ON apir.api_well_number = apd.api_number
LEFT JOIN apd_permit_expiry expiry ON apir.api_well_number = expiry.api_number
GROUP BY w.*;
""")
conn.commit()
