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
from src.utils.info_dataframe import print_dataframe_info
from config.config import get_connection

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

    """
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
        gender=row.get("Gender", "").strip()

        accident_dt_str = f"{row['Date']} {row['Time']}"
        try:
            accident_dt = datetime.strptime(accident_dt_str, "%m/%d/%Y %H:%M")
        except ValueError:
            accident_dt = None
            logger.error("Error in parse datetime")

        row_json = json.dumps(row.to_dict())

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
                    report_number, internal_report_number, source_url, accident_datetime, city, state, crash_severity, 
                    technical_notes, json, original_document_location, generation_date, original_format
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                report_number,
                "ks"+str(report_number),
                url,
                accident_dt,
                city,
                state,
                severity,
                "Imported from df_expanded with JSON",
                row_json,
                os.path.join(file_path,str(report_number)+".pdf"),
                generation_date,
                "pdf"
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
                        driver_name,
                        driver_license,
                        driver_state,
                        insurance_company,
                        technical_notes
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
                    gender,
                    technical_notes
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                vehicle_id,
                "Driver" if license else "Occupant",
                driver if driver else None,
                int(age) if pd.notnull(age) and str(age).isdigit() else None,
                severity,
                "male" if gender.upper() == "M" else "female" if gender.upper() == "F" else "",
                "Passenger record from CSV"
            ))

    conn.commit()
    cur.close()
    conn.close()
    logger.info("Data inserted successfully!: Kansas")


def run_kansas_crash_scraper(path_dir: str):
    """
    Scrapes crash data from the Kansas crash reporting system.

    Parameters
    ----------
    path_dir : str
        Path to the directory where downloaded files, storage folder (storage) or results should be stored.

    Returns
    -------
    None
    """
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

    # ----------------------------------------- 1st page request ---------------------------------------------------------------------

    for days in range(1,3):  # 24h ojo

        # Creating lists for scrapping table content
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
        final_genders=[]


        # setting relative date
        desired_date = datetime.now() - timedelta(days)
        # Format example: 11/06/2024 (NOV)
        format = desired_date.strftime('%m/%d/%Y')

        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9',
            'Cache-Control': 'max-age=0',
            'Connection': 'keep-alive',
            'Content-Type': 'application/x-www-form-urlencoded',
            # 'Cookie': 'JSESSIONID=0BFB69E6C1ED4EEA3978EA280E77A5D6.aptcs04-inst1; ksgov=!0QNNB60YJ5E7c+GOfB8IWYBnkPHbwbmqBMH5akvvsf8OiaxgYWKotSvKG3TRxvrJKqz2gppLxAiQNjbbqQXTIJtRWjjz8/V22PxP323ABFZH; org.springframework.web.servlet.i18n.CookieLocaleResolver.LOCALE=en; _ga=GA1.1.1843948162.1739295866; _ga_WKD2LX56WX=GS1.1.1739464869.2.0.1739464869.0.0.0; _ga_V4YJRE8BKZ=GS1.1.1739464877.6.1.1739465034.0.0.0',
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
        try:
            response = requests.post(
                'https://www.kansas.gov/khp-crashlogs/search.do',
                headers=headers,
                data=data,
                proxies=proxies
                )
        except Exception as e:
            logger.error(e)

        # --------------------------------------------------- find main div ans scrap links and id -----------------------------------------------------------
        soup = BeautifulSoup(response.content, 'html.parser')
        main_content = soup.find("div", class_="col-12").find_all("div", class_="row")

        for x in range(len(main_content)):
            crash_link.append("https://www.kansas.gov/" + main_content[x].find("a").get("href"))
        # print(crash_link)
        # now we have a list of all links to crash reports

        for y in range(len(crash_link)):
            crash_number.append(crash_link[y].split("-")[-1])
        # print(crash_number)

        # --------------------------------------------------- search request -----------------------------------------------------------

        for i in range(len(crash_number)):
            # new request for next page
            headers = {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'Accept-Language': 'en-US,en;q=0.9,pt;q=0.8',
                'Cache-Control': 'max-age=0',
                'Connection': 'keep-alive',
                'Content-Type': 'application/x-www-form-urlencoded',
                # 'Cookie': 'JSESSIONID=A811DC7EE04E50F32FFE7DC315028B51.aptcs04-inst1; ksgov=!UOQWS66nXWryJDiOfB8IWYBnkPHbwameCZWnoDXc7ue0ZqaIxI/7+Nw8lZUAPZXCxXcgLFCvoI7DrWgeh8bRDSf0l2j+CYIRMYdD3zcA+JOG; _ga=GA1.1.1679144528.1739406024; _ga_XVN1E5L507=GS1.1.1739484868.1.1.1739484884.0.0.0; org.springframework.web.servlet.i18n.CookieLocaleResolver.LOCALE=en; _ga_V4YJRE8BKZ=GS1.1.1739484540.2.1.1739484905.0.0.0',
                'Origin': 'https://www.kansas.gov',
                'Referer': 'https://www.kansas.gov/khp-crashlogs/search/index',
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
            response = requests.get(
                'https://www.kansas.gov/khp-crashlogs/search/viewDetail/2025-'''+crash_number[i]+'',
                headers=headers,
                proxies=proxies
                )

            # update html content and acquire data
            soup = BeautifulSoup(response.content, 'html.parser')

        # Extrair data e hora
            match = re.search(r"Date:\s*(.*)", soup.get_text())
            Date = match.group(1).strip() if match else "N/A"

            match = re.search(r"Time:\s*(.*)", soup.get_text())
            Time = match.group(1).strip() if match else "N/A"

            # Extrair tipo de acidente
            match = re.search(r"Type:\s*(.*)", soup.get_text())
            accident_type = match.group(1).strip() if match else "N/A"

            # Extrair nome dos motoristas
            driver_names = []
            citys = []
            States=[]
            Age=[]
            Gender=[]
            for driver_section in soup.find_all("div", class_="page-header1"):
                if "Driver of Vehicle" in driver_section.get_text():
                    # Nome
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

                    gender_tag = driver_section.find_next("p").find_next("p").find_next("p").find_next("p").find_next("p").find_next("p").find_next("p")
                    if gender_tag and "Sex:" in gender_tag.get_text():
                        gender = gender_tag.get_text().split(":", 1)[1].strip()
                        gender = gender[0]
                        Gender.append(gender)
                    else:
                        Gender.append("N/A")
                    

            insurance_company_list=[]
        # Encontrar todas as seções de veículos
            for insurance_section in soup.find_all("div", class_="col-12"):
                if "Vehicle" in insurance_section.get_text():
                    # Procurar todos os <p> dentro dessa seção
                    for p in insurance_section.find_all("p"):
                        # Verificar se o parágrafo contém "Insurance Company:"
                        if "Insurance Company:" in p.get_text():
                            insurance = p.get_text().split(":", 1)[1].strip()
                            insurance_company_list.append(insurance if insurance else "N/A")
                            break  # Parar a busca dentro dessa seção após encontrar o valor
            if insurance_company_list:
                insurance_company_list.pop(0)
                

            license_list=[]
            # Encontrar todas as seções de veículos
            for license_section in soup.find_all("div", class_="col-12"):
                if "Vehicle" in license_section.get_text():
                    # Procurar todos os <p> dentro dessa seção
                    for p in license_section.find_all("p"):
                        # Verificar se o parágrafo contém "Insurance Company:"
                        if "License:" in p.get_text():
                            license = p.get_text().split(":", 1)[1].strip()
                            license_list.append(license if license else "N/A")
                            break  # Parar a busca dentro dessa seção após encontrar o valor
            if license_list:
                license_list.pop(0)

            # append content
            date_list.append(Date)
            time_list.append(Time)

            # driver_list.append(driver_names)
            crash_type.append(accident_type)

            final_driver_list.append(driver_names)
            final_license_list.append(license_list)
            final_insurance_company_list.append(insurance_company_list)
            final_states.append(States)
            final_citys.append(citys)
            final_ages.append(Age)
            final_genders.append(Gender)

            # Exibir os resultados
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

            url = 'https://www.kansas.gov/khp-crashlogs/search/viewDetail/2025-'''+crash_number[i]+''
            # Define the full path for the 'kansas' folder
            kansas_dir = os.path.join(path_dir, "kansas")
            # Create the 'kansas' folder if it doesn't exist
            os.makedirs(kansas_dir, exist_ok=True)
            #output_pdf = crash_number[i]+".pdf" ojo
            output_pdf = os.path.join(kansas_dir,crash_number[i] + ".pdf")

            # Converte a página para PDF
            try:
                HTML(url).write_pdf(output_pdf)
                logger.info(f"PDF generated correctly in: {output_pdf}")
                logger.info(f"Page saved as {output_pdf}")
            except Exception as e:
                logger.error(f"Error generating PDF: {e}")

        # DF for the current day in "days"
        df_temp = pd.DataFrame({
        "ID": crash_number,
        "Date": date_list,
        "Time": time_list,
        "Type": crash_type,
        "Driver": final_driver_list,
        "Age": final_ages,
        "Gender": final_genders,
        "License": final_license_list,
        "Insurance": final_insurance_company_list,
        "State": final_states,
        "City": final_citys,
        "URL": crash_link,
        })

        df_final = pd.concat([df_final, df_temp], ignore_index=True)


    # -------------------------------------- DF managing -------------------------------------------------------
    df=df_final
    # Colunas a serem ajustadas
    cols_to_explode = ["Driver", "Age", "Gender","License", "Insurance", "State", "City"]

    # Ajustando para que cada coluna tenha o mesmo número de elementos por linha
    max_len = df[cols_to_explode].applymap(len).max(axis=1)

    for col in cols_to_explode:
        df[col] = df.apply(lambda row: row[col] + [""] * (max_len[row.name] - len(row[col])), axis=1)

    # Explodindo corretamente, mantendo alinhamento
    df_expanded = df.explode(cols_to_explode, ignore_index=True)
    # info datafram
    try:
        print_dataframe_info(df_expanded)
    except Exception as e:
        logger.warning("Error in struct dataframe")
    #insert into DB
    insert_full_crash_data(df_expanded, kansas_dir)
    #add current date to file name ojo
    file_name='Data_Crashes_Kansas_24H_'+desired_date.strftime('%Y%m%d')+'.csv'

    #save file in saved_files/ folder
    file_name=os.path.join(path_dir, "kansas",file_name)

    df_expanded.to_csv(file_name,index=False)
    logger.info(f"File csv loaded!: {file_name}")

# Add src/ folder to sys.path to import scraper and parser modules
#base_dir = os.path.dirname(os.path.abspath(__file__))
#sys.path.insert(0, base_dir)
#output_dir = "/Users/cristianb/Documents/Python/rel8ed/SynapseIQ_staging/storage"
#output_dir = "/home/data"
#run_kansas_crash_scraper(output_dir)

