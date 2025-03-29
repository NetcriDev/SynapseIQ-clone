import psycopg2

def create_crash_report_schema():
    conn = psycopg2.connect(
        dbname="crash_records",
        user="synapseiq",     #"cristianb",
        password="SynapseIQ$2025",# "Mozart503"
        host="localhost", 
        port="5432"   
    )

    cur = conn.cursor()

    # Table 1: crash_reports (incident + metadata)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS incident_reports (
        id SERIAL PRIMARY KEY,
        report_number TEXT NOT NULL UNIQUE,
        version_json TEXT,
        source_url TEXT,
        original_format TEXT,
        document_hash TEXT,
        responsible TEXT,
        generation_date TIMESTAMP,
        original_document_location TEXT,
        accident_datetime TIMESTAMP,
        city TEXT,
        street TEXT,
        state TEXT,
        zip TEXT,
        latitude DOUBLE PRECISION,
        longitude DOUBLE PRECISION,
        weather_condition TEXT,
        road_condition TEXT,
        crash_severity TEXT,
        number_of_units INTEGER,
        narrative TEXT,
        notes TEXT,
        json JSONB
    )
    """)

    # Table 2: vehicles (several by report)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS vehicles (
        id SERIAL PRIMARY KEY,
        incident_report_id INTEGER REFERENCES incident_reports(id) ON DELETE CASCADE,
        unit_number INTEGER,
        make TEXT,
        model TEXT,
        year INTEGER,
        color TEXT,
        license_plate_number TEXT,
        license_plate_state TEXT,
        license_plate_year INTEGER,
        vin TEXT,
        damage_severity TEXT,
        estimated_cost NUMERIC,
        insurance_company TEXT,
        policy_number TEXT,
        driver_name TEXT,
        driver_license TEXT,
        driver_state TEXT,
        owner_name TEXT,
        owner_address TEXT,
        owner_phone TEXT,
        notes TEXT
    )
    """)

    # Table 3: passengers (several by vehicle)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS passengers (
        id SERIAL PRIMARY KEY,
        vehicle_id INTEGER REFERENCES vehicles(id) ON DELETE CASCADE,
        role TEXT,
        name TEXT,
        age INTEGER,
        gender TEXT,
        license_number TEXT,
        injury_severity TEXT,
        phone1 TEXT,
        phone2 TEXT,
        notes TEXT
    )
    """)

    conn.commit()
    cur.close()
    conn.close()

create_crash_report_schema()

