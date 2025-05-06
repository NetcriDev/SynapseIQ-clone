import psycopg2

def create_audit_log_table():
    try:
        conn = psycopg2.connect(
            dbname="crash_records_001",
            user="synapseiq",
            password="SynapseIQ$2025",
            host="localhost",
            port="5432"
        )
        cur = conn.cursor()

        cur.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id SERIAL PRIMARY KEY,
            table_name TEXT NOT NULL,
            record_id TEXT NOT NULL,
            action TEXT NOT NULL, -- 'INSERT', 'UPDATE', 'DELETE'
            old_data JSONB,
            old_data_text TEXT,       
            new_data JSONB,
            new_data_text TEXT,
            changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            changed_by TEXT,
            source TEXT
        )
        """)

        conn.commit()
        cur.close()
        conn.close()
        print("Tabla 'audit_log' creada o ya existente.")
    except Exception as e:
        print(f"Error al crear la tabla de auditoría: {e}")

if __name__ == "__main__":
    create_audit_log_table()
