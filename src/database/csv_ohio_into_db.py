import psycopg2
import pandas as pd
import os
from datetime import datetime
from typing import Tuple, List, Optional
from config.config import get_connection
from src.utils.split_name import split_driver_name


def split_driver_name(name: str):
    """
    Splits a driver's full name into [first_name, middle_name, last_name] 
    following specific rules about hyphens and suffixes like Jr., Sr., III, etc.
    """
    if not isinstance(name, str):
        return [None, None, None]

    name = name.strip()

    if name.lower() == 'unknown' or ('unknown' in name.lower() and len(name) < 10):
        return [None, None, None]

    suffixes = {"sr.", "jr.", "ii", "iii", "iv", "v", "jr"}
    parts = name.split()

    # Normalize all parts to lower for suffix detection
    parts_lower = [p.lower() for p in parts]

    # Rule 3: Handle suffixes (Sr., Jr., III, etc.)
    for i, part in enumerate(parts_lower):
        if part in suffixes and i > 0:
            last_name = parts[i-1]
            parts = parts[:i-1]  # Remove last name and suffix from parts
            break
    else:
        last_name = None

    # Rebuild name after removing suffix, if found
    name_cleaned = ' '.join(parts)

    # Rule 1: Check for "-"
    if "-" in name_cleaned:
        parts = name_cleaned.split()
        # Find the part containing "-"
        for idx, p in enumerate(parts):
            if "-" in p:
                last_name = p
                if ',' not in name_cleaned and len(parts) >= 4:
                    # Rule 2: if 4+ words and no comma
                    middle_name = parts[idx - 1] if idx >= 1 else None
                    first_name = ' '.join(parts[:idx-1]) if idx >= 2 else None
                else:
                    # Default split for hyphen without 4+ words
                    if ',' in name_cleaned:
                        # Format: Last, First Middle
                        last, first_middle = [part.strip() for part in name_cleaned.split(',', 1)]
                        parts = first_middle.split()
                        first_name = parts[0] if len(parts) >= 1 else None
                        middle_name = ' '.join(parts[1:]) if len(parts) > 1 else None
                    else:
                        # Assume last name and rest
                        parts = name_cleaned.split()
                        last_name = p
                        parts.remove(p)
                        first_name = parts[0] if len(parts) >= 1 else None
                        middle_name = ' '.join(parts[1:]) if len(parts) > 1 else None
                break
    else:
        if ',' in name_cleaned:
            # Format: Last, First Middle
            last, first_middle = [part.strip() for part in name_cleaned.split(',', 1)]
            parts = first_middle.split()
            first_name = parts[0] if len(parts) >= 1 else None
            middle_name = ' '.join(parts[1:]) if len(parts) > 1 else None
            last_name = last if not last_name else last_name
        else:
            # Default format: First Middle Last
            parts = name_cleaned.split()
            if len(parts)==2 and not last_name:
                last_name = parts[-1] if len(parts) >= 1 else None
                parts = parts[:-1]
            if not last_name and len(parts)==3:
                last_name = parts[-1] if len(parts) >= 1 else None
                parts = parts[:-1]
            if not last_name and len(parts)>3:
                last_name = parts[-2] if len(parts) >= 1 else None
                parts = parts[:-1]
                parts = parts[:-1]
            first_name = parts[0] if len(parts) >= 1 else None
            middle_name = ' '.join(parts[1:]) if len(parts) > 1 else None

    # Normalize names (capitalize properly)
    def normalize(n):
        return n.title() if isinstance(n, str) else None

    return [normalize(first_name), normalize(middle_name), normalize(last_name)]



def extract_city_from_address(address: str):
    if not isinstance(address, str):
        return None
    parts = [part.strip() for part in address.split(",")]
    if len(parts) == 4:
        return parts[1]  # segundo componente: ciudad
    return None


def extract_year(date_str):
    try:
        if not isinstance(date_str, str):
            return None
        cleaned = date_str.strip().lower()
        if cleaned in ("null", "n/a", "none", ""):
            return None
        return datetime.strptime(cleaned, "%m/%d/%Y").year
    except (ValueError, TypeError):
        return None


def clean_str(value):
    if pd.isna(value) or str(value).strip().lower() in {"null", "", "none", "N/A"}:
        return None
    return str(value).strip()

def to_int(value):
    try:
        if isinstance(value, str) and value.strip().lower() in ("n/a", "na", "none", ""):
            return None
        return int(float(value))
    except (ValueError, TypeError):
        return None

def to_datetime(value):
    try:
        return pd.to_datetime(value)
    except:
        return None


def insert_data_from_dataframe(df: pd.DataFrame, path_files_saved)-> dict:
    """
    Inserts data from a DataFrame into the database.
    Args:
        df (pd.DataFrame): DataFrame containing the data to be inserted.
        path_files_saved (str): Path folder where the files are saved.
    Returns:
        dict: Summary of the insertion process, including:
            report_number, 
            incident_id, 
            incident_report,
            vehicle,
            passenger
    """
    conn = get_connection()
    cur = conn.cursor()
    resumen = {}
    
    for _, row in df.iterrows():
        try:
            #print(row)
            report_number = clean_str(row.get("Accident Report Number"))
            crash_date = to_datetime(row.get("Crash Date"))
            city =  extract_city_from_address(clean_str(row.get("Address")))  
            street = clean_str(row.get("Address"))
            address = clean_str(row.get("Address"))
            type_ps = clean_str(row.get("TYPE"))
            unit_fault = clean_str(row.get("Unit at Fault"))
            generation_date = datetime.now()
            state = "OH"
            is_external='yes'
            name = clean_str(row.get("Name"))
            first, middle, last = split_driver_name(name)
            gender = clean_str(row.get("Gender"))
            phone1 = clean_str(row.get("Contacts_1"))
            age = to_int(row.get("Age"))
            year_birth = extract_year(row.get("Birth"))
            passenger_notes = f"Minors: {clean_str(row.get('Minors'))}"
            license_plate = clean_str(row.get("License Plate"))
            unit_number = to_int(row.get("Unit"))  
            insurance_company = clean_str(row.get("Unit at Fault Company"))
            policy_number = clean_str(row.get("Unit at Fault Policy"))
            website = "ohio"
            unit_fault = clean_str(row.get("Unit at Fault"))
            narrative = clean_str(row.get("Narrative"))
            notes = f"Unit at Fault: {unit_fault}; " \
                    f"Insurance Policy: {clean_str(row.get('Insurance Policy'))}; " \
                    f"Insurance Company: {clean_str(row.get('Insurance Company'))}; "

            resumen = {
                "report_number": report_number,
                "incident_id": None,
                "incident_report": None,
                "vehicle": None,
                "passenger": None
            }

            # === INCIDENTE ===
            # Verificar incidente por report_number y fecha
            cur.execute("""
                SELECT id FROM incident_reports 
                WHERE report_number = %s AND accident_datetime = %s
            """, (report_number, crash_date))
            incident = cur.fetchone()

            if incident:
                incident_id = incident[0]
                resumen["incident_report"] = "already_registered"
                resumen["incident_id"] = incident_id
            # if not incident:
            else:
                cur.execute("""
                    INSERT INTO incident_reports (
                        report_number, 
                        internal_report_number,
                        accident_datetime, 
                        city, street, generation_date, 
                        state,
                        original_document_location, 
                        narrative,
                        website,
                        is_external
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (report_number,
                    "oh" + str(report_number),
                    crash_date, 
                    city, 
                    street, 
                    generation_date, 
                    state,
                    os.path.join(path_files_saved,report_number + ".pdf"),
                    narrative,
                    website,
                    is_external
                    ))
                incident_id = cur.fetchone()[0]
                resumen["incident_report"] = "inserted"
                resumen["incident_id"] = incident_id
        

            # === VEHÍCULO ===
            # Verificar vehículo
            cur.execute("""
                SELECT id FROM vehicles 
                WHERE incident_report_id = %s AND license_plate_number = %s AND unit_number = %s
            """, (incident_id, license_plate, unit_number))
            vehicle = cur.fetchone()

            if vehicle:
                vehicle_id = vehicle[0]
                resumen["vehicle"] = "already_registered"
            else:
                cur.execute("""
                    INSERT INTO vehicles (
                        incident_report_id, 
                        report_number,
                        unit_number, 
                        license_plate_number, 
                        insurance_company, policy_number, 
                        notes,
                        driver_name, driver_first_name, driver_middle_name, driver_last_name, website
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
                """, (incident_id, 
                    report_number,
                    unit_number, 
                    license_plate, 
                    insurance_company, 
                    policy_number, 
                    notes, 
                    name, first, middle, last, website))
                vehicle_id = cur.fetchone()[0]
                resumen["vehicle"] = "already_registered"

            # Verificar pasajero
            cur.execute("""
                SELECT id FROM passengers
                WHERE vehicle_id = %s AND name = %s AND gender = %s
            """, (vehicle_id, name, gender))
            passenger = cur.fetchone()
            if passenger:
                resumen["passenger"] = "already_registered"
            else:
                cur.execute("""
                    INSERT INTO passengers (
                        vehicle_id,
                        report_number,
                        name, 
                        gender, 
                        phone1, 
                        age, 
                        year_birth, 
                        notes,
                        first_name, 
                        middle_name,
                        last_name, 
                        state, city, street, role, website, insurance_company
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (vehicle_id, 
                    report_number,
                    name, gender, 
                    phone1, age, year_birth, passenger_notes, 
                    first, middle, last, 
                    state, 
                    city, 
                    street, 
                    type_ps, 
                    website, 
                    insurance_company))
                resumen["passenger"] = "already_registered"
        except Exception as e:

            resumen = {
                "report_number": " ",
                "incident_id": None,
                "incident_report": "Dont insert into DB by error:" + str(e),
                "vehicle": None,
                "passenger": None,
                "error": str(e)
            }

            conn.rollback()
            continue
    
    conn.commit()
    cur.close()
    conn.close()
    return resumen