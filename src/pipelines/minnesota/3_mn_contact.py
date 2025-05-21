import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))  # Ajusta según nivel
os.chdir(PROJECT_ROOT)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pandas as pd
from src.utils.logger_config import setup_logger
from config.config import get_connection
from datetime import datetime, timedelta
from src.services.api_contact import DataIrisSession
from src.utils.utils_api_contact import DatabaseType


# --- DIRECTORIOS ---
outputdata_folder = "/Users/cristianb/Documents/Python/rel8ed/Data"
#outputdata_dir = "/home/data"

logger= setup_logger("Scheduled_execution", outputdata_folder)

# --- CONEXIÓN A BASE DE DATOS ---
conn = get_connection()
cur = conn.cursor()

# --- FILTRO DE FECHA ---
fecha_limite = (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d')

# --- CONSULTA DE REGISTROS INCOMPLETOS ---
query = """
    SELECT id, first_name, middle_name, last_name, age, state, city, street
    FROM (
        SELECT *
        FROM passengers
        WHERE website = 'minnesota'
        ORDER BY id DESC
        LIMIT 500
    ) sub
    WHERE
        phone2 IS NULL OR phone2 ILIKE 'n/a' OR phone2 ILIKE 'null' OR phone2 ILIKE 'none' OR trim(phone2) = ''
        OR contact_resolution IS NULL OR contact_resolution ILIKE 'n/a' OR contact_resolution ILIKE 'null' OR contact_resolution ILIKE 'none' OR trim(contact_resolution) = ''
"""

cur.execute(query, (fecha_limite,))
rows = cur.fetchall()

# --- SESIÓN DE CONTACTOS ---
sesion = DataIrisSession(token_file_path=os.path.join(outputdata_folder, "token.json"))

# --- PROCESAMIENTO DE CONTACTOS ---
for row in rows:
    pid, first_name, middle_name, last_name, age, state, city, address = row
    info_contact = DataIrisSession.extract_phone_if_valid(
        sesion.safe_get_contact_resolution(
            database_type=DatabaseType(1).name,
            first_name=first_name,
            last_name=last_name,
            middle_name=middle_name,
            age=age,
            state=state,
            city=city.split(",")[0].strip() if city else None
        )
    )
    logger.info(f"[Actualización] ID: {pid}, Contacto: {info_contact}")

    #Puedes actualizar los campos en la base:
    cur.execute("""
        UPDATE passengers
        SET phone2 = %s, contact_resolution = %s
        WHERE id = %s
        """, (
        (info_contact.get("CellPhone") or "") + ", " + (info_contact.get("Phone") or ""),
        str(info_contact.get("contact_resolution")), pid
        ))

conn.commit()
cur.close()
conn.close()








