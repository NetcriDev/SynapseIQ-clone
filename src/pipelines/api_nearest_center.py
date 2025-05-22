import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))  # Ajusta según nivel
os.chdir(PROJECT_ROOT)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pandas as pd
from src.utils.logger_config import setup_logger
from config.config import get_connection
from datetime import datetime, timedelta
from src.services.api_geocode_distance import HopeCenterDistancer


# --- DIRECTORIOS Y LOGGER ---
outputdata_folder = "/Users/cristianb/Documents/Python/rel8ed/Data"
logger = setup_logger("Scheduled_execution", outputdata_folder)


def seleccionar_direccion(address, street):
    # Define valores no válidos
    invalido = lambda x: x is None or str(x).strip().lower() in ['', 'none', 'null', '-', '_', 'n/a', 'UNKNOWN']

    if not invalido(address):
        return address.strip()
    elif not invalido(street):
        return street.strip()
    else:
        return None
    
    
api_distance = HopeCenterDistancer()

conn = get_connection()
try:
    cur = conn.cursor()

    # --- CONSULTA DE REGISTROS SIN COORDENADAS DE CENTRO ---
    cur.execute("""
        SELECT id, state, city, street, address
        FROM incident_reports
        WHERE 
            nearest_hope_d IS NULL
            AND (name_nearest_hope IS NULL OR trim(name_nearest_hope) = '')
            AND state <> 'Texas'
        ORDER BY id DESC
        LIMIT 10
    """)

    results = cur.fetchall()

    for row in results:
        incident_id, state, city, street, address = row
        try:
            addr_to_use = seleccionar_direccion(address, street)

            hope_center = api_distance.find_nearest_center(
                country="USA",
                state=state,
                city=city,
                street=addr_to_use
            )

            name, distance = hope_center if hope_center else ('-', None)

            logger.info(f"ID {incident_id} => {name} at {distance} km (dir usada: {addr_to_use})")

            cur.execute("""
                UPDATE incident_reports
                SET nearest_hope_d = %s,
                    name_nearest_hope = %s
                WHERE id = %s
            """, (distance, name, incident_id))

        except Exception as e:
            logger.exception(f"Error al procesar ID {incident_id}: {e}")

    conn.commit()
finally:
    try:
        if cur:
            cur.close()
    except Exception as e:
        logger.warning(f"No se pudo cerrar el cursor: {e}")
    try:
        if conn:
            conn.close()
    except Exception as e:
        logger.warning(f"No se pudo cerrar la conexión: {e}")
    logger.info("Actualización de incident_reports completada.")
