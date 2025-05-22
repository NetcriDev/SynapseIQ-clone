import json
import sys
import os
import pandas as pd
from datetime import datetime
from config.config import get_connection
from src.utils.logger_config import setup_logger
from src.utils.split_name import split_driver_name

main_script_path = sys.path[0]
logger = setup_logger("Kansas_execution", main_script_path)



def insert_full_crash_data(df_expanded: pd.DataFrame, file_path: str):
    """
    Insert crash report data from a DataFrame into the database.

    This function iterates over each row in the provided DataFrame and inserts
    crash incident data into the `incident_reports` table. It also checks and inserts
    related vehicle and passenger data into the `vehicles` and `passengers` tables
    if they do not already exist.

    Args:
        df_expanded (pd.DataFrame): 
            A DataFrame containing the expanded crash data. Each row should represent
            a crash record with fields like ID, URL, Driver, License, Insurance, 
            State, City, Type (severity), Date, Time, and Age.
        file_path (str): 
            The file path (carpet storage/kansas) where the original document (PDF) is stored. 
            This is saved along with each incident report.
        home_path: is the root carpet where the main script is (/home/SynapseIq/)

    """

    conn = get_connection()
    cur = conn.cursor()

    logger.info("Start insert into DB: Kansas")
    for _, row in df_expanded.iterrows():
        report_number = str(row["ID"]).strip()
        url = row.get("URL", "").strip()
        driver = row.get("Driver", "").strip()
        license = row.get("License", "").strip()
        insurance = str(row.get("Insurance", "")).strip()
        state = row.get("State", "").strip()
        city = row.get("City", "").strip()
        severity = row.get("Type", "").strip()
        role = row.get("Role", "").strip()
        age = row.get("Age", None)
        generation_date = datetime.now()
        gender=row.get("Gender", "").strip()
        driver_first, driver_middle, driver_last = split_driver_name(driver)
        narrative = row.get("Crash Narrative", "").strip()
        print(f">>>> {narrative}")
        accident_dt_str = f"{row['Date']} {row['Time']}"
        try:
            accident_dt = datetime.strptime(accident_dt_str, "%m/%d/%Y %H:%M")
        except ValueError:
            accident_dt = None
            logger.error("[66] Error in parse datetime")

        # Check if the incident already exists
        if accident_dt:
            cur.execute("""
                SELECT id FROM incident_reports 
                WHERE report_number = %s AND accident_datetime = %s
            """, (report_number, accident_dt))
        else:
            cur.execute("""
                SELECT id FROM incident_reports 
                WHERE report_number = %s
            """, (report_number,))

        existing_incident = cur.fetchone()

        if not existing_incident:
            # Insert incident only if it does not already exist
            cur.execute("""
                INSERT INTO incident_reports (
                    report_number, internal_report_number, source_url, 
                    accident_datetime, city, state, crash_severity, 
                    technical_notes, original_document_location, 
                    generation_date, original_format, website, narrative, is_external
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                report_number,
                "ks"+str(report_number),
                url,
                accident_dt,
                city,
                state,
                severity,
                "Imported from df_expanded with JSON",
                os.path.join(file_path,str(report_number)+".pdf"),
                generation_date,
                "pdf",
                "kansas",
                narrative,
                "no"
            ))

        # Get incident ID
        cur.execute("SELECT id FROM incident_reports WHERE report_number = %s AND accident_datetime = %s", (report_number, accident_dt))
        res = cur.fetchone()
        if not res:
            continue
        incident_id = res[0]

        # Check if this row has license > it's a vehicle
        vehicle_id = None
        if license:
            cur.execute("""
                SELECT id FROM vehicles
                WHERE incident_report_id = %s AND driver_license = %s
            """, (incident_id, license))
            existing_vehicle = cur.fetchone()

            if existing_vehicle:
                vehicle_id = existing_vehicle[0]
            else:
                cur.execute("""
                    INSERT INTO vehicles (
                        incident_report_id,
                        report_number,
                        driver_name,
                        driver_license,
                        driver_state,
                        insurance_company,
                        technical_notes,
                        driver_first_name,
                        driver_middle_name,
                        driver_last_name,
                        website
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    incident_id,
                    report_number,
                    driver,
                    license,
                    state,
                    insurance,
                    "Vehicle record inferred from license",
                    driver_first,
                    driver_middle,
                    driver_last,
                    "kansas"
                ))
                vehicle_id = cur.fetchone()[0]

        # Verificar si el pasajero ya existe para el mismo vehículo
        if driver:
            cur.execute("""
                SELECT 1 FROM passengers
                WHERE vehicle_id = %s AND name = %s
            """, (vehicle_id, driver))
            passenger_exists = cur.fetchone()
        else:
            passenger_exists = False

        if not passenger_exists:

            # Insertar pasajero
            cur.execute("""
                INSERT INTO passengers (
                    vehicle_id,
                    report_number,
                    name,
                    age,
                    injury_severity,
                    gender,
                    technical_notes,
                    first_name,
                    middle_name,
                    last_name,
                    state,
                    city,
                    website,
                    role
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                vehicle_id,
                report_number,
                driver if driver else None,
                int(age) if pd.notnull(age) and str(age).isdigit() else None,
                severity,
                "male" if gender.upper() == "M" else "female" if gender.upper() == "F" else "",
                "Passenger record from CSV",
                driver_first, 
                driver_middle, 
                driver_last,
                state,
                city,
                "kansas",
                role
            ))

    conn.commit()
    cur.close()
    conn.close()
    logger.info("[214] Data inserted successfully!: Kansas")
