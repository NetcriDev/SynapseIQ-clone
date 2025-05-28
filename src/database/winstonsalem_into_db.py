import json
import sys
import os
import pandas as pd
from datetime import datetime
from config.config import get_connection
from src.utils.logger_config import setup_logger
from src.utils.split_name import split_driver_name

main_script_path = sys.path[0]
logger = setup_logger("WinstonSalem_execution", main_script_path)

#insert into DB
def insert_dataframe_into_db(df: pd.DataFrame, file_path: str, home_path: str = None):
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
            The file path (carpet storage/winstonsalem) where the original document (PDF) is stored. 
            This is saved along with each incident report.
        home_path (str):
            is the root carpet where the main script is (/home/SynapseIq/)

    """
    
    conn = get_connection()
    cur = conn.cursor()

    for _, row in df.iterrows():
        report_number = str(row['REPORT']).strip()
        source_url = str(row.get('URL', '')).strip()
        accident_datetime = None
        try:
            accident_datetime = pd.to_datetime(row['DATE'])
        except Exception:
            pass

        city = row.get('City', '')
        state = row.get('State', '')
        street = str(row.get('Address', '')).strip()
        driver = str(row.get('Driver', '')).strip()
        vin = str(row.get('VIN', '')).strip()
        insurance = str(row.get('Insurance', '')).strip()
        policy = str(row.get('Policy', '')).strip()
        severity = str(row.get('Severity', '')).strip()
        cost = str(row.get('Costs', '')).strip()
        generation_date = datetime.now()
        age = int(row['Age']) if pd.notnull(row.get('Age')) and str(row.get('Age')).strip().isdigit() else None
        date_birth = int(row['Date of Birth']) if pd.notnull(row.get('Date of Birth')) and str(row.get('Date of Birth')).strip().isdigit() else None
        row_json = json.dumps(row.dropna().to_dict())
        original_document_location = os.path.join(file_path,"WSP-"+str(datetime.now().year)+"-"+report_number+".pdf")  # ubicación real del PDF
        driver_first, driver_middle, driver_last = split_driver_name(driver)
        narrative = str(row.get('Narrative', '')).strip()

        # Insert incident if not exists
        cur.execute("SELECT id FROM incident_reports WHERE report_number = %s AND accident_datetime = %s", (report_number, accident_datetime))
        res = cur.fetchone()
        if res:
            incident_id = res[0]
        else:
            
            cur.execute("""
                INSERT INTO incident_reports (
                    report_number, internal_report_number, source_url, accident_datetime, city, state, street,
                    technical_notes, json, original_document_location, generation_date,
                    original_format, crash_severity, narrative, website, is_external
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                report_number,
                "wsp" + str(report_number),
                source_url,
                accident_datetime,
                city,
                state,
                street,
                "Inserted from WSP Daily DataFrame",
                row_json,
                original_document_location,
                generation_date,
                "pdf",
                severity,
                narrative,
                "winstonsalem",
                "no"
            ))
            incident_id = cur.fetchone()[0]

        # Insert vehicle if not exists for the incident
        vehicle_id = None
        if incident_id:
            cur.execute("""
                SELECT id FROM vehicles
                WHERE incident_report_id = %s AND vin = %s
            """, (incident_id, vin))
            existing_vehicle = cur.fetchone()
            if existing_vehicle:
                vehicle_id = existing_vehicle[0]
            else:
                cur.execute("""
                    INSERT INTO vehicles (
                        incident_report_id, report_number, vin, insurance_company, policy_number,
                        driver_name, technical_notes,
                        driver_first_name, 
                        driver_middle_name, 
                        driver_last_name,
                        estimated_cost, website
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    incident_id,
                    report_number,
                    vin,
                    insurance,
                    policy,
                    driver,
                    "Inserted from WSP Daily DataFrame",
                    driver_first,
                    driver_middle,
                    driver_last,
                    cost,
                    "winstonsalem"))
                vehicle_id = cur.fetchone()[0]

        # Insert driver also as a passenger with role "Driver"
        if vehicle_id:
            cur.execute("""
                SELECT id FROM passengers
                WHERE vehicle_id = %s AND name = %s AND role = 'Driver'
            """, (vehicle_id, driver))
            exists = cur.fetchone()

            if not exists:
                cur.execute("""
                    INSERT INTO passengers (
                        vehicle_id, 
                        role, report_number,
                        name, technical_notes,
                        age, year_birth,
                        first_name,
                        middle_name,
                        last_name,
                        state,
                        city,
                        street,
                        website,
                        hasinsurance_details, 
                        hasname, 
                        over18
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    vehicle_id,
                    'Driver',
                    report_number,
                    driver,
                    "Inserted from WSP Daily DataFrame",
                    age,
                    date_birth,
                    driver_first, 
                    driver_middle, 
                    driver_last,
                    state,
                    city,
                    street,
                    "winstonsalem",
                    str(bool(insurance)),
                    str(bool(driver) and driver.upper() not in {"", "N/A", "KNOWN", "UNKNOWN"}),
                    str((age_value := (int(age) if str(age).isdigit() else None)) is not None and age_value > 17)
                ))

    conn.commit()
    cur.close()
    conn.close()
    logger.info("Data successfully inserted: WinstonSalem")



