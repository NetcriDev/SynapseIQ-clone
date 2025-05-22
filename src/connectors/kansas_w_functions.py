import os
import sys
import requests
import pandas as pd
import re
import os
import pdfkit
from weasyprint import HTML
from io import BytesIO
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from src.utils.logger_config import setup_logger

main_script_path = sys.path[0]
logger = setup_logger("Kansas_execution", main_script_path)

# ::::::::::::::::::::::::::::::::::::::::: Path :::::::::::::::::::::::::::::::::::::::::
#DIRETORIO_BASE = r"D:\GitHub Rel8ed\WebScraping\SynapselQ\Kansas website"

# ::::::::::::::::::::::::::::::::::::::::: proxies :::::::::::::::::::::::::::::::::::::::::
USERNAME = 'rrel8ed' # Insira seu usuário
PASSWORD = 'zFfUPRWH6q' # Insira sua senha
COUNTRY = 'US'  # Insira o país
BASE_SEARCH_URL = 'https://www.kansas.gov/khp-crashlogs/search.do'
BASE_DETAIL_URL = 'https://www.kansas.gov/khp-crashlogs/search/viewDetail/2025-'

# ::::::::::::::::::::::::::::::::::::::::: functios for aquisition and parsing :::::::::::::::::::::::::::::::::::::::::

def setup_proxies(username, password, country_code):
    entry = (f'http://customer-{username}-cc-{country_code}:{password}@pr.oxylabs.io:7777')
    proxies = {
        'http': entry,
        'https': entry,
    }
    return proxies

def get_search_headers():
    return {
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
    }

def get_detail_headers():
    return {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'en-US,en;q=0.9,pt;q=0.8',
        'Cache-Control': 'max-age=0',
        'Connection': 'keep-alive',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Origin': 'https://www.kansas.gov',
        'Referer': 'https://www.kansas.gov/khp-crashlogs/search/index',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-User': '?1',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
    }

def fetch_page_content(url, method='get', headers=None, data=None, proxies=None):
    try:
        if method.lower() == 'post':
            response = requests.post(url, headers=headers, data=data, proxies=proxies, timeout=30)
        else:
            response = requests.get(url, headers=headers, proxies=proxies, timeout=30)
        response.raise_for_status()
        return BeautifulSoup(response.content, 'html.parser')
    except requests.exceptions.RequestException as e:
        print(f"Erro ao buscar {url}: {e}")
        return None

# ::::::::::::::::::::::::::::::::::::::::: functins for extracting data :::::::::::::::::::::::::::::::::::::::::

def extract_crash_links_and_ids(soup):
    crash_links = []
    crash_ids = []

    container_div = soup.find("div", class_="col-12") 
    if container_div:
        rows = container_div.find_all("div", class_="row")
        for row in rows:
            link_tag = row.find("a")
            if link_tag and link_tag.get("href"):
                full_link = "https://www.kansas.gov" + link_tag.get("href")
                crash_links.append(full_link)
                try:
                    crash_id = full_link.split("-")[-1]
                    crash_ids.append(crash_id)
                except IndexError:
                    print(f"Não foi possível extrair o ID do link: {full_link}")
                    crash_ids.append(None) 
    return crash_links, crash_ids

# ::::::::::::::::::::::::::::::::::::::::: functins for extracting data from details screen :::::::::::::::::::::::::::::::::::::::::

def extract_basic_crash_info(soup):
    text_content = soup.get_text()
    date_match = re.search(r"Date:\s*(.*)", text_content)
    crash_date = date_match.group(1).strip() if date_match else "N/A"
    time_match = re.search(r"Time:\s*(.*)", text_content)
    crash_time = time_match.group(1).strip() if time_match else "N/A"
    type_match = re.search(r"Type:\s*(.*)", text_content)
    accident_type = type_match.group(1).strip() if type_match else "N/A"
    return crash_date, crash_time, accident_type

def extract_persons_data(soup):
    names, cities, states, ages, genders, roles, driver_vehicle_numbers = [], [], [], [], [], [], []
    for section in soup.find_all("div", class_="page-header1"): # motorist and occupant sections
        section_text = section.get_text()
        current_role = "N/A"
        driver_vehicle_num = '' 

        if "Driver of Vehicle" in section_text:
            current_role = "Driver"
            try:
                # original: driver_number=re.findall('\d+',section_text)[0]
                driver_vehicle_num = re.findall(r'\d+', section_text)[0]
            except IndexError:
                driver_vehicle_num = '' 
        elif "Occupant" in section_text:
            current_role = "Occupant"

        if current_role != "N/A":
            roles.append(current_role)
            driver_vehicle_numbers.append(driver_vehicle_num)
            
            name_tag = section.find_next("p")
            try:
                names.append(name_tag.get_text().split(":", 1)[1].strip() if name_tag and "Name:" in name_tag.get_text() else "N/A")
            except: names.append("N/A")

            city_tag = name_tag.find_next("p") if name_tag else None
            try:
                cities.append(city_tag.get_text().split(":", 1)[1].strip() if city_tag and "City:" in city_tag.get_text() else "N/A")
            except: cities.append("N/A")

            state_tag = city_tag.find_next("p") if city_tag else None
            try:
                states.append(state_tag.get_text().split(":", 1)[1].strip() if state_tag and "State:" in state_tag.get_text() else "N/A")
            except: states.append("N/A")
            
            age_tag = state_tag.find_next("p").find_next("p").find_next("p") if state_tag else None
            try:
                ages.append(age_tag.get_text().split(":", 1)[1].strip() if age_tag and "Age:" in age_tag.get_text() else "N/A")
            except: ages.append("N/A")
            
            gender_tag = age_tag.find_next("p") if age_tag else None
            try:
                gender_text = gender_tag.get_text().split(":", 1)[1].strip() if gender_tag and "Sex:" in gender_tag.get_text() else "N/A"
                genders.append(gender_text[0] if gender_text != "N/A" and gender_text else "N/A")
            except: genders.append("N/A")
            
    return names, cities, states, ages, genders, roles, driver_vehicle_numbers

def extract_vehicles_data(soup):
    """Extrai dados dos veículos e a narrativa do acidente, fiel à lógica original."""
    vehicle_insurance_map = {} 
    vehicle_license_map = {} 
    
    single_crash_narrative_for_accident = '' 

    for section_div in soup.find_all("div", class_="col-12"):
        if "Vehicle" in section_div.get_text():
            
            vehicle_number_str = ''
            h2_tag = section_div.find('h2')
            if h2_tag:
                 match_vn = re.findall(r'\d+', h2_tag.get_text())
                 if match_vn:
                     vehicle_number_str = match_vn[0]

            for p_tag in section_div.find_all("p"):
                if "Insurance Company:" in p_tag.get_text():
                    parts = p_tag.get_text().split(":", 1)
                    value_str = parts[1].strip() if len(parts) > 1 else ""
            
                    if vehicle_number_str:
                         vehicle_insurance_map[vehicle_number_str] = value_str if value_str else "N/A"
                    break 
            
            for p_tag in section_div.find_all("p"):
                if "License:" in p_tag.get_text():
                    parts = p_tag.get_text().split(":", 1)
                    value_str = parts[1].strip() if len(parts) > 1 else ""
                    if vehicle_number_str:
                        vehicle_license_map[vehicle_number_str] = value_str if value_str else "N/A"
                    break
            
            for p_tag in section_div.find_all("p"):
                if "Crash Narrative:" in p_tag.get_text():
                    parts = p_tag.get_text().split(":", 1)
                    if len(parts) > 1:
                        single_crash_narrative_for_accident = parts[1].strip() 
                    else:
                        single_crash_narrative_for_accident = "" 
            
            if vehicle_number_str:
                if vehicle_number_str not in vehicle_insurance_map:
                    vehicle_insurance_map[vehicle_number_str] = "N/A"
                if vehicle_number_str not in vehicle_license_map:
                    vehicle_license_map[vehicle_number_str] = "N/A"
                    
    return vehicle_insurance_map, vehicle_license_map, single_crash_narrative_for_accident


def link_person_to_vehicle_details(driver_vehicle_numbers,
                                   vehicle_insurance_map, 
                                   vehicle_license_map, 
                                   single_crash_narrative_for_accident,
                                   num_persons):
    person_licenses = []
    person_insurances = []
    person_narratives = [single_crash_narrative_for_accident] * num_persons

    for i in range(num_persons):
        vehicle_id_for_this_person = driver_vehicle_numbers[i]

        if not vehicle_id_for_this_person:
            person_licenses.append('')
            person_insurances.append('')
        else: 
            person_licenses.append(vehicle_license_map.get(vehicle_id_for_this_person, ''))
            person_insurances.append(vehicle_insurance_map.get(vehicle_id_for_this_person, '')) 
            
    return person_licenses, person_insurances, person_narratives

#::::::::::::::::::::::::::::::::::::::::: pdf download :::::::::::::::::::::::::::::::::::::::::

def download_crash_report_pdf(crash_id, detail_url, outdata_folder):
    output_pdf_filename = f"{crash_id}.pdf"
    full_path = os.path.join(outdata_folder, output_pdf_filename)
    

    try:
        HTML(detail_url).write_pdf(full_path)
        logger.info(f"saved pdf with weasyprint {full_path}")
    except:
        try:
            pdfkit.from_url(detail_url, full_path)
            logger.info(f"saved pdf with pdfkit {full_path}")
        except:
            logger.error(f"could not save pdf {full_path}")


# ::::::::::::::::::::::::::::::::::::::::: processing and dataframe :::::::::::::::::::::::::::::::::::::::::

def process_single_crash(crash_id, crash_link, detail_url, proxies, outdata_folder):
    print(f"Processando acidente ID: {crash_id}...")
    soup_detail = fetch_page_content(detail_url, headers=get_detail_headers(), proxies=proxies)
    if not soup_detail:
        print(f"Não foi possível obter detalhes para o acidente {crash_id}.")
        return None

    crash_date, crash_time, accident_type = extract_basic_crash_info(soup_detail)

    (person_names, person_cities, person_states, person_ages, 
     person_genders, person_roles, driver_vehicle_numbers) = extract_persons_data(soup_detail)
    
    vehicle_insurance_map, vehicle_license_map, single_narrative_str_for_accident = extract_vehicles_data(soup_detail)
    
    num_persons = len(person_names) 
    if num_persons == 0 :
        print(f"Nenhuma pessoa encontrada para o acidente {crash_id}. Apenas dados básicos do acidente serão registrados.")
        person_licenses, person_insurances, person_narratives = [], [], []
        if single_narrative_str_for_accident and num_persons > 0:
             person_narratives = [single_narrative_str_for_accident] * num_persons


    else: # num_persons > 0
        person_licenses, person_insurances, person_narratives = link_person_to_vehicle_details(
            driver_vehicle_numbers, vehicle_insurance_map, vehicle_license_map, single_narrative_str_for_accident, num_persons
        )
    
    download_crash_report_pdf(crash_id, detail_url, outdata_folder)

    return {
        "id": crash_id, # Equivalente a `crash_number` sendo uma lista de um elemento
        "date": crash_date, # Equivalente a `date_list` sendo uma lista de um elemento
        "time": crash_time, # Equivalente a `time_list`
        "type": accident_type, # Equivalente a `crash_type`
        "url_link": crash_link, # Equivalente a `crash_link` sendo uma lista de um elemento
        
        # Estas são as listas de dados por pessoa PARA ESTE ACIDENTE
        "person_names": person_names, # Equiv. a `driver_names` que ia para `final_driver_list`
        "person_ages": person_ages,   # Equiv. a `Age` que ia para `final_ages`
        "person_genders": person_genders,
        "person_licenses": person_licenses, # Equiv. a `license_list` que ia para `final_license_list`
        "person_insurances": person_insurances,
        "person_states": person_states,
        "person_cities": person_cities,
        "person_roles": person_roles,
        "person_narratives": person_narratives # Equiv. a `crash_narratives` (plural) que ia para `final_crash_narratives`
    }


def normalize_dataframe(df_aggregated_data): # df_aggregated_data is created from all_crashes_data

    rename_map = {
        "id": "ID", "date": "Date", "time": "Time", "type": "Type", "url_link": "URL",
        "person_names": "Driver", "person_ages": "Age", "person_genders": "Gender",
        "person_licenses": "License", "person_insurances": "Insurance",
        "person_states": "State", "person_cities": "City", "person_roles": "Role",
        "person_narratives": "Crash Narrative"
    }
    df_renamed = df_aggregated_data.rename(columns=rename_map)
    
    cols_to_explode_final_names = ["Driver", "Age", "Gender", "License", "Insurance", "State", "City", "Role", "Crash Narrative"]

    # Verificar se as colunas a explodir existem
    actual_cols_to_explode = [col for col in cols_to_explode_final_names if col in df_renamed.columns]
    if not actual_cols_to_explode:
        print("Nenhuma coluna para explodir foi encontrada no DataFrame renomeado.")
        df_expanded = df_renamed
    else:
        df_expanded = df_renamed.explode(actual_cols_to_explode, ignore_index=True)

    # ::::::::::::::::::::::::::::::::::::::::: put driver info into occupants :::::::::::::::::::::::::::::::::::::::::
    def assign_driver_info_original_logic(group):
        driver_license_val = None
        driver_insurance_val = None
    
        new_licenses = group['License'].copy()
        new_insurances = group['Insurance'].copy()

        for idx in group.index:
            role = group.loc[idx, 'Role']
            
            if role == 'Driver':
                driver_license_val = group.loc[idx, 'License'] 
                driver_insurance_val = group.loc[idx, 'Insurance']
            elif role == 'Occupant':
                new_licenses.loc[idx] = driver_license_val
                new_insurances.loc[idx] = driver_insurance_val
        
        group['License'] = new_licenses
        group['Insurance'] = new_insurances
        return group

    if not df_expanded.empty and 'ID' in df_expanded.columns:
        df_expanded = df_expanded.groupby('ID', group_keys=False, sort=False).apply(assign_driver_info_original_logic)
    else:
        if df_expanded.empty:
            print("DataFrame expandido está vazio, pulando atribuição de motorista.")
        else: # Não tem ID
             print("DataFrame expandido não possui coluna 'ID', pulando atribuição de motorista.")
        
    return df_expanded

# ::::::::::::::::::::::::::::::::::::::::: save csv :::::::::::::::::::::::::::::::::::::::::
def save_to_csv(df, desired_date_for_filename, outdata_folder):
    if df.empty:
        print("DataFrame is empty.")
        return
    
    file_name = f'Data_Crashes_Kansas_{desired_date_for_filename.strftime("%Y%m%d")}.csv'
    full_path = os.path.join(outdata_folder, file_name)
    
    df.to_csv(full_path, index=False)
    return full_path

# ::::::::::::::::::::::::::::::::::::::::: main function :::::::::::::::::::::::::::::::::::::::::

def pipeline_kansas(outdata_folder: str = "/home/data/kansas"):
    """
    Main function to run the Kansas crash report scraping and save the data to a CSV file.
    Args:
        outdata_folder (str): Path to the folder where the CSV and pdfs files will be saved. If None, defaults to '/home/data/kansas'.
    Returns:
        None
    """
    os.makedirs(outdata_folder, exist_ok=True)

    proxies = setup_proxies(USERNAME, PASSWORD, COUNTRY)
    all_processed_crashes_data = [] 
    
    latest_date_with_data = None # name CSV file

    # Loop to search for accidents for the last 2 days
    for days_ago in range(1, 3): 
        desired_date_for_loop = datetime.now() - timedelta(days=days_ago)
        formatted_date_for_search = desired_date_for_loop.strftime('%m/%d/%Y')
        print(f"\nSearching leads for: {formatted_date_for_search}")

        search_payload = {
            'accidentDate': formatted_date_for_search,
            'injuryType': '',
            'county': '',
            'submit': 'Search',
        }
        
        soup_search_results = fetch_page_content(
            BASE_SEARCH_URL, 
            method='post', 
            headers=get_search_headers(), 
            data=search_payload, 
            proxies=proxies
        )

        if not soup_search_results:
            print(f"Not able to obtain results for {formatted_date_for_search}.")
            continue

        crash_links_from_search, crash_ids_from_search = extract_crash_links_and_ids(soup_search_results)
        
        if not crash_ids_from_search:
            print(f"No lead found for {formatted_date_for_search}.")
            continue
            
        print(f"Found {len(crash_ids_from_search)} leads to {formatted_date_for_search}.")

        found_data_for_this_date = False
        for i in range(len(crash_ids_from_search)):
            current_crash_id = crash_ids_from_search[i]
            current_crash_link = crash_links_from_search[i] 
            
            if current_crash_id is None:
                print(f"invalid ID for{current_crash_link}, skipping.")
                continue

            detail_page_url = f"{BASE_DETAIL_URL}{current_crash_id}"
            
            # Retorna um dicionário com todos os dados extraídos para UM acidente
            single_crash_processed_data = process_single_crash(current_crash_id, current_crash_link, detail_page_url, proxies, outdata_folder)
            
            if single_crash_processed_data: # Se o processamento foi bem-sucedido
                all_processed_crashes_data.append(single_crash_processed_data)
                found_data_for_this_date = True
        
        if found_data_for_this_date:
            latest_date_with_data = desired_date_for_loop # Atualiza para a última data que teve dados


    if not all_processed_crashes_data:
        print("No data found on estimated period.")
        return

    # Criar DataFrame com todos os dados coletados de todos os dias
    df_aggregated = pd.DataFrame(all_processed_crashes_data)
    
    if df_aggregated.empty:
        print("DataFrame is empty.")
        return

    # Normalizar o DataFrame (explodir listas, atribuir info do motorista, etc.)
    df_final_normalized = normalize_dataframe(df_aggregated.copy()) # Usar .copy()
    
    csv_full_path = ""
    if latest_date_with_data:
        csv_full_path = save_to_csv(df_final_normalized, latest_date_with_data, outdata_folder)
    elif not df_final_normalized.empty: # Fallback se latest_date_with_data não foi setado mas temos dados
        print("latest_date_with_data not defined, using last day range.")
        last_day_in_range = datetime.now() - timedelta(days=range(1,3)[-1]) # Ex: se range(1,3), usa dia 2
        csv_full_path = save_to_csv(df_final_normalized, last_day_in_range, outdata_folder)
    else:
        print("No data to save.")


    with open(outdata_folder + "/last_csv_path.txt", "w") as f:
        f.write(csv_full_path + "\n")

if __name__ == "__main__":
    pipeline_kansas()