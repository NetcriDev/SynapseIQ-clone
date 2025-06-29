# Aqui el codigo que lee el csv llama al a funcion pura e inserta a la base de dtos

# paso 1 : Ir a leer el archivo .txt, ller la primera linea y obtener la ubicacion del archivo csv

# paso 2: Leer el archivo csv usando pandas, y genera el dataFrame

# Paso 3: LLamar al funcion chicago_into_db y pasarle el datFrame

import os
import sys



PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))  # Ajusta según nivel
os.chdir(PROJECT_ROOT)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pandas as pd
from src.database.chicago.chicago_traffic_into_db import insert_db_full_crashes
from src.utils.logger_config import setup_logger

#outputdata_dir = "/Users/cristianb/Documents/Python/rel8ed/Data"
#home_dir = "/Users/cristianb/Documents/Python/rel8ed/SynapseIQ_staging"
outputdata_dir = "/home/data/chicago/traffic"
#   home_dir="home/SynapseIQ"

logger= setup_logger("Scheduled_execution", outputdata_dir)
# now


def load_latest_chicago_traffic_csv(txt_path="csv_path_traffic.txt") -> pd.DataFrame:
    """
    Reads the path to the most recent CSV from a .txt file and loads it into a DataFrame.

    Args:
        txt_path (str): Path to the file containing the CSV path.

    Returns:
        pd.DataFrame: DataFrame containing the CSV data.

    Raises:
        FileNotFoundError: If the .txt file or CSV file does not exist.
        ValueError: If the file is empty or CSV cannot be read.
    """
    if not os.path.exists(txt_path):
        raise FileNotFoundError(f"Csv File not found: {txt_path}")
    
    with open(txt_path, "r") as f:
        csv_path = f.readline().strip()

    if not csv_path:
        raise ValueError("CSV path file is empty or improperly formatted.")

    if not os.path.isfile(csv_path):
        raise FileNotFoundError(f"CSV file not found at path: {csv_path}")

    try:
        df = pd.read_csv(csv_path, sep=";", dtype={"ID": str, "Age": str, "License":str})
    except Exception as e:
        raise ValueError(f"Failed to read CSV: {e}")

    return df


def chicago_traffic_into_db():
    logger.info(">>> chicago-traffic: Start insert into db ")

    df = load_latest_chicago_traffic_csv(txt_path=os.path.join(outputdata_dir, "csv_path_traffic.txt")) 
    insert_db_full_crashes(os.path.join(outputdata_dir))

    logger.info(" chicago-traffic: Finish insert into db -----|")

chicago_traffic_into_db()
