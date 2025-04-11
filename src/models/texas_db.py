
# database_setup_psycopg2_improved.py
import psycopg2
from config.config import get_connection
# Conexión
conn = get_connection()
conn.autocommit = True
cursor = conn.cursor()

# Crear tabla principal de reportes de accidentes
create_list_of_accident_report_table = """
CREATE TABLE IF NOT EXISTS list_of_accident_report (
    id SERIAL PRIMARY KEY,
    crash_id VARCHAR NOT NULL,
    internal_crash_id VARCHAR NOT NULL UNIQUE,
    agency VARCHAR,
    case_id VARCHAR,
    state VARCHAR,
    city VARCHAR,
    county VARCHAR,
    street_number VARCHAR,
    street VARCHAR,
    region VARCHAR,
    crash_date TIMESTAMP,
    crash_severity VARCHAR
);
"""

# Crear tabla de pasajeros con todas las columnas extra
create_passengers_table = """
CREATE TABLE IF NOT EXISTS passenger_report_list (
    id SERIAL PRIMARY KEY,
    crash_report_id INTEGER REFERENCES list_of_accident_report(id) ON DELETE CASCADE,
    crash_id VARCHAR,
    amount_damage VARCHAR,
    contributing_factors VARCHAR,
    fatal_crash_flag VARCHAR,
    street_number VARCHAR,
    nearest_trauma_center VARCHAR,
    nearest_trauma_center_distance NUMERIC(7, 4),
    contributing_factor_1 VARCHAR,
    contributing_factor_2 VARCHAR,
    contributing_factor_3 VARCHAR,
    driver_zip_code INTEGER,
    lessee_owner_zip_code INTEGER,
    vehicle_hit_and_run_flag VARCHAR,
    vin VARCHAR,
    person_age INTEGER,
    person_gender VARCHAR,
    person_injury_severity VARCHAR,
    person_non_suspected_serious_injury_count INTEGER,
    person_count_number INTEGER,
    physical_location_of_an_occupant VARCHAR
);
"""

try:
    cursor.execute(create_list_of_accident_report_table)
    print("Table 'list_of_accident_report' created successfully")
    
    cursor.execute(create_passengers_table)
    print("Table 'passengers' created successfully.")

except Exception as e:
    print(f"Error creating tables: {e}")

finally:
    cursor.close()
    conn.close()
