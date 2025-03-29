import requests
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import pdfplumber
import re
import os
from weasyprint import HTML
import psycopg2
import json
from datetime import datetime


def insert_full_crash_data(df_expanded):
    conn = psycopg2.connect(
        dbname="crash_records",
        user="synapseiq",
        password="SynapseIQ$2025",
        host="localhost",
        port="5432"
    )
    cur = conn.cursor()

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

        accident_dt_str = f"{row['Date']} {row['Time']}"
        try:
            accident_dt = datetime.strptime(accident_dt_str, "%m/%d/%Y %H:%M")
        except ValueError:
            accident_dt = None

        row_json = json.dumps(row.to_dict())

        # Insert incident if not exists
        cur.execute("""
            INSERT INTO incident_reports (
                report_number, source_url, accident_datetime, city, state, crash_severity, notes, json
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (report_number) DO NOTHING
        """, (
            report_number,
            url,
            accident_dt,
            city,
            state,
            severity,
            "Imported from df_expanded with JSON",
            row_json
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
                insurance,
                "Passenger record from CSV"
            ))

    conn.commit()
    cur.close()
    conn.close()



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

for days in range(1,2):  # 24h

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

    response = requests.post(
        'https://www.kansas.gov/khp-crashlogs/search.do',
        headers=headers,
        data=data,
        proxies=proxies
        )

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

        # Exibir os resultados
        print("Date:", Date)
        print("Time:", Time)
        print("Type:", accident_type)
        print("Drivers:", driver_names)
        print("Insurance:", insurance_company_list)
        print("License:", license_list)
        print("City:", States)
        print("State:", citys)
        print("Age:", Age)
        print("--------------------")

        url = 'https://www.kansas.gov/khp-crashlogs/search/viewDetail/2025-'''+crash_number[i]+''
        output_pdf = "/home/SynapseIQ_temp/data/"+ crash_number[i]+".pdf"
        #output_pdf = crash_number[i]+".pdf"

        # Converte a página para PDF
        #pdfkit.from_url(url, output_pdf)
        HTML(url).write_pdf(output_pdf)

        print(f"Página salva como {output_pdf}")




    # DF for the current day in "days"
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


# -------------------------------------- DF managing -------------------------------------------------------
df=df_final
# Colunas a serem ajustadas
cols_to_explode = ["Driver", "Age", "License", "Insurance", "State", "City"]

# Ajustando para que cada coluna tenha o mesmo número de elementos por linha
max_len = df[cols_to_explode].applymap(len).max(axis=1)

for col in cols_to_explode:
    df[col] = df.apply(lambda row: row[col] + [""] * (max_len[row.name] - len(row[col])), axis=1)

# Explodindo corretamente, mantendo alinhamento
df_expanded = df.explode(cols_to_explode, ignore_index=True)
# insert into DAtaBase
insert_full_crash_data(df_expanded)

#add current date to file name
file_name='Data_Crashes_Kansas_24H_'+desired_date.strftime('%Y%m%d')+'.csv'

#save file in saved_files/ folder
# file_name=os.path.join('saved_files',file_name)
# Ruta de guardado deseada
output_dir = '/home/SynapseIQ_temp/data' #'/Users/cristianb/Documents/Python/SynapseIQ_001/SynapseIQ_Lab_01' 
output_path = os.path.join(output_dir, file_name)

df_expanded.to_csv(output_path,index=False)
print("File loaded!")