import os
import sys
import json
import psycopg2
import psycopg2.extras

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))  # Ajusta según nivel
os.chdir(PROJECT_ROOT)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.utils.logger_config import setup_logger
from config.config import get_connection
from datetime import datetime, timedelta
from src.parsers.parse_texto_from_pdf import PDFTextExtractor


# --- DIRECTORIOS Y LOGGER ---
#outputdata_folder = "/Users/cristianb/Documents/Python/rel8ed/Data"
outputdata_folder= "/home/data"

logger = setup_logger("Text_from_pdf", outputdata_folder)

# extractor = PDFTextExtractor()
# pdf_path = "/Users/cristianb/Documents/Python/rel8ed/SynapseIQ_staging/storage/winstonsalem/2509741.pdf"
# region = "winstonsalem"
# text = extractor.extract_text(pdf_path, region)
# json_string = json.dumps(text, indent=2, ensure_ascii=False)
# print(json_string)

# --- PROCESAMIENTO MASIVO ---
def pipeline_get_text_from_pdf():
    extractor = PDFTextExtractor()
    conn = get_connection()

    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT id, website, original_document_location, narrative
                FROM incident_reports
                WHERE website IS NOT NULL AND original_document_location IS NOT NULL AND state <> 'Texas' AND text_from_pdf IS NULL
                ORDER BY id DESC
                LIMIT 50
            """)
            rows = cur.fetchall()

            for row in rows:
                pdf_path = row["original_document_location"]
                region = row.get("website", "Desconocido")
                narrative = row.get("narrative", "Desconocido")

                if not os.path.isfile(pdf_path):
                    logger.warning(f"Archivo no encontrado: {pdf_path}")
                    continue

                text = extractor.extract_text(pdf_path, region, narrative)

                cur.execute(
                    "UPDATE incident_reports SET text_from_pdf = %s WHERE id = %s",
                    (text, row["id"])
                )
                conn.commit()
                logger.info(f"Actualizado texto para ID {row['id']} | Región: {region}")

    except Exception as e:
        logger.error(f"Error durante procesamiento masivo: {str(e)}")
    finally:
        conn.close()

if __name__ == "__main__":
    pipeline_get_text_from_pdf()





