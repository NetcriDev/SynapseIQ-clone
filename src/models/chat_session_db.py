import psycopg2


# Nota importante: Habilitar gen_random_uuid()
# La función gen_random_uuid() pertenece a la extensión pgcrypto. Si aún no la has habilitado, ejecuta esto una vez en tu base de datos:
# CREATE EXTENSION IF NOT EXISTS pgcrypto;
import psycopg2

try:
    # Conexión a la base de datos
    conn = psycopg2.connect(
        dbname="crash_records_001",
        user="synapseiq",
        password="SynapseIQ$2025",
        host="localhost",
        port="5432"
    )

    with conn.cursor() as cur:
        # Tabla de sesiones mejorada (sin UUID)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS chat_session (
                id SERIAL PRIMARY KEY,
                report_number TEXT NOT NULL,
                state TEXT,
                city TEXT,
                started_at TIMESTAMP DEFAULT NOW(),
                last_interaction TIMESTAMP DEFAULT NOW(),
                status TEXT DEFAULT 'active' CHECK (status IN ('active', 'closed', 'expired')),
                message_count INTEGER DEFAULT 0,
                duration_seconds INTEGER,
                model_id TEXT DEFAULT 'meta-llama/llama-3-2-11b-vision-instruct',
                text_from_pdf TEXT,
                document_location_ibm TEXT,
                metadata JSONB
            );
        """)

        # Tabla de mensajes (referencia por ID entero)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id SERIAL PRIMARY KEY,
                report_number TEXT NOT NULL,
                state TEXT,
                city TEXT,
                session_id INTEGER REFERENCES chat_session(id) ON DELETE CASCADE,
                role TEXT CHECK (role IN ('user', 'assistant')) NOT NULL,
                content TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)

    conn.commit()
    print("Tablas creadas correctamente.")

except Exception as e:
    print(f"Error: {e}")
    if conn:
        conn.rollback()

finally:
    if conn:
        conn.close()
