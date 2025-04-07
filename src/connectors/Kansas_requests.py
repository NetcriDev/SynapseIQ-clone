import re
import os
import sys
import requests
import psycopg2
import json
import pdfplumber
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from weasyprint import HTML
from weasyprint.urls import URLFetchingError
from src.utils.logger_config import setup_logger
from config.config import get_connection

main_script_path = sys.path[0]
logger = setup_logger("Kansas_execution", main_script_path)

def insert_full_crash_data(df_expanded: pd.DataFrame, file_path: str):
    conn = get_connection()
    cur = conn.cursor()
    logger.info("Start insert into DB: Kansas")
    for _, row in df_expanded.iterrows():
        report_number = str(row["ID"]).strip()
        url = row.get("URL", "").strip()
        driver = row.get("Driver", "").strip()
        license = row.get("License", "").strip()
        insurance = row.get("Insurance", "").strip()
        state = row.get("State", "").strip()
        city = row.get("City", "").strip()
        severity = row.get("Type", "").strip()
        age = row.get("Age", None)
        generation_date = datetime.now()

        accident_dt_str = f"{row['Date']} {row['Time']}"
        try:
            accident_dt = datetime.strptime(accident_dt_str, "%m/%d/%Y %H:%M")
        except ValueError:
            accident_dt = None
            logger.error("Error in parse datetime")

        row_json = json.dumps(row.to_dict())

        # Insert incident if not exists
        cur.execute("""
            INSERT INTO incident_reports (
                report_number, source_url, accident_datetime, city, state, crash_severity, 
                notes, json, original_document_location, generation_date, original_format
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (report_number) DO NOTHING
        """, (
            report_number,
            url,
            accident_dt,
            city,
            state,
            severity,
            "Imported from df_expanded with JSON",
            row_json,
            file_path,
            generation_date,
            "pdf"
        ))

        # Get incident ID
        cur.execute("SELECT id FROM incident_reports WHERE report_number = %s", (report_number,))
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
                        driver_name,
                        driver_license,
                        driver_state,
                        insurance_company,
                        notes
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    incident_id,
                    driver,
                    license,
                    state,
                    insurance,
                    "Vehicle record inferred from license"
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
                    role,
                    name,
                    age,
                    injury_severity,
                    notes
                ) VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                vehicle_id,
                "Driver" if license else "Occupant",
                driver if driver else None,
                int(age) if pd.notnull(age) and str(age).isdigit() else None,
                severity,
                "Passenger record from CSV"
            ))

    conn.commit()
    cur.close()
    conn.close()
    logger.info("Data inserted successfully!: Kansas")


def run_kansas_crash_scraper(path_dir):
    username = 'rrel8ed'
    password = 'zFfUPRWH6q'
    country = 'US'
    entry = ('http://customer-%s-cc-%s:%s@pr.oxylabs.io:7777' %
        (username, country, password))

    proxies = {
        'http': entry,
        'https': entry,
    }

    df_final = pd.DataFrame()

    for days in range(1,2):
        date_list=[]
        time_list=[]
        crash_type=[]

        driver_list=[]
        license_list=[]
        insurance_company_list = []

        crash_number=[]
        crash_link=[]

        final_driver_list=[]
        final_license_list=[]
        final_insurance_company_list = []
        final_states=[]
        final_citys=[]
        final_ages=[]

        desired_date = datetime.now() - timedelta(days)
        format = desired_date.strftime('%m/%d/%Y')

        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9',
            'Cache-Control': 'max-age=0',
            'Connection': 'keep-alive',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': 'https://www.kansas.gov',
            'Referer': 'https://www.kansas.gov/khp-crashlogs/search.do',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
            'sec-ch-ua': '"Not A(Brand";v="8", "Chromium";v="132", "Google Chrome";v="132"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
        }

        data = {
            'accidentDate': format,
            'injuryType': '',
            'county': '',
            'submit': 'Search',
        }

        response = requests.post(
            'https://www.kansas.gov/khp-crashlogs/search.do',
            headers=headers,
            data=data,
            proxies=proxies
        )

        soup = BeautifulSoup(response.content, 'html.parser')
        main_content = soup.find("div", class_="col-12").find_all("div", class_="row")

        for x in range(len(main_content)):
            crash_link.append("https://www.kansas.gov/" + main_content[x].find("a").get("href"))

        for y in range(len(crash_link)):
            crash_number.append(crash_link[y].split("-")[-1])

        for i in range(len(crash_number)):
            response = requests.get(
                'https://www.kansas.gov/khp-crashlogs/search/viewDetail/2025-'+crash_number[i],
                headers=headers,
                proxies=proxies
            )

            soup = BeautifulSoup(response.content, 'html.parser')

            match = re.search(r"Date:\s*(.*)", soup.get_text())
            Date = match.group(1).strip() if match else "N/A"

            match = re.search(r"Time:\s*(.*)", soup.get_text())
            Time = match.group(1).strip() if match else "N/A"

            match = re.search(r"Type:\s*(.*)", soup.get_text())
            accident_type = match.group(1).strip() if match else "N/A"

            driver_names = []
            citys = []
            States=[]
            Age=[]
            for driver_section in soup.find_all("div", class_="page-header1"):
                if "Driver of Vehicle" in driver_section.get_text():
                    name_tag = driver_section.find_next("p")
                    if name_tag and "Name:" in name_tag.get_text():
                        name = name_tag.get_text().split(":", 1)[1].strip()
                        driver_names.append(name)
                    else:
                        driver_names.append("N/A")

                    city_tag = driver_section.find_next("p").find_next("p")
                    if city_tag and "City:" in city_tag.get_text():
                        city = city_tag.get_text().split(":", 1)[1].strip()
                        citys.append(city)
                    else:
                        citys.append("N/A")

                    state_tag = driver_section.find_next("p").find_next("p").find_next("p")
                    if state_tag and "State:" in state_tag.get_text():
                        state = state_tag.get_text().split(":", 1)[1].strip()
                        States.append(state)
                    else:
                        States.append("N/A")

                    age_tag = driver_section.find_next("p").find_next("p").find_next("p").find_next("p").find_next("p").find_next("p")
                    if age_tag and "Age:" in age_tag.get_text():
                        age = age_tag.get_text().split(":", 1)[1].strip()
                        Age.append(age)
                    else:
                        Age.append("N/A")

            insurance_company_list=[]
            for insurance_section in soup.find_all("div", class_="col-12"):
                if "Vehicle" in insurance_section.get_text():
                    for p in insurance_section.find_all("p"):
                        if "Insurance Company:" in p.get_text():
                            insurance = p.get_text().split(":", 1)[1].strip()
                            insurance_company_list.append(insurance if insurance else "N/A")
                            break
            if insurance_company_list:
                insurance_company_list.pop(0)

            license_list=[]
            for license_section in soup.find_all("div", class_="col-12"):
                if "Vehicle" in license_section.get_text():
                    for p in license_section.find_all("p"):
                        if "License:" in p.get_text():
                            license = p.get_text().split(":", 1)[1].strip()
                            license_list.append(license if license else "N/A")
                            break
            if license_list:
                license_list.pop(0)

            date_list.append(Date)
            time_list.append(Time)
            crash_type.append(accident_type)
            final_driver_list.append(driver_names)
            final_license_list.append(license_list)
            final_insurance_company_list.append(insurance_company_list)
            final_states.append(States)
            final_citys.append(citys)
            final_ages.append(Age)

            #print("Date:", Date)
            #print("Time:", Time)
            #print("Type:", accident_type)
            #print("Drivers:", driver_names)
            #print("Insurance:", insurance_company_list)
            #print("License:", license_list)
            #print("City:", States)
            #print("State:", citys)
            #print("Age:", Age)
            #print("--------------------")

            url = 'https://www.kansas.gov/khp-crashlogs/search/viewDetail/2025-'+crash_number[i]
            output_pdf = os.path.join(path_dir, crash_number[i] + ".pdf")

            try:
                HTML(url).write_pdf(output_pdf)
                logger.info(f"PDF generated correctly in: {output_pdf}")
                logger.info(f"Page saved as {output_pdf}")
            except Exception as e:
                logger.error(f"Error generating PDF: {e}")

        df_temp = pd.DataFrame({
        "ID": crash_number,
        "Date": date_list,
        "Time": time_list,
        "Type": crash_type,
        "Driver": final_driver_list,
        "Age": final_ages,
        "License": final_license_list,
        "Insurance": final_insurance_company_list,
        "State": final_states,
        "City": final_citys,
        "URL": crash_link,
        })

        df_final = pd.concat([df_final, df_temp], ignore_index=True)

    df=df_final
    cols_to_explode = ["Driver", "Age", "License", "Insurance", "State", "City"]
    max_len = df[cols_to_explode].applymap(len).max(axis=1)

    for col in cols_to_explode:
        df[col] = df.apply(lambda row: row[col] + [""] * (max_len[row.name] - len(row[col])), axis=1)

    df_expanded = df.explode(cols_to_explode, ignore_index=True)
    insert_full_crash_data(df_expanded, output_pdf)

    file_name='Data_Crashes_Kansas_24H_'+desired_date.strftime('%Y%m%d')+'.csv'
    output_path = os.path.join(path_dir, file_name)
    df_expanded.to_csv(output_path,index=False)
    logger.info("File csv loaded!")


# Add src/ folder to sys.path to import scraper and parser modules
#base_dir = os.path.dirname(os.path.abspath(__file__))
#sys.path.insert(0, base_dir)
#output_dir = "/Users/cristianb/Documents/Python/rel8ed/SynapseIQ_staging/storage"
#output_dir = "/home/data"
#run_kansas_crash_scraper(output_dir)

