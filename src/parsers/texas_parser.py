import os
import time
import pandas as pd
from datetime import datetime
import os
import time
import pandas as pd
from datetime import datetime, timedelta
import sys
from src.utils.logger_config import setup_logger
from config.config import get_connection

main_script_path = os.path.dirname(os.path.abspath(sys.argv[0]))

logger = setup_logger("MSP_execution", main_script_path)



import psycopg2
import pandas as pd
import json
from datetime import datetime

def insert_crash_data_to_db(df: pd.DataFrame, pdf_base_path: str):
    conn = get_connection()
    cur = conn.cursor()

    grouped = df.groupby("Crash ID")

    for crash_id, group in grouped:
        # Para incident_reports
        report_number = str(crash_id)
        accident_datetime = pd.to_datetime(group["Crash Date"].iloc[0], errors='coerce')
        
        # Verificar si ya existe el incidente
        cur.execute("""
            SELECT id FROM incident_reports 
            WHERE report_number = %s AND accident_datetime = %s
        """, (report_number, accident_datetime))
        incident = cur.fetchone()
        if incident:
            incident_id = incident[0]
        else:
            # Construir narrative concatenado
            narrative_parts = [
                f"Nearest Trauma Center: {group['Nearest Trauma Center (Nearest Trauma Center)'].iloc[0]}",
                f"Region: {group['Region'].iloc[0]}",
                f"Contributing Factors: {', '.join(group['Contributing Factors'].dropna().unique())}",
                f"Contributing Factor 1: {', '.join(group['Contributing Factor 1'].dropna().unique())}",
                f"Contributing Factor 2: {', '.join(group['Contributing Factor 2'].dropna().unique())}",
                f"Contributing Factor 3: {', '.join(group['Contributing Factor 3'].dropna().unique())}",
                f"$1000 Damage to Any One Person's Property: {group['$1000 Damage to Any One Person\'s Property'].iloc[0]}",
                f"Agency: {group['Agency'].iloc[0]}",
                f"Case ID: {group['Case ID'].iloc[0]}",
                f"County: {group['County'].iloc[0]}",
                f"Fatal Crash Flag: {group['Fatal Crash Flag'].iloc[0]}",
                f"Lessee/Owner Zip Code: {group['Lessee/Owner Zip Code'].iloc[0]}",
                f"Vehicle Hit and Run Flag: {group['Vehicle Hit and Run Flag'].iloc[0]}",
                f"Person Non-Suspected Serious Injury Count: {group['Person Non-Suspected Serious Injury Count'].iloc[0]}"
            ]
            narrative = ". ".join([p for p in narrative_parts if p]) + "."

            # Construir otros campos
            street = group['Intersecting Street Name'].iloc[0]
            street = '' if street == 'NO DATA' else street

            original_document_location = f"{pdf_base_path}/{report_number}.pdf"
            nearest_center_d = group['Nearest Trauma Center Distance (Distance to the nearest Trauma Center)'].iloc[0]
            zip_code = group['Driver Zip Code'].iloc[0]

            row_json = json.dumps(group.dropna().to_dict())

            # Insertar el incidente
            cur.execute("""
                INSERT INTO incident_reports (
                    report_number, accident_datetime, city, street, zip,
                    original_document_location, generation_date, json, narrative,
                    nearest_center_d
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                report_number,
                accident_datetime,
                group['City'].iloc[0],
                street,
                zip_code,
                original_document_location,
                datetime.now(),
                row_json,
                narrative,
                nearest_center_d
            ))
            incident_id = cur.fetchone()[0]

        # Insertar en vehicles y passengers
        for idx, row in group.iterrows():
            vin = str(row['VIN']).strip()

            # Verificar si ya existe el vehículo
            cur.execute("""
                SELECT id FROM vehicles WHERE incident_report_id = %s AND vin = %s
            """, (incident_id, vin))
            vehicle = cur.fetchone()
            if vehicle:
                vehicle_id = vehicle[0]
            else:
                notes_parts = [
                    f"County: {row['County']}",
                    f"Contributing Factors: {row['Contributing Factors']}",
                    f"Contributing Factor 1: {row['Contributing Factor 1']}",
                    f"Contributing Factor 2: {row['Contributing Factor 2']}",
                    f"Contributing Factor 3: {row['Contributing Factor 3']}"
                ]
                notes = ". ".join([n for n in notes_parts if n]) + "."

                cur.execute("""
                    INSERT INTO vehicles (
                        incident_report_id, vin, notes
                    ) VALUES (%s, %s, %s)
                    RETURNING id
                """, (incident_id, vin, notes))
                vehicle_id = cur.fetchone()[0]

            # Insertar pasajero (la persona del registro)
            cur.execute("""
                INSERT INTO passengers (
                    vehicle_id, role, name, age, gender, injury_severity
                )
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                vehicle_id,
                "Passenger",  # Puedes cambiar a "Driver" si sabes cuál es
                row.get('Physical Location of An Occupant', None),
                row.get('Person Age', None),
                row.get('Person Gender', None),
                row.get('Person Injury Severity', None)
            ))

    conn.commit()
    cur.close()
    conn.close()

    print("Data inserted successfully.")





def get_paths():
    current_dir = os.path.abspath(os.path.dirname(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, ".."))
    raw_path = os.path.join(project_root, "data", "raw")
    processed_path = os.path.join(project_root, "data", "processed")
    os.makedirs(processed_path, exist_ok=True)
    return raw_path, processed_path

def read_and_save_recent_csv(raw_path: str = None, processed_path: str = None, margin_seconds=60):
    if raw_path is None or processed_path is None:
        raw_folder, processed_folder = get_paths()

    raw_folder = raw_path
    processed_folder = processed_path
    
    threshold = time.time() - margin_seconds

    for f in os.listdir(raw_folder):
        if f.endswith(".csv"):
            full_path = os.path.join(raw_folder, f)
            if os.path.getmtime(full_path) > threshold:
                df = pd.read_csv(full_path, skiprows=10)
                print(f"Loaded recent CSV: {f}")
                today = datetime.now()
                try: 
                    begin_date = (today - timedelta(days=4)).strftime("%m/%d/%Y").replace("/", "_")
                    end_date = (today - timedelta(days=1)).strftime("%m/%d/%Y").replace("/", "_")
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    output_name = f"texasprocessed_crashes_{begin_date}_to_{end_date}_at_{timestamp}.csv"
                    output_path = os.path.join(processed_folder, output_name)
                    df.to_csv(output_path, index=False)
                except Exception as e:
                    print(e)
                print(f"Saved to: {output_path}")
                return df

    print("No recent CSV found.")
    logger.info("4")
    return None


#if __name__ == "__main__":
#    df = read_and_save_recent_csv(margin_seconds=60)

