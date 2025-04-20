from src.parsers.chicago_pdf_parse import parse_crash_pdf
from config.config import get_connection
import psycopg2, os
import json
from datetime import datetime
from glob import glob

def insert_incident_and_vehicles_chi(data: dict, path_output: str):
    try:
        conn = get_connection()
        cur = conn.cursor()

        # Parsear fecha
        accident_dt = datetime.strptime(data['incident']['accident_datetime'], "%m/%d/%Y")

        # Insertar en incident_reports
        cur.execute("""
            INSERT INTO incident_reports (
                report_number,
                internal_report_number,
                notes,
                city,
                street,
                state,
                accident_datetime,
                json,
                original_document_location
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            data['incident']['report_number'],
            "chi" + str(data['incident']['report_number']),  # fallback
            data['incident'].get('notes'),
            data['incident']['city'],
            data['incident']['street'],
            data['incident']['state'],
            accident_dt,
            json.dumps(data),
            os.path.join(path_output,"chicago",data['incident']['report_number'] + ".pdf")
        ))

        incident_id = cur.fetchone()[0]

        # Insertar vehículos
        for v in data['vehicles']:
            cur.execute("""
                INSERT INTO vehicles (
                    incident_report_id,
                    unit_number,
                    make,
                    model,
                    year,
                    license_plate_number,
                    license_plate_state,
                    insurance_company,
                    policy_number,
                    driver_name,
                    driver_first_name,
                    driver_middle_name,
                    driver_last_name,
                    driver_license,
                    driver_address,
                    owner_name,
                    owner_address
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                incident_id,
                v.get('unit_number'),
                v.get('make'),
                v.get('model'),
                int(v['year']) if v.get('year') and v['year'].isdigit() else None,
                v.get('license_plate_number'),
                v.get('license_plate_state'),
                v.get('insurance_company'),
                v.get('policy_number'),
                v.get('driver_name'),
                v.get('driver_first_name'),
                v.get('driver_middle_name'),
                v.get('driver_last_name'),
                v.get('driver_license'),
                v.get('driver_address'),
                v.get('owner_name'),
                v.get('owner_address')
            ))

        conn.commit()
        print(" Inserción exitosa del incidente y vehículos.")
        cur.close()
        conn.close()

    except Exception as e:
        print(f" Error en la inserción: {e}")

# # Aplicar a los archivos cargados
all_pdfs = glob("/home/data/chicago/*.pdf")
#pdf_file = "/Users/cristianb/Documents/Python/rel8ed/SynapseIQ_Lab_01/JJ145209.pdf"
for path in all_pdfs:
    extracted_data = parse_crash_pdf(path)
    insert_incident_and_vehicles_chi(extracted_data, "/home/data")
    print(extracted_data)