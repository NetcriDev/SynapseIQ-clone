import requests
from src.utils.logger_config import setup_logger
import pandas as pd
from bs4 import BeautifulSoup
import pdfkit
from datetime import datetime, timedelta
import re
from weasyprint import HTML
from datetime import datetime
from config.config import get_connection
import psycopg2
import json


output_dir = "/Users/cristianb/Documents/Python/rel8ed/SynapseIQ_staging/storage"
output_home = "/Users/cristianb/Documents/Python/rel8ed/SynapseIQ_staging"
logger = setup_logger("MSP_execution", output_home)


def insert_dataframe_to_db(df, pdf_base_path):
    conn = get_connection()
    cur = conn.cursor()

    for _, row in df.iterrows():
        report_number = str(row['ID']).strip()
        accident_datetime = pd.to_datetime(row['Date']) if pd.notna(row['Date']) else None
        city = row['City'].strip() if pd.notna(row['City']) else ''
        street = row['Location'].strip() if pd.notna(row['Location']) else ''
        source_url = row['URL'].strip() if pd.notna(row['URL']) else ''
        narrative = row['Description'].strip() if pd.notna(row['Description']) else ''
        driver = row['Driver'].strip() if pd.notna(row['Driver']) else ''
        age = int(row['Age']) if pd.notna(row['Age']) else None
        media_contact = row['Media Contact'].strip() if pd.notna(row['Media Contact']) else ''
        crash_severity = row['Type'].strip() if pd.notna(row['Type']) else ''
        original_document_location = f"{pdf_base_path}/ms{report_number}.pdf"
        generation_date = datetime.now()
        case_number= row['Case Number'].strip() if pd.notna(row['Case Number']) else ''

        # JSON completo del registro
        row_json = json.dumps(row.dropna().to_dict(),default=str)

        # Verificar si ya existe el incidente
        cur.execute("SELECT id FROM incident_reports WHERE report_number = %s", (report_number,))
        result = cur.fetchone()
        if result:
            incident_id = result[0]
        else:
            cur.execute("""
                INSERT INTO incident_reports (
                    report_number, accident_datetime, city, street,
                    state, source_url, narrative, original_document_location,
                    generation_date, original_format, notes, crash_severity, json
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                report_number,
                accident_datetime,
                city,
                street,
                "Minnesota",                   # state
                source_url,
                narrative,
                original_document_location,
                generation_date,
                "pdf",                         # original_format
                "Case Number: " + case_number + ". " + media_contact,                # notes
                crash_severity,               # crash_severity
                row_json
            ))
            incident_id = cur.fetchone()[0]

        # Verificar si ya existe el vehículo para ese conductor
        cur.execute("""
            SELECT id FROM vehicles
            WHERE incident_report_id = %s AND driver_name = %s
        """, (incident_id, driver))
        result = cur.fetchone()
        if result:
            vehicle_id = result[0]
        else:
            cur.execute("""
                INSERT INTO vehicles (
                    incident_report_id, driver_name, notes
                ) VALUES (%s, %s, %s)
                RETURNING id
            """, (incident_id, driver, "Imported from CSV"))
            vehicle_id = cur.fetchone()[0]

        # Verificar si ya existe el pasajero tipo "Driver"
        cur.execute("""
            SELECT id FROM passengers
            WHERE vehicle_id = %s AND name = %s
        """, (vehicle_id, driver))
        result = cur.fetchone()
        if not result:
            cur.execute("""
                INSERT INTO passengers (
                    vehicle_id, role, name, age, notes
                ) VALUES (%s, %s, %s, %s, %s)
            """, (
                vehicle_id,
                'Driver',
                driver,
                age,
                " "     #notes
            ))

    conn.commit()
    cur.close()
    conn.close()
    print("Data inserted successfully.")




# Creating lists for scrapping table content
logger.info(f"Date and time of execution: {datetime.now()}")
date_list=[]
crash_type=[]

driver_list=[]

crash_number=[]
crash_link=[]

final_driver_list=[]
final_citys=[]
final_ages=[]

icr_out=[]
district_out=[]
case_out=[]
contact_out=[]
location_out=[]
description_out=[]

# ------------------------- proxies ----------------------------

username = 'rrel8ed'
password = 'zFfUPRWH6q'
country = 'CA'
entry = ('http://customer-%s-cc-%s:%s@pr.oxylabs.io:7777' %
    (username, country, password))
 
proxies = {
    'http': entry,
    'https': entry,
}

# ------------------------- request ----------------------------

headers = {
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'accept-language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
    'cache-control': 'max-age=0',
    'priority': 'u=0, i',
    'sec-ch-ua': '"Not(A:Brand";v="99", "Google Chrome";v="133", "Chromium";v="133"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'document',
    'sec-fetch-mode': 'navigate',
    'sec-fetch-site': 'cross-site',
    'sec-fetch-user': '?1',
    'upgrade-insecure-requests': '1',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
    # 'cookie': '__uzma=dc2a45a3-5a6f-49da-a2de-9058dc1be4b8; __uzmb=1739969577; __uzme=9423; __ssds=2; __ssuzjsr2=a9be0cd8e; __uzmbj2=1739969581; __uzmlj2=EAINVnkjSCguQymb6JNC4PYuFT1j6P4hrmfG9Pf+Bd0=; __uzmaj2=dc2a45a3-5a6f-49da-a2de-9058dc1be4b8; __uzmcj2=358371677588; __uzmdj2=1739969658; __uzmfj2=7f60009215922a-6365-486b-af30-defd8d15d620173996958138076962-ede9017c8e11645416; uzmxj=7f90001266c8b2-a70d-424c-a594-72d455087e2c1-173996958138076962-8be07e77a65b716d16; __uzmc=371491948521; __uzmd=1739969723',
}

response = requests.get('https://app.dps.mn.gov/MSPMedia2/Current', headers=headers, proxies=proxies, verify=False)

# update html content and acquire data
soup = BeautifulSoup(response.content, 'html.parser')
main_content = soup.find_all("div", class_="col-md-10 col-xs-8")
# print(main_content)

for x in range(len(main_content)):
    crash_link.append("https://app.dps.mn.gov" + main_content[x].find("a").get("href"))
# print(crash_link)
# now we have a list of all links to crash reports

for y in range(len(crash_link)):
    crash_number.append(main_content[y].find("a").text)
# print(crash_number)

df_final = pd.DataFrame()

# for i in range(len(crash_number)):
for i in range(8):
    # new request for next page
    headers = {
       'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
        'cache-control': 'max-age=0',
        'priority': 'u=0, i',
        'sec-ch-ua': '"Not(A:Brand";v="99", "Google Chrome";v="133", "Chromium";v="133"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'cross-site',
        'sec-fetch-user': '?1',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
        # 'cookie': '__uzma=dc2a45a3-5a6f-49da-a2de-9058dc1be4b8; __uzmb=1739969577; __uzme=9423; __ssds=2; __ssuzjsr2=a9be0cd8e; __uzmbj2=1739969581; __uzmlj2=EAINVnkjSCguQymb6JNC4PYuFT1j6P4hrmfG9Pf+Bd0=; __uzmaj2=dc2a45a3-5a6f-49da-a2de-9058dc1be4b8; __uzmcj2=358371677588; __uzmdj2=1739969658; __uzmfj2=7f60009215922a-6365-486b-af30-defd8d15d620173996958138076962-ede9017c8e11645416; uzmxj=7f90001266c8b2-a70d-424c-a594-72d455087e2c1-173996958138076962-8be07e77a65b716d16; __uzmc=371491948521; __uzmd=1739969723',
        }
    
    response = requests.get(
        crash_link[i],
        headers=headers,
        proxies=proxies
        )

    # update html content and acquire data
    soup = BeautifulSoup(response.content, 'html.parser')

    # Extrair data e hora
    match = re.search(r"Date/Time:\s*(.*)", soup.get_text())
    Date = match.group(1).strip() if match else "N/A"

    # Extrair tipo de acidente
    match = re.search(r"Incident type:\s*(.*)", soup.get_text())
    accident_type = match.group(1).strip() if match else "N/A"

    icr=''
    district=''
    case=''
    contact=''
    location=''
    description=''
    #getting general info
    for incident_content in soup.find('div',id='incident-body').find_all('div',class_='row'):
    #lets get internal divs
        divs=incident_content.find_all('div')
        for k in range(len(divs)):
            if 'Incident type' in divs[k].text:
                incident_type=divs[k+1].text.strip()
            if 'ICR' in divs[k].text:
                icr=divs[k+1].text.strip()
            if 'Date/Time' in divs[k].text:
                date=divs[k+1].text.strip()
            # if 'District' in divs[k].text:
            #     district=divs[k+1].text.strip()
            if 'Case Info' in divs[k].text:
                case=divs[k+1].text.strip()
            if 'Media Contact' in divs[k].text:
                contact=divs[k+1].text.strip()
            if 'Location:' in divs[k].text:
                location=divs[k+2].text.strip()
            if 'Description' in divs[k].text:
                description=divs[k+1].text.strip()


    # Extrair nome dos motoristas
    driver_names = []
    citys = []
    States=[]
    Age=[]

    #print(soup.find_all("div", class_="row person-form"))
    for driver_section in soup.find_all("div", class_="row person-form"):
        # Nome
        name_tag = driver_section.find_next("div", class_="col-md-12 col-xs-12")
        name = name_tag.get_text(strip=True)
        

        city_tag = driver_section.find_next("div", class_="col-md-12 col-xs-12").find_next("div", class_="col-md-12 col-xs-12").find_next("div", class_="col-md-12 col-xs-12")
        city = city_tag.get_text().strip()
        citys.append(city)

        age_tag = driver_section.find_next("div", class_="col-md-12 col-xs-12").find_next("div", class_="col-md-12 col-xs-12").find_next("div", class_="col-md-12 col-xs-12").find_next("div", class_="col-md-12 col-xs-12")
        if age_tag and "Age:" in age_tag.get_text():
            age = age_tag.get_text().split(":", 1)[1].strip()
            Age.append(age)
        else:
            if "Age:" in name:
                age = name.split(":", 1)[1].strip()
                Age.append(age)
                name='N/A'
            else:
                Age.append("N/A")
        driver_names.append(name)

    # append content
    date_list.append(Date)

    # driver_list.append(driver_names)
    crash_type.append(accident_type)

    final_driver_list.append(driver_names)
    final_citys.append(citys)
    final_ages.append(Age)

    icr_out.append(icr)
    # district_out.append(district)
    case_out.append(case)
    contact_out.append(contact)
    location_out.append(location)
    description_out.append(description)

    # Exibir os resultados
    print("Drivers:", driver_names)
    print("City:", citys)
    print("Age:", Age)
    print("--------------------")

    url = crash_link[i]
    output_pdf = output_dir + "/ms" + crash_number[i] + ".pdf"

    df_temp = pd.DataFrame({
    "ID": [crash_number[i]]*len(driver_names),
    "Date": [Date]*len(driver_names),
    "Type": [accident_type]*len(driver_names),
    "ICR":[icr]*len(driver_names),
    # "District":[district]*len(driver_names),
    "Case Number":[case]*len(driver_names),
    "Media Contact":[contact]*len(driver_names),
    "Location":[location]*len(driver_names),
    "Description":[description]*len(driver_names),
    "Driver": driver_names,
    "Age": Age,
    "City": citys,
    "URL": [url]*len(driver_names),
    })
    
    # Criando datas de hoje e ontem como objetos datetime
    date_today = (datetime.now() - timedelta(1)).date()
    date_yesterday = (datetime.now() - timedelta(2)).date()
    
    # Convertendo a coluna 'Date' para datetime
    df_temp['Date'] = pd.to_datetime(df_temp['Date'], format='%m/%d/%Y %H:%M', errors='coerce')

    # Verifica se há alguma linha com data de ontem ou anteontem
    if df_temp['Date'].dt.date.isin([date_today, date_yesterday]).any():
        df_final = pd.concat([df_final, df_temp], ignore_index=True)
        # Converte a página para PDF
        try:
            HTML(url).write_pdf(output_pdf)
            print(f"saved pdf {output_pdf}")
        except:
            try:
                pdfkit.from_url(url, output_pdf)
                print(f"saved pdf {output_pdf}")
            except:
                print(f"could not save pdf {output_pdf}")

    

#old method doesnt split people in different rows:
# DF for the current day in "days"
# df_temp = pd.DataFrame({
# "ID": crash_number,
# "Date": date_list,
# "Type": crash_type,
# "ICR":icr_out,
# "District":district_out,
# "Case Number":case_out,
# "Contact":contact_out,
# "Location":location_out,
# "Description":description_out,
# "Driver": final_driver_list,
# "Age": final_ages,
# "City": final_citys,
# "URL": crash_link,
# })
# df_final = pd.concat([df_final, df_temp], ignore_index=True)
insert_dataframe_to_db(df_final, output_dir)
df_final.to_csv('output.csv',index=False)





