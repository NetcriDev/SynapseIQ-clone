import os
import time
import sys
import json
import pandas as pd
from datetime import datetime, timedelta
from src.utils.logger_config import setup_logger
from config.config import get_connection
from src.utils.info_dataframe import print_dataframe_info


main_script_path = sys.path[0]
logger = setup_logger("Texas_execution", main_script_path)

def clean_numeric(value):
    if pd.isna(value) or str(value).strip().lower() in ['no data', '']:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None

def clean_integer(value):
    num = clean_numeric(value)
    if num is not None:
        return int(num)
    return None

def clean_text(value):
    if pd.isna(value):
        return None
    value = str(value).strip()
    if value.lower() in ['no data', '']:
        return None
    return value



def insert_crash_data_to_db(df: pd.DataFrame, pdf_base_path: str):
    conn = get_connection()
    cur = conn.cursor()

    grouped = df.groupby("Crash ID")
    logger.info("Start insert into DB")
    
    for crash_id, group in grouped:
        report_number = str(crash_id)
        accident_datetime = pd.to_datetime(group["Crash Date"].iloc[0], errors='coerce')

        cur.execute("""
            SELECT id FROM incident_reports 
            WHERE report_number = %s AND accident_datetime = %s
        """, (report_number, accident_datetime))
        incident = cur.fetchone()
        
        if incident:
            incident_id = incident[0]
        else:
            # --- Limpieza y preparación de datos ---
            street = clean_text(group['Intersecting Street Number'].iloc[0])
            zip_code = clean_text(group['Driver Zip Code'].iloc[0])
            crash_severity = clean_text(group['Crash Severity'].iloc[0])
            nearest_center_d = clean_numeric(group['Nearest Trauma Center Distance'].iloc[0])
            city = clean_text(group['City'].iloc[0])
            number_of_units = group['VIN'].nunique()
            original_document_location = pdf_base_path

            narrative_parts = [
                f"Nearest Trauma Center: {clean_text(group['Nearest Trauma Center Distance'].iloc[0])}",
                f"Region: {clean_text(group['Region'].iloc[0])}",
                f"Contributing Factors: {', '.join(group['Contributing Factors'].dropna().unique())}",
                f"Contributing Factor 1: {', '.join(group['Contributing Factor 1'].dropna().unique())}",
                f"Contributing Factor 2: {', '.join(group['Contributing Factor 2'].dropna().unique())}",
                f"Contributing Factor 3: {', '.join(group['Contributing Factor 3'].dropna().unique())}",
                f"""$1000 Damage: {clean_text(group["$1000 Damage to Any One Person's Property"].iloc[0])}""",
                f"Agency: {clean_text(group['Agency'].iloc[0])}",
                f"Case ID: {clean_text(group['Case ID'].iloc[0])}",
                f"County: {clean_text(group['County'].iloc[0])}",
                f"Fatal Crash Flag: {clean_text(group['Fatal Crash Flag'].iloc[0])}",
                f"Lessee/Owner Zip Code: {clean_text(group['Lessee/Owner Zip Code'].iloc[0])}",
                f"Vehicle Hit and Run Flag: {clean_text(group['Vehicle Hit and Run Flag'].iloc[0])}",
                f"Person Non-Suspected Serious Injury Count: {clean_text(group['Person Non-Suspected Serious Injury Count'].iloc[0])}"
            ]
            narrative = " || ".join([p for p in narrative_parts if p]) + "."

            row_json = json.dumps(group.dropna().to_dict())

            # Insert incident
            cur.execute("""
                INSERT INTO incident_reports (
                    report_number, internal_report_number, accident_datetime, city, street, zip, crash_severity,
                    source_url, original_document_location, generation_date, json, narrative,
                    nearest_center_d, number_of_units, state, original_format
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                report_number,
                "tx" + str(report_number),
                accident_datetime,
                city,
                street,
                zip_code,
                crash_severity,
                "https://cris.dot.state.tx.us/public/Query/app/home",
                original_document_location,
                datetime.now(),
                row_json,
                narrative,
                nearest_center_d,
                number_of_units,
                "Texas",
                ".csv"
            ))
            incident_id = cur.fetchone()[0]

        vins_seen = {}
        for idx, row in group.iterrows():
            vin = clean_text(row['VIN'])

            if vin not in vins_seen:
                vins_seen[vin] = len(vins_seen) + 1
            unit_number = vins_seen[vin]

            cur.execute("""
                SELECT id FROM vehicles WHERE incident_report_id = %s AND vin = %s
            """, (incident_id, vin))
            vehicle = cur.fetchone()
            
            if vehicle:
                vehicle_id = vehicle[0]
            else:
                notes_parts = [
                    f"County: {clean_text(row['County'])}",
                    f"Contributing Factors: {clean_text(row['Contributing Factors'])}",
                    f"Contributing Factor 1: {clean_text(row['Contributing Factor 1'])}",
                    f"Contributing Factor 2: {clean_text(row['Contributing Factor 2'])}",
                    f"Contributing Factor 3: {clean_text(row['Contributing Factor 3'])}"
                ]
                notes = ". ".join([n for n in notes_parts if n]) + "."

                cur.execute("""
                    INSERT INTO vehicles (
                        incident_report_id, vin, unit_number, notes
                    ) VALUES (%s, %s, %s, %s)
                    RETURNING id
                """, (incident_id, vin, unit_number, notes))
                vehicle_id = cur.fetchone()[0]

            person_number = clean_integer(row.get('Person Number'))

            cur.execute("""
                SELECT id FROM passengers 
                WHERE vehicle_id = %s AND number_occupant = %s
            """, (vehicle_id, person_number))
            existing_passenger = cur.fetchone()

            if not existing_passenger:
                location = clean_text(row.get('Physical Location of An Occupant', ''))
                role = "Driver" if location and ('FRONT LEFT' in location or 'DRIVER' in location) else "Passenger"

                gender = clean_text(row.get('Person Gender', ''))
                if gender:
                    gender = gender.lower()
                    if "male" in gender:
                        gender = "male"
                    elif "female" in gender:
                        gender = "female"
                    else:
                        gender = None

                notes_parts = [
                    f"Person Number: {person_number}",
                    f"Contributing Factors: {clean_text(row.get('Contributing Factors', ''))}",
                    f"Contributing Factor 1: {clean_text(row.get('Contributing Factor 1', ''))}",
                    f"Contributing Factor 2: {clean_text(row.get('Contributing Factor 2', ''))}",
                    f"Contributing Factor 3: {clean_text(row.get('Contributing Factor 3', ''))}",
                    f"Physical Location: {location}"
                ]
                notes = " || ".join([n for n in notes_parts if n])

                cur.execute("""
                    INSERT INTO passengers (
                        vehicle_id, role, name, age, gender, injury_severity, number_occupant, notes
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    vehicle_id,
                    role,
                    location,
                    clean_integer(row.get('Person Age')),
                    gender,
                    clean_text(row.get('Person Injury Severity')),
                    person_number,
                    notes
                ))

    conn.commit()
    cur.close()
    conn.close()
    logger.info("Data inserted successfully: Texas")




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
                logger.info(f"Loaded recent CSV: {f}")
                today = datetime.now()
                try: 
                    begin_date = (today - timedelta(days=4)).strftime("%m/%d/%Y").replace("/", "_")
                    end_date = (today - timedelta(days=1)).strftime("%m/%d/%Y").replace("/", "_")
                    output_name = f"texasprocessed_crashes_{begin_date}_to_{end_date}.csv"
                    output_path = os.path.join(processed_folder, output_name)
                    os.makedirs(processed_folder, exist_ok=True)
                    df.to_csv(output_path, index=False)
                    logger.info(df.columns)
                    print_dataframe_info(df)
                    insert_crash_data_to_db(df, output_path)
                except Exception as e:
                    logger.error(e)
                logger.info(f"Saved to: {output_path}")
                return df

    logger.warning("No recent CSV found.")
    return None


#if __name__ == "__main__":
#    df = read_and_save_recent_csv(margin_seconds=60)

