import requests
import json
import re
import os
import pdfplumber
import sys
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from config.config import get_connection
from src.utils.logger_config import setup_logger
from src.utils.info_dataframe import print_dataframe_info
import numpy as np

main_script_path = sys.path[0]
logger = setup_logger("Winstonsalem_execution", main_script_path)


#insert into DB
def insert_dataframe_into_db(df: pd.DataFrame, file_path: str):
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

        city = str(row.get('City', '')).strip()
        state = str(row.get('State', '')).strip()
        street = str(row.get('STREET', '')).strip()
        driver = str(row.get('Driver', '')).strip()
        vin = str(row.get('VIN', '')).strip()
        insurance = str(row.get('Insurance', '')).strip()
        policy = str(row.get('Policy', '')).strip()
        generation_date = datetime.now()
        age = int(row['Age']) if pd.notnull(row.get('Age')) and str(row.get('Age')).strip().isdigit() else None
        date_birth = int(row['Date of Birth']) if pd.notnull(row.get('Date of Birth')) and str(row.get('Date of Birth')).strip().isdigit() else None
        row_json = json.dumps(row.dropna().to_dict())
        original_document_location = os.path.join(file_path,"WSP-"+str(datetime.now().year)+"-"+report_number+".pdf")  # ubicación real del PDF

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
                    original_format
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                "pdf"
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
                        incident_report_id, vin, insurance_company, policy_number,
                        driver_name, technical_notes
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    incident_id,
                    vin,
                    insurance,
                    policy,
                    driver,
                    "Inserted from WSP Daily DataFrame"
                ))
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
                        vehicle_id, role, name, technical_notes, age, year_birth
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    vehicle_id,
                    'Driver',
                    driver,
                    "Inserted from WSP Daily DataFrame",
                    age,
                    date_birth
                ))

    conn.commit()
    cur.close()
    conn.close()
    logger.info("Data successfully inserted: WinstonSalem")

# Função para extrair os nomes dos motoristas
def extrair_motoristas(texto):
    # Captura qualquer sequência de nomes entre "20VEHICLE" e "Driver Driver"
    padrao = r"20VEHICLE\n([A-Z\s'-]+(?:\s[A-Z'-]+){0,3})\nDriver Driver"
    resultado = re.findall(padrao, texto, re.MULTILINE)
    resultado = [res.replace('UNKNOWN UNKNOWN','UNKNOWN') for res in resultado]

    # Separar os nomes corretamente se houver múltiplos
    nomes_extraidos = []
    for grupo in resultado:
        nomes_extraidos.extend(re.split(r'\s{2,}|\n', grupo.strip()))  # Garantir que cada nome seja separado corretamente

    return [nome.strip() for nome in nomes_extraidos if nome.strip()]  # Remover espaços extras

# Função para separar motoristas de acordo com os sobrenomes
def separar_motoristas_por_nome(nomes, sobrenomes):
    motoristas = []
    
    for nome in nomes:
        partes_nome = nome.split()
        nome_completo = []
        nome_atual = []

        # for parte in partes_nome:
        #     nome_atual.append(parte)
        #     # Verifica se algum dos sobrenomes contém esta parte
        #     for sobrenome in sobrenomes:
        #         sobrenome_variantes = [s.strip() for s in sobrenome.split(';')]  # Considera sobrenomes compostos
        #         if parte in sobrenome_variantes:
        #             if nome_completo:
        #                 motoristas.append(' '.join(nome_completo))
        #             nome_completo = nome_atual
        #             nome_atual = []
        #             break
        
        # if nome_completo:
        #     motoristas.append(' '.join(nome_completo))

        #codigo patrick:::::
        
        nome_completo=' '.join(nomes)
        # print(nome_completo)
        for sobrenome in sobrenomes:
            sobrenome_split=sobrenome.split(';')
            sobrenome_split=[sobr.strip() for sobr in sobrenome_split]
            if all(sobr[0:16] in nome_completo for sobr in sobrenome_split): #[0:16] pois nomes maiores ficam truncados para fora da string
                #encontrado o sobreno especifico para esse nome
                for sobr in sobrenome_split:
                    motoristas.append((nome_completo.split(sobr[0:16])[0].strip()+' '+sobr).strip())
                    nome_completo=sobr.join(nome_completo.split(sobr[0:16])[1:])
    return motoristas

# Função para validar VINs
def is_valid_vin(vin):
    # Verifica se o VIN tem 17 caracteres
    if len(vin) != 17:
        return False
    # Verifica se o VIN contém apenas caracteres alfanuméricos válidos (exceto I, O, Q)
    invalid_chars = {'I', 'O', 'Q'}
    return all(char.isalnum() and char not in invalid_chars for char in vin)

def fix_city_state_base_insurance(cityState,insurances): #inserir vazios para corrigir cidade e estado, baseado na insurance (pressupoe que está correto)
    if len(cityState)>len(insurances):
        return cityState
    
    content_out=[] #cityState corrigido
    idx_ref=0 #index de cityState
    for insurance in insurances:
        if insurance=='':
            content_out.append('')
        else:
            if idx_ref+1<=len(cityState):
                content_out.append(cityState[idx_ref])
                idx_ref+=1
    
    return content_out



def run_wsp_crash_scraper(output_dir):
    """
    Scrapes crash data from the Winston Salem crash reporting system.

    Parameters
    ----------
    path_dir : str
        Path to the directory where downloaded files, storage folder (storage) or results should be stored.

    Returns
    -------
    None
    """
    # Creating lists for scrapping table content
    list_report=[]
    list_date=[]
    list_driver=[]
    list_street=[]
    list_url=[]
    list_url_final=[]
    list_insurance=[]
    list_vin=[]
    list_policy=[]
    owner_list=[]
    list_cities=[]
    list_States=[]
    list_Addresses=[]
    list_DOB=[]

    # Creating Date Variable
    days=2 #2
    # (-1) from today
    desired_date = datetime.now() - timedelta(days)
    logger.info(desired_date)
    # Format 1: 2024.11.6 (NOV)
    format1 = desired_date.strftime('%Y.%m.%d')
    # Format 2: 11/06/2024 (NOV)
    format2 = desired_date.strftime('%m/%d/%Y')
    # beggining of month
    first_day_of_month = datetime.now().replace(day=1).strftime('%Y.%m.%d')

    viewstate='/wEPDwUJNTkyNDI3NTY2D2QWAgIDD2QWAgIDD2QWCGYPZBYCZg9kFgJmDw8WAh4EVGV4dAVGV2VsY29tZSB0byBXaW5zdG9uLVNhbGVtIFBvbGljZSBEZXBhcnRtZW50J3M8YnIvPkNyYXNoIFJlcG9ydCBEYXRhYmFzZWRkAgEPDxYCHgdWaXNpYmxlaGRkAgIPZBYCZg9kFgJmD2QWAmYPZBYCZg9kFgJmD2QWAmYPZBYCZg9kFgICAg9kFgICAQ9kFgJmD2QWAgIBD2QWBmYPZBYEAgEPZBYCZg8PFgIfAGVkZAIDD2QWBGYPDxYCHwBlZGQCAw8WBh4MU2VsZWN0ZWREYXRlZB4KRGF0ZUZvcm1hdAUKTU0vZGQveXl5eR4NQ2FsZW5kYXJJdGVtcwUMPGNhbGVuZGFyIC8+ZAIBD2QWBAIBD2QWAmYPDxYCHwBlZGQCAw9kFgJmDw8WAh8AZWRkAgMPDxYCHwFnZBYCZg9kFgJmDw8WBB8ABYwBVG8gcmVjZWl2ZSBhbiBlbGVjdHJvbmljIGNvcHkgb2YgYSBXaW5zdG9uLVNhbGVtIFBvbGljZSBEZXBhcnRtZW50IENyYXNoIFJlcG9ydCw8YnIvPnBsZWFzZSBzZWFyY2ggdXNpbmcgYXQgbGVhc3Qgb25lIG9mIHRoZSBhYm92ZSBjcml0ZXJpYS4fAWdkZAIDD2QWAmYPZBYCZg9kFgJmD2QWAmYPZBYCZg9kFgJmD2QWAmYPZBYCAgIPZBYCAgEPZBYCZg9kFgICAQ9kFgJmDzwrAAoBAA8WAh4LRm9sZGVyU3R5bGUFHC9TdHlsZXMvZ3JhbmRfZ3JheS9PYm91dEdyaWRkZBgBBR5fX0NvbnRyb2xzUmVxdWlyZVBvc3RCYWNrS2V5X18WAwUVQVNQeFJvdW5kUGFuZWwyJGdyaWQxBRhBU1B4Um91bmRQYW5lbDEkaW1nQ2xlYXIFGUFTUHhSb3VuZFBhbmVsMSRDYWxlbmRhcjHpftIgY0nTcB2cZR0DZcCDlzBjZx/42/kW4Vu/EuQh9g=='
    eventvalidation='/wEdAATRou6MHqSWkBDZQ7SCXAv3PIMmlrdlpXESQnOS4mHW+QFkT5n3l3TDiP1aCzZXk2iTHpfAQzQZ2fZHXAwYa9/JLgIfiyr04Ed69IzuiKamOI6O3qXOtz9TSjVvT+VoL08='
    viewstateContainer=''

    # 1st request based on a date
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
        'Cache-Control': 'max-age=0',
        'Connection': 'keep-alive',
        'Content-Type': 'application/x-www-form-urlencoded',
        # 'Cookie': 'ASP.NET_SessionId=btr1teshyztsluy4x2wqixd1',
        'Origin': 'https://winston-salem.ecrash.interplat.com',
        'Referer': 'https://winston-salem.ecrash.interplat.com/SearchReports.aspx',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-User': '?1',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'sec-ch-ua': '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
    }
    data = {
        'h_ASPxRoundPanel1_Calendar1': ''+format1+';'+first_day_of_month+'',
        'sd_ASPxRoundPanel1_Calendar1': '',
        '__EVENTTARGET': '',
        '__EVENTARGUMENT': '',
        '__VIEWSTATE': viewstate,
        '__VIEWSTATEGENERATOR': '0C6A3359',
        '__EVENTVALIDATION': eventvalidation,
        'ASPxRoundPanel1$txtLocalUse': '',
        'ASPxRoundPanel1$txtDate': ''+format2+'',
        'ASPxRoundPanel1$txtLastName': '',
        'ASPxRoundPanel1$txtRoadName': '',
        'ASPxRoundPanel1$btnSearch': 'Search',
        'DXScript': '1_42',
    }
    response = requests.post(
        'https://winston-salem.ecrash.interplat.com/SearchReports.aspx',
        headers=headers,
        data=data,
    )

    # Update url
    soup = BeautifulSoup(response.content, 'html.parser')
    viewstate= soup.find("input", id="__VIEWSTATE").get_attribute_list("value")[0].replace('+','%2B').replace('/','%2F').replace('=','%3D').replace('&','%26').replace(' ','%20')
    eventvalidation= soup.find("input", id="__EVENTVALIDATION").get_attribute_list("value")[0].replace('+','%2B').replace('/','%2F').replace('=','%3D').replace('&','%26').replace(' ','%20')
    viewstateContainer= soup.find("input", id="ASPxRoundPanel2_grid1_ob_grid1ViewstateContainer").get_attribute_list("value")[0].replace('+','%2B').replace('/','%2F').replace('=','%3D').replace('&','%26').replace(' ','%20')

    # Find main table and scrap content || For 1st page
    soup = BeautifulSoup(response.content, 'html.parser')
    trs_table = soup.find("table", class_="ob_gBody").find("tbody").find_all("tr")

    for i in range(len(trs_table)):
        list_report.append(trs_table[i].find_all("td")[1].find("a").text)
        list_date.append(trs_table[i].find_all("td")[2].find("div").find_all("div")[1].text)
        list_driver.append(trs_table[i].find_all("td")[3].text)
        list_street.append(trs_table[i].find_all("td")[4].text)
        list_url.append(trs_table[i].find_all("td")[1].find("a").get("href"))

    # 1st page done --> now we need to get the rest of the pages
    # Getting the amount of pages
    pages=0
    try:
        # Missing pages for scrapping
        pages=int(soup.text.split('10 of ')[-1][0:2].replace('\\',''))
        # Round up the rest of division, to get total pages
        pages=pages//10 + (pages % 10 > 0) -1
    except:
        pages = 0
    logger.info('pages total:' + str(pages))

    # Update data info in response to get other page details
    for page in range(pages):
        logger.info('running page' + str(page))
        data = ('''__EVENTTARGET=&__EVENTARGUMENT=&__VIEWSTATE='''+viewstate.replace('/','%2F')+'''&__VIEWSTATEGENERATOR=0C6A3359&ob_iDdlob_grid1PageSizeSelectorTB=10&ASPxRoundPanel2%24grid1%24ob_grid1FooterContainer%24ob_grid1PageSizeSelector=10&ob_iDdlob_grid1PageSizeSelectorSIS=1&ASPxRoundPanel2%24grid1%24ob_grid1EditControl1=&ASPxRoundPanel2%24grid1%24ob_grid1EditControl2=&ASPxRoundPanel2%24grid1%24ob_grid1EditControl3=&ASPxRoundPanel2%24grid1%24ob_grid1EditControl4=&ASPxRoundPanel2%24grid1%24ob_grid1ViewstateContainer='''+
                viewstateContainer
                +'''&ASPxRoundPanel2%24grid1%24ob_grid1EMRC=&ASPxRoundPanel2%24grid1%24ob_grid1PageSelector='''+
                str(1+page)+'''&ASPxRoundPanel2%24grid1%24ob_grid1TotalRecords=32&ASPxRoundPanel2%24grid1%24ob_grid1CellDivsWidthContainer=&ASPxRoundPanel2%24grid1%24ob_grid1ColumnsWidthContainer=0%2C110%2C90%2C50%25%2C50%25&ASPxRoundPanel2%24grid1%24ob_grid1VSC=&ASPxRoundPanel2%24grid1%24ob_grid1FBConfC=1&ASPxRoundPanel2%24grid1%24ob_grid1CFEC=&ASPxRoundPanel2%24grid1%24ob_grid1SerializedCols=key_crash*_o_osep_*None*_o_osep_*0*_o_osep_*false*_o_osep_*0*_o_osep_*false*_o_osep_*0*_o_osep_*key_crash*_o_asep_*LocalUse*_o_osep_*Desc*_o_osep_*0*_o_osep_*false*_o_osep_*0*_o_osep_*true*_o_osep_*1*_o_osep_*LocalUse*_o_asep_*DateOfCrash*_o_osep_*None*_o_osep_*0*_o_osep_*false*_o_osep_*0*_o_osep_*true*_o_osep_*2*_o_osep_*DateOfCrash*_o_asep_*LastName*_o_osep_*None*_o_osep_*0*_o_osep_*false*_o_osep_*0*_o_osep_*true*_o_osep_*3*_o_osep_*LastName*_o_asep_*RoadOn*_o_osep_*None*_o_osep_*0*_o_osep_*false*_o_osep_*0*_o_osep_*true*_o_osep_*4*_o_osep_*RoadOn&ASPxRoundPanel2%24grid1%24ob_grid1SortExpression=&ASPxRoundPanel2%24grid1%24ob_grid1SortOrder=&&__ob_gridgrid1IsCallback=1&__CALLBACKID=ASPxRoundPanel2%24grid1&__CALLBACKPARAM=&__EVENTVALIDATION='''+eventvalidation.replace('/','%2F')
                )
        try:
            response = requests.post(
                'https://winston-salem.ecrash.interplat.com/SearchReports.aspx',
                headers=headers,
                data=data,
            )
        except Exception as e:
            logger.error(e)
        # Update html and scrap each page remaining
        soup = BeautifulSoup(response.content, 'html.parser')
        trs_table = soup.find("table", class_="ob_gBody").find("tbody").find_all("tr")
        for i in range(len(trs_table)):
            list_report.append(trs_table[i].find_all("td")[1].find("a").text)
            list_date.append(trs_table[i].find_all("td")[2].find("div").find_all("div")[1].text)
            list_driver.append(trs_table[i].find_all("td")[3].text)
            list_street.append(trs_table[i].find_all("td")[4].text)
            list_url.append(trs_table[i].find_all("td")[1].find("a").get("href"))

    # get ID and find final URL
    base_url = "https://winston-salem.ecrash.interplat.com/ShowReport.aspx?id="
    list_url_final=[]
    for k in range(len(list_url)):
        report_id = list_url[k].split("id=")[1].split("'")[0]
        list_url_final.append(f"{base_url}{report_id}")

    # PDF Scrapping ---------------------------------------------------------------------------------
    logger.info("List Driver: " + str(list_driver))
    for k in range(len(list_url)):
        attempts=0
        while attempts<10:
            headers = {
                'Accept': '*/*',
                'Accept-Language': 'en-US,en;q=0.9,pt;q=0.8',
                'Connection': 'keep-alive',
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                # 'Cookie': 'ASP.NET_SessionId=g4glkvl5feznja3yxitocl2i',
                'Origin': 'https://winston-salem.ecrash.interplat.com',
                'Referer': list_url_final[k],
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-origin',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
                'sec-ch-ua': '"Not A(Brand";v="8", "Chromium";v="132", "Google Chrome";v="132"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
            }
            params = {
                'id': list_url_final[k].split("id=")[-1],
            }
            data = {
                '__EVENTTARGET': '',
                '__EVENTARGUMENT': '',
                '__VIEWSTATE': '/wEPDwULLTEzNDEwMTk5MDZkZKhdvVrQ8umwjIp00WHWvW0x71Cz3mV+jz8cFgPHLYVY',
                '__VIEWSTATEGENERATOR': '0E95757D',
                'DXScript': '1_42,1_75,1_40,1_57',
                '__CALLBACKID': 'ASPxCallback1',
                '__CALLBACKPARAM': 'c0:',
                '__EVENTVALIDATION': '/wEdAALwSOy1zNsBlN7c9Srenp3RWHVOJnwVPmH5+9jYfGZMnyOnYOWzG6WjtP7ORJz7EE3Dpd3InCEvvC72WY3wjWRA',
            }
            response = requests.post(
                'https://winston-salem.ecrash.interplat.com/ShowReport.aspx',
                params=params,
                # cookies=cookies,
                headers=headers,
                data=data,
                # verify=False,
            )

            response.raise_for_status()  # verify if download was a success

            # print(response.content)
            conteudo=str(response.content)
            conteudo = conteudo.split("'data':'")[-1].split("'")[0]
            # print(conteudo)

            # ----------------------------------------------------------

            # URL do arquivo que você deseja baixar
            new_url = "https://winston-salem.ecrash.interplat.com" + conteudo
            #print(new_url)

            # Define the directory and ensure it exists
            path_ws = os.path.join(output_dir, "winstonsalem")
            os.makedirs(path_ws, exist_ok=True)

            file_path2 = os.path.join(path_ws,"temp_file.txt") 

            headers = {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'Accept-Language': 'en-US,en;q=0.9,pt;q=0.8',
                'Connection': 'keep-alive',
                'DNT': '1',
                'If-Modified-Since': 'Tue, 01 Feb 2020 11:48:19 GMT',
                'If-None-Match': '"365065d87a7cdb1:0"',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Upgrade-Insecure-Requests': '1',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 Edg/132.0.0.0',
                'sec-ch-ua': '"Not A(Brand";v="8", "Chromium";v="132", "Microsoft Edge";v="132"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
            }

            #now download pdf from link
            response = requests.get(new_url, headers=headers,stream=True) #verify=False
            with open(os.path.join(path_ws,"temp_file.pdf"), "wb") as pdf:
                for chunk in response.iter_content(chunk_size=4096):
                    if chunk:
                        pdf.write(chunk)

            # Criar uma cópia do arquivo como "xx.pdf"
            file_path_data=os.path.join(path_ws,"WSP-"+str(datetime.now().year)+"-"+list_report[k]+".pdf")
            with open(os.path.join(path_ws,"temp_file.pdf"), "rb") as temp_pdf, open(file_path_data, "wb") as copy_pdf:
                copy_pdf.write(temp_pdf.read())

            try:
                with pdfplumber.open(os.path.join(path_ws,'temp_file.pdf')) as pdf:
                    pass
                break
            except:
                os.remove(os.path.join(path_ws,'temp_file.pdf'))
                response = requests.get(new_url, headers=headers,stream=True) #verify=False
                with open(os.path.join(path_ws,'temp_file.pdf'), "wb") as pdf:
                    for chunk in response.iter_content(chunk_size=4096):
                        if chunk:
                            pdf.write(chunk)

                # Criar uma cópia do arquivo como "xx.pdf"
                logger.warning(" list_report: " + str(list_report[k]))
                with open(os.path.join(path_ws,'temp_file.pdf'), "rb") as temp_pdf, open(os.path.join(path_ws,list_report[k]+".pdf"), "wb") as copy_pdf:
                    copy_pdf.write(temp_pdf.read())

                attempts+=1
                continue
            attempts+=1

        # Abrir o arquivo PDF
        with pdfplumber.open(os.path.join(path_ws,'temp_file.pdf')) as pdf:
            texto = ''
            nomes_extraidos=[]
            # Extrair texto de cada página
            for pagina in pdf.pages:
                pagina_partial=pagina.extract_text()
                texto += pagina_partial
                #print(texto)
                nomes_extraidos = nomes_extraidos + extrair_motoristas(pagina_partial)
            # owners = texto.split('\nOwner')[-1].split('\n')[0]
            # owners = re.sub("\d+", "", owners).strip() # substitui por qualquer numero por nada em qualquer lugar
            # # print(owners)
            # owners = owners.split('Owner')
            # # print(owners)

            sobrenomes = list_driver
            
            # Chamar as funções
            
            owners = separar_motoristas_por_nome(nomes_extraidos, sobrenomes)
            #print(owners)

            # Extract Insurance
            insurance = []
            partes = texto.split("Insurance ")[1:]  # ignore first part
            for parte in partes:
                parte = parte.strip()  # delete empty spaces
                if parte:  # verify if its not empty
                    insurance_info = parte.split("Company")[0].strip() 
                    if insurance_info:  # verify if its not empty
                        insurance.append(insurance_info)
                    else:
                        insurance.append('')
                else:
                    insurance.append('')

            cities=[]
            States=[]
            # Encontrar a seção de "Driver Driver" até a próxima ocorrência de "City State Zip"
            match = re.search(r"Driver Driver.*?City State Zip", texto, re.DOTALL)
            if match:
                trecho_motoristas = match.group()
                # Regex para capturar "Cidade Estado" antes do ZIP code
                padrao = r"([A-Z\s]+) ([A-Z]{2}) \d{5}(-\d{4})?"
                resultados = re.findall(padrao, trecho_motoristas)
                # Caso não haja nenhum resultado, adiciona valores vazios
                if not resultados:
                    cities.append("")
                    States.append("")
                else:
                    # Exibir os resultados e fazer append nas listas
                    for cidade, estado, _ in resultados:
                        cities.append(cidade.strip())
                        States.append(estado)

            cities=fix_city_state_base_insurance(cities,insurance)
            States=fix_city_state_base_insurance(States,insurance)
            
            #get the address information
            Addresses=[]
            match_found=re.findall(r'First Middle Last.*?City State Zip',texto,re.DOTALL)
            for partial_content in match_found:
                partial_content=partial_content.split('First Middle Last')[-1].split('City State Zip')[0].strip().split('Address')[1:]
                partial_content=[content.split('\n')[0].strip() for content in partial_content]
                Addresses+=partial_content

            #get DOB information
            DOB=[]
            match_found=re.findall(r'\n.*DOB.*DOB.*\n',texto)
            for partial_content in match_found:
                partial_content=partial_content.split('DOB ')[1:]
                partial_content=[content.strip().split(' ')[0].strip().split('/')[-1].strip() for content in partial_content]
                DOB+=partial_content

            #print(cities), print(States),print(Addresses)

            # Extract VINs
            vins = []
            vin_parts = texto.split("VIN ")
            for part in vin_parts[1:]:  # ignore 1st part
                part = part.strip()  # remove espaços em branco
                if part:  # verifica se a parte não está vazia
                    vin = part.split()[0].strip()  # pega a primeira palavra após "VIN "
                    if vin and is_valid_vin(vin):  # verifica se o VIN não está vazio e é válido
                        vins.append(vin)

            # Extract Policy Numbers
            policies = []
            if "Policy #" in texto:
                policy_parts = texto.split("Policy #")
                for part in policy_parts[1:]:  # ignora a primeira parte
                    part = part.strip()  # remove espaços em branco
                    # print(part)
                    if part:  # verifica se a parte não está vazia
                        policy = part.partition("Policy #")[2].strip() # Passo 1: Dividir a string após "Policy #"
                        policy = part.partition("20 COMMERCIAL")[0].strip() # Passo 2: Dividir novamente, agora antes do "20"
                        # Verifica se o número da apólice é válido (não é "20" e é um número)
                        if policy != "20":  # evita capturar "20"
                            policies.append(policy)
                        else:
                            policies.append('')
                    else:
                        policies.append('')

        # Save content in list
        list_insurance.append(insurance)
        list_vin.append(vins)
        list_policy.append(policies)
        owner_list.append(owners)
        list_cities.append(cities)
        list_States.append(States)
        list_Addresses.append(Addresses)
        list_DOB.append(DOB)
        
        # Deleta o arquivo após a leitura
        os.remove(os.path.join(path_ws,'temp_file.pdf'))

    # print(texto)

    # DF Creation -----------------------------------------------------------------------------------
    df = pd.DataFrame({
        "REPORT": list_report,
        "DATE": list_date,
        "DRIVERS": owner_list,
        "STREET": list_Addresses, 
        "URL": list_url_final,
        "Insurances":list_insurance,
        "VINs": list_vin,
        "Policies": list_policy,
        "Cities": list_cities,
        "States": list_States,
        "DOB": list_DOB,
    })

    # Colunas que precisam ser expandidas
    cols_to_explode = ["DRIVERS", "Insurances", "VINs", "Policies", "Cities", "States","STREET","DOB"]

    # Garantir que todas as colunas tenham listas com o mesmo tamanho por linha
    max_len = df[cols_to_explode].applymap(len).max(axis=1)

    for col in cols_to_explode:
        df[col] = df.apply(lambda row: row[col] + [None] * (max_len[row.name] - len(row[col])), axis=1)

    # Explodir os dados para alinhar corretamente Motorista, Seguro e VIN
    df_expanded = df.explode(cols_to_explode, ignore_index=True)

    # Renomear colunas para um nome singular
    df_expanded.rename(columns={"DRIVERS": "Driver", "Insurances": "Insurance", "VINs": "VIN", "Policies": "Policy", 
                                "Cities": "City", "States": "State","DOB":"Date of Birth"}, inplace=True)

    # Substituir valores None por string vazia para evitar problemas ao salvar
    df_expanded.fillna("", inplace=True)

    df_expanded['Insurance']=df_expanded['Insurance'].apply(lambda x : x[:-9].strip() if x.strip().endswith('Insurance') else x)
    df_expanded.replace("", np.nan, inplace=True)
    df_expanded = df_expanded.dropna(subset=['Driver', 'Insurance','VIN','City','State'], how='all')
    df_expanded.fillna("", inplace=True)
    df_expanded.sort_values(by=["REPORT","Driver"],inplace=True)
    #drop duplicates keep first
    df_expanded.drop_duplicates(subset=["REPORT","Driver"], keep='first', inplace=True)
    df_expanded['Driver']=df_expanded['Driver'].apply(lambda x: 'UNKNOWN' if x.strip()=='' else x)
    df_expanded['Date of Birth']=df_expanded['Date of Birth'].apply(lambda x: '' if len(x)<4 else x)
    df_expanded['Age'] = df_expanded['Date of Birth'].apply(lambda x: datetime.now().year - int(x) if x.isdigit() and len(x) == 4 else '')

    #add current date to file name
    file_name= os.path.join(path_ws,'Data_Crashes_WSP_Daily_'+format1+'.csv')    #datetime.now().strftime('%Y%m%d')+'.csv'
    
    #save file in saved_files/ folder
    # file_name=os.path.join('saved_files',file_name)

    insert_dataframe_into_db(df_expanded, path_ws)
    print_dataframe_info(df_expanded)
    df_expanded.to_csv(file_name,index=False)

    logger.info("File saved!: Winston Salem csv")



#output_dir = "/Users/cristianb/Documents/Python/rel8ed/SynapseIQ_staging/storage"
#output_dir = "/home/data"
#run_wsp_crash_scraper(output_dir)