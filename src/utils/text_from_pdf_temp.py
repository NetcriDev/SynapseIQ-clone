import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))  # Ajusta según nivel
os.chdir(PROJECT_ROOT)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


import psycopg2
from psycopg2.extras import RealDictCursor
from src.services.text_from_pdf import PdfProcessor

# Conexión a la base de datos
conn = psycopg2.connect(
        dbname="crash_records_001",
        user="synapseiq",
        password="SynapseIQ$2025",
        host="localhost",
        port="5432"
    )

# Crear cursor
cur = conn.cursor(cursor_factory=RealDictCursor)

# Ejecutar consulta
cur.execute("""
        SELECT report_number, state, original_document_location
        FROM incident_reports
        WHERE 
            (text_from_pdf IS NULL OR text_from_pdf = '')
            AND NOT source_url LIKE '%https://cris.dot.state.tx.us/public/Query/app/home%'
        ORDER BY id DESC
        LIMIT 100;
            """)

# Procesar resultados
pdfp = PdfProcessor()

for row in cur.fetchall():
    original_document_location = row["original_document_location"]
    report_number = row["report_number"]
    state = row["state"]
    pdfp.process_pdf_from_path(report_number, state, original_document_location)

# Cierre
cur.close()
conn.close()
