import json
import sys
import os
import pandas as pd
from datetime import datetime
from config.config import get_connection
from src.utils.logger_config import setup_logger
from src.utils.split_name import split_driver_name

main_script_path = sys.path[0]
logger = setup_logger("Minnesota_execution", main_script_path)


def safe_int(value):
    if pd.isna(value):
        return None
    str_val = str(value).strip().lower()
    if str_val in ("n/a", "null", "none", ""):
        return None
    try:
        return int(float(value))
    except ValueError:
        return None
    
def mn_dataframe_to_db(df: pd.DataFrame, pdf_base_folder: str):
    """
    Insert crash report data from a DataFrame into the database.

    Args:
        df (pd.DataFrame): DataFrame containing crash report data.
        pdf_base_folder (str): Path to the folder where PDF files are saved.
    Returns:
        None
    """

    conn = get_connection()
    cur = None
    try:
        cur = conn.cursor()

        for _, row in df.iterrows():
            report_number = str(row['ID']).strip()
            try:
                accident_datetime = pd.to_datetime(row['Date']) if pd.notna(row['Date']) else None
            except Exception as e:
                logger.error(f"[50]: {e}")

            current_year = datetime.now().year
            city = row['City'].strip() if pd.notna(row['City']) else ''
            state = row['State'].strip() if pd.notna(row['State']) else ''
            addres = row.get("Location", "").strip()
            source_url = row['URL'].strip() if pd.notna(row['URL']) else ''
            narrative = row['Description'].strip() if pd.notna(row['Description']) else ''
            driver_name = row['Driver'].strip() if pd.notna(row['Driver']) else ''
            age = safe_int(row["Age"])
            media_contact = row['Contact'].strip() if pd.notna(row['Contact']) else ''
            crash_severity = row['Type'].strip() if pd.notna(row['Type']) else ''
            original_document_location = os.path.join(pdf_base_folder, report_number + ".pdf")
            generation_date = datetime.now()
            case_number = row['Case Number'].strip() if pd.notna(row['Case Number']) else ''
            driver_first, driver_middle, driver_last = split_driver_name(driver_name)
            row_json = json.dumps(row.dropna().to_dict(), default=str)

            cur.execute("SELECT id FROM incident_reports WHERE report_number = %s AND accident_datetime = %s", (report_number, accident_datetime))
            result = cur.fetchone()
            if result:
                incident_id = result[0]
            else:
                cur.execute("""
                    INSERT INTO incident_reports (
                        report_number, internal_report_number, accident_datetime, city,
                        state, source_url, narrative, original_document_location,
                        generation_date, original_format, notes, crash_severity,
                        json, website, is_external
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    report_number,
                    str(current_year) + state + str(report_number),
                    accident_datetime,
                    city,
                    state,
                    source_url,
                    narrative,
                    original_document_location,
                    generation_date,
                    "pdf",
                    "Case Number: " + case_number + " || Contact: " + media_contact,
                    crash_severity,
                    row_json,
                    "minnesota",
                    "no"
                ))
                incident_id = cur.fetchone()[0]

            cur.execute("""
                SELECT id FROM vehicles
                WHERE incident_report_id = %s AND driver_name = %s
                """, (incident_id, driver_name))
            result = cur.fetchone()
            if result:
                vehicle_id = result[0]
            else:
                cur.execute("""
                    INSERT INTO vehicles (
                        incident_report_id,
                        report_number,
                        driver_name,
                        driver_first_name,
                        driver_middle_name,
                        driver_last_name,
                        website
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    incident_id,
                    report_number, 
                    driver_name,
                    driver_first,
                    driver_middle,
                    driver_last,
                    "minnesota"
                ))
                vehicle_id = cur.fetchone()[0]

            cur.execute("""
                SELECT id FROM passengers
                WHERE vehicle_id = %s AND name = %s
            """, (vehicle_id, driver_name))
            result = cur.fetchone()
            if not result: 
                cur.execute("""
                    INSERT INTO passengers (
                        vehicle_id,
                        report_number,
                        role, 
                        name, 
                        age,
                        first_name,
                        middle_name,
                        last_name,
                        state,
                        city,
                        address,
                        website
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    vehicle_id,
                    report_number,
                    'Driver',
                    driver_name,
                    age,
                    driver_first,
                    driver_middle,
                    driver_last,
                    state,
                    city,
                    addres,
                    "minnesota"
                ))

        conn.commit()
        logger.info("Data inserted successfully!: Minnesota")
    except Exception as e:
        logger.exception("Error inserting data into database")
        conn.rollback()
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()
