import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

def create_database_if_not_exists():
    """Conecta a postgres y crea la base de datos si no existe"""
    try:
        # Primero conectamos a la base de datos postgres (que siempre existe)
        conn = psycopg2.connect(
            dbname="postgres",
            user="synapseiq",
            password="SynapseIQ$2025",
            host="localhost",
            port="5432"
        )
        
        # Para crear bases de datos
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        
        cur = conn.cursor()
        
        # Verificamos si la base de datos existe
        cur.execute("SELECT 1 FROM pg_database WHERE datname = 'crash_records_001'")
        exists = cur.fetchone()
        
        if not exists:
            print("Creando base de datos crash_records_001...")
            cur.execute("CREATE DATABASE crash_records_001")
            print("Base de datos creada exitosamente.")
        else:
            print("La base de datos crash_records_001 ya existe.")
            
        cur.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"Error al crear la base de datos: {e}")
        return False

def create_crash_report_schema():
    conn = psycopg2.connect(
        dbname="crash_records_001",
        user="synapseiq",     
        password="SynapseIQ$2025",
        host="localhost", 
        port="5432"   
    )

    cur = conn.cursor()

    # Table 1: crash_reports (incident + metadata)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS incident_reports (
        id SERIAL PRIMARY KEY,
        report_number TEXT NOT NULL,
        internal_report_number TEXT NOT NULL UNIQUE,
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
        nearest_center_d NUMERIC(10,2),
        nearest_hope_d NUMERIC(10,2),
        name_nearest_hope TEXT,
        notes TEXT,
        technical_notes TEXT,
        json JSONB,
        text_from_pdf TEXT,
        is_external TEXT,
        website TEXT,
        document_location_ibm TEXT,
        address TEXT
    )
    """)

    # Table 2: vehicles (several by report)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS vehicles (
        id SERIAL PRIMARY KEY,
        incident_report_id INTEGER REFERENCES incident_reports(id) ON DELETE CASCADE,
        report_number TEXT,
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
        driver_first_name TEXT,
        driver_middle_name TEXT,
        driver_last_name TEXT,
        driver_license TEXT,
        driver_state TEXT,
        driver_address TEXT,
        owner_name TEXT,
        owner_first_name TEXT,
        owner_middle_name TEXT,
        owner_last_name TEXT,
        owner_address TEXT,
        owner_phone TEXT,
        notes TEXT,
        technical_notes TEXT,
        website TEXT
    )
    """)

    # Table 3: passengers (several by vehicle)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS passengers (
        id SERIAL PRIMARY KEY,
        vehicle_id INTEGER REFERENCES vehicles(id) ON DELETE CASCADE,
        report_number TEXT,
        role TEXT,
        name TEXT,
        first_name TEXT,
        middle_name TEXT,
        last_name TEXT,
        age INTEGER,
        gender TEXT,
        state TEXT,
        city TEXT,
        street TEXT
        license_number TEXT,
        injury_severity TEXT,
        number_occupant INTEGER,
        year_birth INTEGER,
        phone1 TEXT,
        phone2 TEXT,
        contact_resolution TEXT,
        notes TEXT,
        technical_notes TEXT,
        website TEXT,
        address TEXT,
        insurance_company TEXT,
        hasphone TEXT,
        hasinsurance_details TEXT,
        hasname TEXT,
        over18 TEXT,
        hotlead TEXT
    )
    """)

    conn.commit()
    cur.close()
    conn.close()

def main():
    # Primero creamos la base de datos si no existe
    if create_database_if_not_exists():
        # Luego creamos las tablas
        create_crash_report_schema()
    else:
        print("No se pudo continuar con la creación de tablas debido a un error.")

if __name__ == "__main__":
    main()
