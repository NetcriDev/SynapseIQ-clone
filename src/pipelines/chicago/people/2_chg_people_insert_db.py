# Aqui el codigo que lee el csv llama al a funcion pura e inserta a la base de dtos

# paso 1 : Ir a leer el archivo .txt, ller la primera linea y obtener la ubicacion del archivo csv

# paso 2: Leer el archivo csv usando pandas, y genera el dataFrame

# Paso 3: LLamar al funcion chicago_into_db y pasarle el datFrame

import os
import sys
from dotenv import load_dotenv
import ibm_boto3
from ibm_botocore.client import Config
import pandas as pd
from src.utils.logger_config import setup_logger
from src.database.chicago.chicago_people_into_db import insert_db_full_crashes

# Cargar variables de entorno
load_dotenv()

# Configuración de COS desde variables de entorno
COS_BUCKET = os.getenv("COS_BUCKET")
COS_APIKEY = os.getenv("COS_APIKEY")
COS_RESOURCE_INSTANCE_ID = os.getenv("COS_RESOURCE_INSTANCE_ID")
COS_ENDPOINT = os.getenv("COS_ENDPOINT")
COS_OBJECT_NAME = os.getenv("COS_OBJECT_NAME")  # El nombre del archivo en COS

# Ruta local temporal donde se descargará el CSV
LOCAL_CSV_PATH = "/tmp/people.csv"

# Descargar el archivo CSV desde COS

def descargar_csv_de_cos():
    cos = ibm_boto3.client("s3",
        ibm_api_key_id=COS_APIKEY,
        ibm_service_instance_id=COS_RESOURCE_INSTANCE_ID,
        config=Config(signature_version="oauth"),
        endpoint_url=COS_ENDPOINT
    )
    with open(LOCAL_CSV_PATH, "wb") as f:
        cos.download_fileobj(COS_BUCKET, COS_OBJECT_NAME, f)
    print(f"Archivo descargado de COS a {LOCAL_CSV_PATH}")

descargar_csv_de_cos()

# Logger y rutas
outputdata_dir = "/tmp"  # Usamos /tmp porque ahí estará el CSV descargado
logger = setup_logger("Scheduled_execution", outputdata_dir)


def load_latest_chicago_people_csv(csv_path=LOCAL_CSV_PATH) -> pd.DataFrame:
    """
    Carga el archivo CSV descargado desde COS y lo convierte en DataFrame.
    """
    if not os.path.isfile(csv_path):
        raise FileNotFoundError(f"CSV file not found at path: {csv_path}")
    try:
        df = pd.read_csv(csv_path, sep=";", dtype={"ID": str, "Age": str, "License":str})
    except Exception as e:
        raise ValueError(f"Failed to read CSV: {e}")
    return df


def chicago_people_into_db():
    logger.info(">>> chicago-people: Start insert into db ")
    df = load_latest_chicago_people_csv(csv_path=LOCAL_CSV_PATH)
    insert_db_full_crashes(outputdata_dir) 
    logger.info(" chicago-people: Finish insert into db -----|")

chicago_people_into_db()
