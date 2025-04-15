from PyPDF2 import PdfReader
from typing import List, Dict
import re
import os
from glob import glob
from src.utils.split_name import split_driver_name

# Función para leer líneas de texto desde un PDF
def read_pdf_lines(pdf_path: str) -> List[str]:
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    return text.splitlines()

# Función para agrupar datos por unidades
def extract_vehicle_units(lines: List[str]) -> List[Dict]:
    units = []
    i = 0
    current_unit = {}
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("Unit"):
            if current_unit:
                units.append(current_unit)
                current_unit = {}
            current_unit["unit_number"] = int(re.search(r'\d+', line).group())
        elif line == "Driver's Name":
            name = lines[i+1].strip()
            current_unit["driver_name"] = name
            first, middle, last = split_driver_name(name)
            current_unit["driver_first_name"] = first
            current_unit["driver_middle_name"] = middle
            current_unit["driver_last_name"] = last
            i += 1
        elif line == "Driver's Address":
            current_unit["driver_address"] = lines[i+1].strip()
            i += 1
        elif line == "Driver's Phone No.":
            current_unit["driver_phone"] = lines[i+1].strip()
            i += 1
        elif line == "Driver's License No":
            current_unit["driver_license"] = lines[i+1].strip()
            i += 1
        elif line == "Vehicle Make":
            current_unit["make"] = lines[i+1].strip()
            i += 1
        elif line == "Vehicle Model":
            current_unit["model"] = lines[i+1].strip()
            i += 1
        elif line == "Vehicle Year":
            current_unit["year"] = lines[i+1].strip()
            i += 1
        elif line.startswith("Plate No"):
            current_unit["license_plate_number"], current_unit["license_plate_state"] = [x.strip() for x in lines[i+1].split("/")]
            i += 1
        elif line == "Owner Name":
            current_unit["owner_name"] = lines[i+1].strip()
            i += 1
        elif line == "Owner Address":
            current_unit["owner_address"] = lines[i+1].strip()
            i += 1
        elif line == "Insurance Company":
            current_unit["insurance_company"] = lines[i+1].strip()
            i += 1
        elif line == "Insurance Policy No.":
            current_unit["policy_number"] = lines[i+1].strip()
            i += 1
        i += 1
    if current_unit:
        units.append(current_unit)
    return units

# Función para extraer datos generales del incidente
def extract_incident_metadata(lines: List[str]) -> Dict:
    data = {}
    for i, line in enumerate(lines):
        if line == "Agency Report No.":
            data["report_number"] = lines[i+1].strip()
        elif line == "IDOT Control Number":
            data["notes"] = "idot_control_number: " + str(lines[i+1].strip())
        elif line == "County":
            data["county"] = lines[i+1].strip()
            data["state"] = "Illinois"
        elif line == "City":
            data["city"] = lines[i+1].strip()
        elif line == "Crash Address":
            data["street"] = lines[i+1].strip()
        elif line == "Crash Date":
            data["accident_datetime"] = lines[i+1].strip()
    return data

# Función principal para procesar un PDF
def parse_crash_pdf(pdf_path: str) -> Dict:
    lines = read_pdf_lines(pdf_path)
    incident = extract_incident_metadata(lines)
    vehicles = extract_vehicle_units(lines)
    return {
        "incident": incident,
        "vehicles": vehicles
    }

# # Aplicar a los archivos cargados
# all_pdfs = glob("/ruta/a/pdfs/*.pdf")
# pdf_files = ["/Users/cristianb/Documents/Python/rel8ed/SynapseIQ_Lab_01/JJ145209.pdf", "/Users/cristianb/Documents/Python/rel8ed/SynapseIQ_Lab_01/JJ145492.pdf"]
# extracted_data = [parse_crash_pdf(path) for path in pdf_files]

# extracted_data
