import os
import sys
import time
import pandas as pd
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from src.utils.logger_config import setup_logger

main_script_path = sys.path[0]
logger = setup_logger("Texas_execution", main_script_path)

def get_project_paths():
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    raw_data_path = os.path.join(project_root, "data", "raw")
    os.makedirs(raw_data_path, exist_ok=True)
    return project_root, raw_data_path

def get_date_ranges(n_days=4):
    today = datetime.now()
    begin_date = (today - timedelta(days=n_days)).strftime("%m/%d/%Y")
    end_date = (today - timedelta(days=1)).strftime("%m/%d/%Y")
    return begin_date, end_date

def setup_driver(download_dir):
    options = Options()
    options.add_argument('--start-maximized')
    options.add_argument('--headless=new') ######### ojo dont show interfaz
    options.add_argument("--no-sandbox")           # Necesario en algunos servidores
    options.add_argument("--disable-dev-shm-usage")# Evita problemas de memoria compartida
    options.add_argument("--disable-gpu")          # Opcional, para evitar errores GPU


    prefs = {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "directory_upgrade": True,
        "safebrowsing.enabled": True
    }
    options.add_experimental_option("prefs", prefs)
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    return driver

def wait_for_export_button(driver):
    def export_enabled(driver):
        try:
            btn = driver.find_element(By.XPATH, '//*[@id="btn-export"]')
            return btn.is_displayed() and btn.is_enabled()
        except:
            return False
    WebDriverWait(driver, 40).until(export_enabled)
    driver.find_element(By.XPATH, '//*[@id="btn-export"]').click()

def wait_for_download_complete(folder, extension=".csv", timeout=30, margin=10):
    deadline = time.time() + timeout
    threshold = time.time() - margin
    while time.time() < deadline:
        if any(f.endswith(".crdownload") for f in os.listdir(folder)):
            time.sleep(1)
            continue
        for f in os.listdir(folder):
            if f.endswith(extension):
                path = os.path.join(folder, f)
                if os.path.getmtime(path) > threshold:
                    return f
        time.sleep(1)
    return None

def rename_downloaded_file(download_dir, old_name, begin_date, end_date, abbreviation="my_list"):
    # Verify that the name contains the abbreviation
    if abbreviation not in old_name:
        logger.info(f"File ignored because it does not contain '{abbreviation}': {old_name}")
        return None
    begin_fmt = begin_date.replace("/", "_")
    end_fmt = end_date.replace("/", "_")
    current_time = datetime.now().strftime("%H%M%S")
    new_name = f"texascrashes_{begin_fmt}_to_{end_fmt}.csv"
    new_path = os.path.join(download_dir, new_name)
    old_path = os.path.join(download_dir, old_name)
    if os.path.exists(new_path):
        os.remove(new_path)
    os.rename(old_path, new_path)
    return new_path

def load_csv_from_raw(path):
    df = pd.read_csv(path, skiprows=10)
    logger.info(df.head())
    return df

def run_scraper(data_dir: str = None, home_dir: str = None):
    if data_dir is None or home_dir is None:
        project_root, download_dir = get_project_paths()
    project_root = home_dir
    download_dir = data_dir
    begin_date, end_date = get_date_ranges()
    driver = setup_driver(download_dir)
    driver.get('https://cris.dot.state.tx.us/public/Query/app/home')

    wait = WebDriverWait(driver, 20)
    wait.until(EC.element_to_be_clickable((By.XPATH, "/html/body/app-root/div[2]/app-homepage/cris-page/div/cris-homepage-card-container/div/div[2]/div[2]/ul/li[1]/a"))).click()
    wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="btn-accept"]'))).click()
    wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="ngb-nav-0-panel"]/app-panel-renderer/app-wizard-type-panel/app-query-type-selector/div[2]/div/div[3]/label'))).click()
    wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="btn-next"]'))).click()
    wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="ngb-nav-1-panel"]/app-panel-renderer/app-wizard-date-panel/app-query-date-selector-panel/app-query-date-selector/div/div/div[3]/label'))).click()

    fecha_inicio = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="queryBeginCrashDate"]')))
    fecha_fin = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="queryEndDate"]')))
    fecha_inicio.clear()
    fecha_fin.clear()
    fecha_inicio.send_keys(begin_date)
    fecha_fin.send_keys(end_date)

    wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="btn-next"]'))).click()
    wait.until(EC.element_to_be_clickable((By.XPATH, "(//app-query-location-selector//label)[5]"))).click()
    wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="btn-view-results"]'))).click()
    wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="views"]/li[4]/a/div[2]'))).click()
    wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="btn-select-columns"]'))).click()

    fields = [
        "$1000 Damage to Any One Person's Property", "Agency", "Case ID", "City", "Contributing Factors",
        "County", "Crash Date", "Crash Severity", "Fatal Crash Flag",
        "Nearest Trauma Center (Nearest Trauma Center)", "Intersecting Street Name",
        "Nearest Trauma Center Distance (Distance to the nearest Trauma Center)", "Street Name",
        "Street Number", "Region", "Lessee/Owner Zip Code", "Driver Zip Code", "Contributing Factor 1",
        "Contributing Factor 2", "Contributing Factor 3", "Vehicle Hit and Run Flag", "VIN",
        "Person Age", "Person Gender", "Person Injury Severity", "Person Non-Suspected Serious Injury Count",
        "Person Number", "Physical Location of An Occupant"
    ]

    for field in fields:
        xpath = f"//label[contains(text(), \"{field}\")]"
        wait.until(EC.element_to_be_clickable((By.XPATH, xpath))).click()

    wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="closeButton"]'))).click()
    wait_for_export_button(driver)
    time.sleep(5)
    driver.quit()

    downloaded = wait_for_download_complete(download_dir, margin=10)
    if downloaded:
        renamed_path = rename_downloaded_file(download_dir, downloaded, begin_date, end_date)
        df = load_csv_from_raw(renamed_path)
        return df
    else:
        logger.warning("No file was downloaded.")
        return None

if __name__ == "__main__":
    run_scraper()