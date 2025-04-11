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


# Funciones utilitarias
def clean_value(value):
    if value in ('NO DATA', 'No Data', '', None) or pd.isna(value):
        return None
    return value

def clean_int(value):
    if value in ('NO DATA', 'No Data', '', None) or pd.isna(value):
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None

def clean_float(value):
    if value in ('NO DATA', 'No Data', '', None) or pd.isna(value):
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None
    

def insert_crash_and_passengers(df: pd.DataFrame):
    conn = get_connection()
    cur = conn.cursor()

    try:
        for idx, row in df.iterrows():
            crash_id = row.get('Crash ID')
            crash_date_raw = row.get('Crash Date')
            
            # Convertir el crash_date a datetime si existe
            crash_date = pd.to_datetime(crash_date_raw, errors='coerce') if crash_date_raw else None

            if crash_id is None or crash_date is None:
                print(f"Fila {idx} omitida: Crash ID o Crash Date nulo.")
                continue  # Saltar filas incompletas

            # Verificar si ya existe el registro
            check_query = """
            SELECT id FROM list_of_accident_report
            WHERE crash_id = %s AND crash_date= %s;
            """
            cur.execute(check_query, (str(crash_id), crash_date))
            existing = cur.fetchone()

            if existing:
                continue  # Saltar si ya existe

            # Insertar en list_of_accident_report
            insert_crash_query = """
            INSERT INTO list_of_accident_report (
                crash_id, internal_crash_id, agency, case_id, state, city, county,
                street_number, street, region, crash_date, crash_severity
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id;
            """

            crash_values = (
                crash_id,
                f"tx{crash_id}",  # Generar internal_crash_id basado en Crash ID
                clean_value(row.get('Agency')),
                clean_value(row.get('Case ID')),
                clean_value(row.get('State')) or "Texas",
                clean_value(row.get('City')),
                clean_value(row.get('County')),
                clean_value(row.get('Intersecting Street Number')),
                None,  # Street sigue en None
                clean_value(row.get('Region')),
                crash_date,  # crash_date ya está limpio como datetime o None
                clean_value(row.get('Crash Severity'))
            )

            cur.execute(insert_crash_query, crash_values)
            crash_report_id = cur.fetchone()[0]

            # Insertar en passenger_report_list
            insert_passenger_query = """
            INSERT INTO passenger_report_list (
                crash_report_id, crash_id, amount_damage, contributing_factors, fatal_crash_flag,
                street_number, nearest_trauma_center, nearest_trauma_center_distance,
                contributing_factor_1, contributing_factor_2, contributing_factor_3,
                driver_zip_code, lessee_owner_zip_code, vehicle_hit_and_run_flag, vin,
                person_age, person_gender, person_injury_severity,
                person_non_suspected_serious_injury_count, person_count_number,
                physical_location_of_an_occupant
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
            """

            passenger_values = (
                crash_report_id,
                crash_id,
                clean_value(row.get("$1000 Damage to Any One Person's Property")),  # amount_damage
                clean_value(row.get('Contributing Factors')),                       # contributing_factors
                clean_value(row.get('Fatal Crash Flag')),                            # fatal_crash_flag
                clean_value(row.get('Intersecting Street Number')),                 # street_number
                clean_value(row.get('Nearest Trauma Center')),                      # nearest_trauma_center
                clean_float(row.get('Nearest Trauma Center Distance')),             # nearest_trauma_center_distance (NUMERIC)
                clean_value(row.get('Contributing Factor 1')),                      # contributing_factor_1
                clean_value(row.get('Contributing Factor 2')),                      # contributing_factor_2
                clean_value(row.get('Contributing Factor 3')),                      # contributing_factor_3
                clean_int(row.get('Driver Zip Code')),                               # driver_zip_code (INTEGER)
                clean_int(row.get('Lessee/Owner Zip Code')),                         # lessee_owner_zip_code (INTEGER)
                clean_value(row.get('Vehicle Hit and Run Flag')),                   # vehicle_hit_and_run_flag
                clean_value(row.get('VIN')),                                         # vin
                clean_int(row.get('Person Age')),                                    # person_age (INTEGER)
                clean_value(row.get('Person Gender')),                               # person_gender
                clean_value(row.get('Person Injury Severity')),                     # person_injury_severity
                clean_int(row.get('Person Non-Suspected Serious Injury Count')),     # person_non_suspected_serious_injury_count (INTEGER)
                clean_int(row.get('Person Number')),                                 # person_count_number (INTEGER)
                clean_value(row.get('Physical Location of An Occupant'))             # physical_location_of_an_occupant
            )

            cur.execute(insert_passenger_query, passenger_values)

        conn.commit()
        logger.info("Datos insertados exitosamente.")

    except Exception as e:
        conn.rollback()
        print(f"Error insertando datos: {e}")

    finally:
        cur.close()
        conn.close()


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
                    #logger.info(df.columns)
                    print_dataframe_info(df)
                    insert_crash_and_passengers(df)
                except Exception as e:
                    logger.error(e)
                logger.info(f"Saved to: {output_path}")
                return df

    logger.warning("No recent CSV found.")
    return None


#if __name__ == "__main__":
#    df = read_and_save_recent_csv(margin_seconds=60)

