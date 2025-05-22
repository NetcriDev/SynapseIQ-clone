import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))  # Ajusta según nivel
os.chdir(PROJECT_ROOT)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pandas as pd
from src.utils.logger_config import setup_logger
from src.database.kansas_into_db import insert_full_crash_data


#outputdata_dir = "/Users/cristianb/Documents/Python/rel8ed/Data"
#home_dir = "/Users/cristianb/Documents/Python/rel8ed/SynapseIQ_staging"
outputdata_dir = "/home/data"
home_dir="home/SynapseIQ"

logger= setup_logger("Scheduled_execution", outputdata_dir)
# now


def load_latest_kansas_csv(txt_path="/tmp/last_csv_path.txt") -> pd.DataFrame:
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
        df = pd.read_csv(csv_path)
    except Exception as e:
        raise ValueError(f"Failed to read CSV: {e}")

    return df


def kansas_into_db():
    logger.info(">>> kansas: Start insert into db ")

    df = load_latest_kansas_csv(txt_path=os.path.join(outputdata_dir, "kansas", "last_csv_path.txt")) 
    insert_full_crash_data(df, os.path.join(outputdata_dir, "kansas"))

    logger.info(" kansas: Finish insert into db -----|")

kansas_into_db()
