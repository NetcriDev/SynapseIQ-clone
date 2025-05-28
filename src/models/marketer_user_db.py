import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

DB_CONFIG = {
    "dbname": "crash_records_001",
    "user": "synapseiq",
    "password": "SynapseIQ$2025",
    "host": "localhost",
    "port": 5432,
}

def create_marketing_tables_with_audit():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()

        # Tabla principal de usuarios de marketing
        cur.execute("""
        CREATE TABLE IF NOT EXISTS marketer_users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            full_name TEXT,
            hashed_password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'marketing',
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP,
            last_login_at TIMESTAMP
        );
        """)

        # Tabla de relación con columnas de auditoría
        cur.execute("""
        CREATE TABLE IF NOT EXISTS passenger_marketer_users (
            id SERIAL PRIMARY KEY,
            passenger_id INTEGER NOT NULL REFERENCES passengers(id) ON DELETE CASCADE,
            marketer_user_id INTEGER NOT NULL REFERENCES marketer_users(id) ON DELETE CASCADE,
            assigned_at TIMESTAMP DEFAULT NOW(),
            created_by TEXT,
            updated_by TEXT,
            updated_at TIMESTAMP,
            status TEXT DEFAULT 'active',
            UNIQUE(passenger_id, marketer_user_id)
        );
        """)

        print("Tablas 'marketing_users' y 'passenger_marketing_users' (con auditoría) creadas o ya existentes.")
        cur.close()
        conn.close()

    except Exception as e:
        print(f"Error al crear las tablas: {e}")

if __name__ == "__main__":
    create_marketing_tables_with_audit()
