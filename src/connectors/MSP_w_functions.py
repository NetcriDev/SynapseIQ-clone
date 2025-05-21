import re
import os
import sys
import pdfkit
import requests
from weasyprint import HTML
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from src.utils.logger_config import setup_logger
from src.database.minnesota_into_db import mn_dataframe_to_db



main_script_path = sys.path[0]
logger = setup_logger("Minnesota_execution", main_script_path)

# ::::::::::::::::::::::::::::::: proxies :::::::::::::::::::::::::::::::
def get_proxies():
    username = 'rrel8ed'
    password = 'zFfUPRWH6q'
    country = 'CA'
    entry = f'http://customer-{username}-cc-{country}:{password}@pr.oxylabs.io:7777'
    return {'http': entry, 'https': entry}

def get_headers():
    return {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'accept-language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
        'cache-control': 'max-age=0',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)... Chrome/133.0.0.0 Safari/537.36'
    }

# ::::::::::::::::::::::::::::::: scraping :::::::::::::::::::::::::::::::
def get_crash_links():
    response = requests.get('https://app.dps.mn.gov/MSPMedia2/Current', headers=get_headers(), proxies=get_proxies())
    soup = BeautifulSoup(response.content, 'html.parser')
    main_content = soup.find_all("div", class_="col-md-10 col-xs-8")
    links = ["https://app.dps.mn.gov" + div.find("a").get("href") for div in main_content]
    numbers = [div.find("a").text for div in main_content]
    return numbers, links

def extract_crash_data(url, crash_number):
    response = requests.get(url, headers=get_headers(), proxies=get_proxies())
    soup = BeautifulSoup(response.content, 'html.parser')
    
    text = soup.get_text()
    
    date = re.search(r"Date/Time:\s*(.*)", text)
    Date = date.group(1).strip() if date else "N/A"
    
    incident = re.search(r"Incident type:\s*(.*)", text)
    accident_type = incident.group(1).strip() if incident else "N/A"
    
    icr = case = contact = location = description = ''
    for incident_content in soup.find('div', id='incident-body').find_all('div', class_='row'):
        divs = incident_content.find_all('div')
        for k in range(len(divs)):
            if 'ICR' in divs[k].text:
                icr = divs[k+1].text.strip()
            if 'Case Info' in divs[k].text:
                case = divs[k+1].text.strip()
            if 'Media Contact' in divs[k].text:
                contact = divs[k+1].text.strip()
            if 'Location:' in divs[k].text:
                location = divs[k+2].text.strip()
            if 'Description' in divs[k].text:
                description = divs[k+1].text.strip()

    driver_names, cities, ages = extract_driver_info(soup)
    df_temp = build_dataframe(crash_number, Date, accident_type, icr, case, contact, location, description, driver_names, cities, ages, url)
    
    return df_temp, driver_names, cities, ages

def extract_driver_info(soup):
    driver_names = []
    cities = []
    ages = []
    for driver_section in soup.find_all("div", class_="row person-form"):
        name_tag = driver_section.find_next("div", class_="col-md-12 col-xs-12")
        name = name_tag.get_text(strip=True)

        city_tag = name_tag.find_next("div", class_="col-md-12 col-xs-12").find_next("div", class_="col-md-12 col-xs-12")
        city = city_tag.get_text().strip()
        cities.append(city)

        age_tag = city_tag.find_next("div", class_="col-md-12 col-xs-12")
        if age_tag and "Age:" in age_tag.get_text():
            age = age_tag.get_text().split(":", 1)[1].strip()
            ages.append(age)
        else:
            if "Age:" in name:
                age = name.split(":", 1)[1].strip()
                ages.append(age)
                name = 'N/A'
            else:
                ages.append("N/A")
        driver_names.append(name)
    return driver_names, cities, ages

# ::::::::::::::::::::::::::::::: build dataframe :::::::::::::::::::::::::::::::

def build_dataframe(crash_number, Date, accident_type, icr, case, contact, location, description, driver_names, cities, ages, url):
    df_temp = pd.DataFrame({
        "ID": [crash_number] * len(driver_names),
        "Date": [Date] * len(driver_names),
        "Type": [accident_type] * len(driver_names),
        "ICR": [icr] * len(driver_names),
        "Case Number": [case] * len(driver_names),
        "Contact": [contact] * len(driver_names),
        "Location": [location] * len(driver_names),
        "Description": [description] * len(driver_names),
        "Driver": driver_names,
        "Age": ages,
        "City": cities,
        "URL": [url] * len(driver_names),
    })
    
    # Separar "City, State, Country" -> em City e State com fallback
    split_location = df_temp['City'].str.split(",", expand=True)
    
    df_temp['City'] = split_location[0].str.strip()
    df_temp['State'] = split_location[1].str.strip() if split_location.shape[1] > 1 else "N/A"

    # Caso alguma cidade ou estado venha vazia, preencher com "N/A"
    df_temp['City'] = df_temp['City'].fillna("N/A")
    df_temp['State'] = df_temp['State'].fillna("MN")

    df_temp['Date'] = pd.to_datetime(df_temp['Date'], format='%m/%d/%Y %H:%M', errors='coerce')
    return df_temp

# ::::::::::::::::::::::::::::::: salvar PDF :::::::::::::::::::::::::::::::

def save_as_pdf(url, filename):
    try:
        HTML(url).write_pdf(filename)
        logger.info(f"saved pdf with weasyprint {filename}")
    except:
        try:
            pdfkit.from_url(url, filename)
            logger.info(f"saved pdf with pdfkit {filename}")
        except:
            logger.error(f"could not save pdf {filename}")

# ::::::::::::::::::::::::::::::: main :::::::::::::::::::::::::::::::


def pipeline_minnesota(output_folder: str = None, token_folder: str = None) -> pd.DataFrame:
    """
    Main function to run the Minnesota crash report scraping and save the data to a CSV file.
    Args:
        output_folder (str): Path to the folder where the CSV and pdfs files will be saved. If None, defaults to '/home/data/minnesota'.
        token_folder (str): Path to the folder containing the DataIris token.
    returns:
        pd.DataFrame: DataFrame containing the crash report data.    
    """
    if output_folder is None:
        output_folder = r'/home/data/minnesota'  # Change to your desired output folder <-----------------------
    # Create folder if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)


    crash_numbers, crash_links = get_crash_links()
    df_final = pd.DataFrame()
    
    for i, url in enumerate(crash_links):
        crash_number = crash_numbers[i]
        df_temp, driver_names, cities, ages = extract_crash_data(url, crash_number)
        
        date_today = (datetime.now() - timedelta(1)).date()
        if df_temp['Date'].dt.date.isin([date_today]).any():
            df_final = pd.concat([df_final, df_temp], ignore_index=True)
            
            pdf_filename = os.path.join(output_folder, crash_number + ".pdf")
            save_as_pdf(url, pdf_filename)
            logger.info(f"PDF salvo: {pdf_filename}")
        
        print("Drivers:", driver_names)
        print("City:", cities)
        print("Age:", ages)
        print("--------------------")
    
    file_name = f'Data_Crashes_MSP_{date_today.strftime("%Y%m%d")}.csv'
    csv_path = os.path.join(output_folder, file_name)
    df_final.to_csv(csv_path, index=False)
    logger.info(f"CSV saved in: {csv_path}")

    with open(output_folder + "/last_csv_path.txt", "w") as f:
        f.write(csv_path + "\n")

if __name__ == "__main__":
    pipeline_minnesota()