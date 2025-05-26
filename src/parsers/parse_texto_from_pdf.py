import os
import time
import sys
import json
import re
from typing import Dict
import pdfplumber
import pandas as pd
from datetime import datetime, timedelta
from src.utils.logger_config import setup_logger
from config.config import get_connection
from psycopg2.extras import RealDictCursor
from collections import defaultdict
import pdfplumber
import re

main_script_path = sys.path[0]
logger = setup_logger("Text_from_execution", main_script_path)
#from dotenv import load_dotenv
#load_dotenv()

def extract_generic(path: str) -> str:
    with pdfplumber.open(path) as pdf:
        return "\n".join(p.extract_text() or "" for p in pdf.pages)


def extract_kansas(path: str) -> dict:
    """
    Extract structured crash data from Kansas Highway Patrol PDF.
    Returns a dictionary organized into header fields, narrative, vehicles, drivers, etc.
    """

    with pdfplumber.open(path) as pdf:
        full_text = "\n".join(p.extract_text() or "" for p in pdf.pages)

    # Limpieza básica
    full_text = re.sub(r"\n{2,}", "\n", full_text).strip()

    # Separar la sección principal
    sections = re.split(r"(?=Case \d{4}-\d{6} Crash Information)", full_text)
    if len(sections) < 2:
        return {"raw_text": full_text, "error": "Unexpected structure"}

    body = sections[1]
    result = {
        "raw_text": full_text,
        "Header": {},
        "Sections": {}
    }

    # Dividir el cuerpo por secciones principales
    parts = re.split(
        r"\n(?=(Vehicle \d+ Information|Driver of Vehicle \d+ Information|Occupant \d+ of Vehicle \d+ Information|Crash Narrative))",
        body
    )

    # Procesar encabezado antes de la primera sección
    header_block = parts[0]
    for line in header_block.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            result["Header"][key.strip()] = value.strip()

    # Procesar las secciones del informe
    current_section = None
    for part in parts[1:]:
        if re.match(r"^(Vehicle \d+ Information|Driver of Vehicle \d+ Information|Occupant \d+ of Vehicle \d+ Information|Crash Narrative)$", part.strip()):
            current_section = part.strip()
            result["Sections"][current_section] = ""
        elif current_section:
            result["Sections"][current_section] += part.strip() + " "

    return str(result)


def extract_ohio(path: str) -> str:
    severity_map = {
        "1": "FATAL",
        "2": "SERIOUS INJURY, SUSPECTED",
        "3": "MINOR INJURY, SUSPECTED",
        "4": "INJURY POSSIBLE",
        "5": "PROPERTY DAMAGE ONLY"
    }

    try:
        with pdfplumber.open(path) as pdf:
            text = "\n".join(p.extract_text() or "" for p in pdf.pages)

            def extract_narrative(text: str) -> str:
                """
                Extrae la sección completa de narrativa desde 'NARRATIVE' hasta el siguiente bloque identificado.
                """
                # Usamos un delimitador que marca bien el final del bloque, permitiendo líneas multilínea
                match = re.search(
                    r"\bNARRATIVE\b\s*\n+(.*?)(?=\n(?:REPORT TAKEN BY|CRASH REPORTED DATE|DISPATCH DATE|SUPPLEMENT|\s{0,10}[A-Z ]{5,}\n))",
                    text,
                    re.DOTALL | re.IGNORECASE
                )
                if match:
                    narrative = match.group(1).strip()
                    # Normalizamos los saltos de línea
                    narrative = re.sub(r'\n+', ' ', narrative)
                    return narrative
                return "Narrative not found"

            def extract_crash_severity(text: str) -> dict:
                for line in text.splitlines():
                    match = re.search(r"\d{2}/\d{2}/\d{4} \d{2}:\d{2}\s+([1-5])\b", line)
                    if match:
                        code = match.group(1)
                        return {
                            "code": code,
                            "label": severity_map.get(code, "Unknown")
                        }
                return {"code": None, "label": "Not found"}

            def extract_unit_error(text: str) -> str:
                match = re.search(r"(\S+)\s+9\s+98\s+9", text)
                return match.group(1) if match else "Value before '9 98 9' not found"

            # Extraer datos
            narrative = extract_narrative(text)
            severity = extract_crash_severity(text)
            raz = extract_unit_error(text)

            # Formar texto de salida
            result = (
                f"Narrative: {narrative}\n"
                f"Crash Severity: {severity['code']} - {severity['label']}\n"
                f"Unit was at error: {raz}\n"
                f"Raw Text: {text}"
            )
            return result

    except Exception as e:
        return f"Error extracting data: {str(e)}"


def extract_winston_salem(path: str) -> str:
    """
    Extrae la narrativa y el texto completo (raw text) de un reporte PDF de Winston-Salem (DMV-349).
    Retorna ambos bloques concatenados en un solo string.
    """
    try:
        with pdfplumber.open(path) as pdf:
            text = "\n".join(p.extract_text() or "" for p in pdf.pages)

        # Buscar el bloque de narrativa
        match = re.search(
            r"85\s+NARRATIVE\s*\n*(.*?)(?=\n{2,}|\n\s*\d{2,}|\n\s*ORI|\n\s*Officer Name)",
            text,
            re.DOTALL | re.IGNORECASE
        )
        if match:
            narrative = match.group(1).strip()
            narrative = re.sub(r"\n+", " ", narrative)
        else:
            narrative = "Narrative not found"

        return (
            f"[WINSTON SALEM] Narrative:\n{narrative}\n\n"
            f"[WINSTON SALEM] Raw Text:\n{text.strip()}"
        )

    except Exception as e:
        return f"[WINSTON SALEM] Error: {str(e)}"
    

def extract_minnesota(path: str) -> str:
    try:
        with pdfplumber.open(path) as pdf:
            text = "\n".join(p.extract_text() or "" for p in pdf.pages)
        return text
    except Exception as e:
        pass





EXTRACTOR_MAP = {
    "kansas": extract_kansas,
    "ohio": extract_ohio,
    "winstonsalem": extract_winston_salem,
    "minnesota": extract_minnesota
}

class PDFTextExtractor:
    def __init__(self):
        self.conn = get_connection()

    def fetch_paths(self):
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT id, report_number, website, original_document_location, state
                FROM incident_reports 
                WHERE website IS NOT NULL AND website <> 'texas'
                ORDER BY id DESC
                LIMIT 100
            """)
            return cur.fetchall()

    def extract_text(self, pdf_path: str, region: str = "Desconocido", narrative: str = None) -> str:
        extractor_fn = EXTRACTOR_MAP.get(region.lower(), extract_generic)
        try:
            text_from_pdf = extractor_fn(pdf_path)
            #print(text_from_pdf)
            return (narrative or "") + "\n" + (text_from_pdf or "")
            
        except Exception as e:
            logger.error(f"Error extrayendo texto de {pdf_path}: {e}")
            return ""

    def run(self):
        records = self.fetch_paths()
        for record in records:
            path = record["website"]
            region = record.get("state", "Desconocido")

            if not os.path.isfile(path):
                logger.warning(f"Archivo no encontrado: {path}")
                continue

            text = self.extract_text(path, region)
            logger.info(f"ID: {record['id']} | Region: {region} | Texto parcial:\n{text[:300]}\n---")

if __name__ == "__main__":
    extractor = PDFTextExtractor()
    extractor.run()














