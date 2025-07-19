import requests
import pandas as pd
import psycopg2
from psycopg2 import sql, extras
from datetime import datetime
import os
from dotenv import load_dotenv
import ibm_boto3
from ibm_botocore.client import Config

# === Cargar variables desde archivo .env ===
load_dotenv()

API_URL_PEOPLE = os.getenv('API_URL_PEOPLE')
TABLE_NAME_PEOPLE = os.getenv('TABLE_NAME_PEOPLE')
# Configuración de IBM COS desde variables de entorno
COS_BUCKET = os.getenv('COS_BUCKET')
COS_APIKEY = os.getenv('COS_APIKEY')
COS_RESOURCE_INSTANCE_ID = os.getenv('COS_RESOURCE_INSTANCE_ID')
COS_ENDPOINT = os.getenv('COS_ENDPOINT')


def obtener_datos():
    """
    Obtiene datos desde la API y los convierte en DataFrame normalizado.
    Hace una solicitud GET
    Extrae y transforma los campos necesarios
    Normaliza las columnas a minúsculas
    Convierte crash_date a tipo datetime    """
    
    try:
        response = requests.get(API_URL_PEOPLE)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"Error al obtener datos de la API: {e}")
        return pd.DataFrame()

    person_data = [
        {
            'crash_record_id': item.get('crash_record_id'),
            'person_id': item.get('person_id'),
            'vehicle_id': item.get('vehicle_id'),
            'crash_date': item.get('crash_date'),
            'city': item.get('city'),
            'state': item.get('state'),
            'zipcode': item.get('zipcode'),
            'sex': item.get('sex'),
            'age': item.get('age'),
            'drivers_license_state': item.get('drivers_license_state'),
            'safety_equipment': item.get('safety_equipment'),
            'airbag_deployed': item.get('airbag_deployed'),
            'ejection': item.get('ejection'),
            'injury_classification': item.get('injury_classification'),
            'driver_action': item.get('driver_action'),
            'driver_vision': item.get('driver_vision'),
            'physical_condition': item.get('physical_condition'),
            'bac_result': item.get('bac_result'),
            'bac_result_value': item.get('bac_result_value'),
            'unit_type': item.get('unit_type'),
            'person_type': item.get('person_type'),
            'person_num': item.get('person_num'),
            'injury_type': item.get('injury_type'),
            'hospital': item.get('hospital'),
            'ems_run_no': item.get('ems_run_no'),
            'ems_agency': item.get('ems_agency'),
            'ems_response_time': item.get('ems_response_time'),
            'ems_transport_time': item.get('ems_transport_time'),
            'ems_hospital_time': item.get('ems_hospital_time'),
        }
        for item in data
        if item.get('crash_record_id') and item.get('person_id')
    ]

    df = pd.DataFrame(person_data)
    df.columns = df.columns.str.lower()
    df['crash_date'] = pd.to_datetime(df['crash_date'], errors='coerce')
    return df

def guardar_csv(df, path, fecha):
    """
    Guarda el DataFrame en un archivo .csv con nombre basado en la fecha actual.
    Crea el directorio si no existe
    Define nombre y ruta del archivo
    Exporta usando df.to_csv    """

    try:
        os.makedirs(path, exist_ok=True)
        nombre = f"chicago_reportCrash_people_{fecha.strftime('%Y_%m_%d')}.csv"
        ruta = os.path.join(path, nombre)
        df.to_csv(ruta, index=False, sep=';', encoding='utf-8')
        print(f"Datos exportados a {ruta}")
        return ruta
    except Exception as e:
        print(f"Error al guardar CSV: {e}")
        return None

def subir_a_cos(ruta_archivo, nombre_objeto):
    try:
        print("Intentando subir a COS...")
        cos = ibm_boto3.client("s3",
            ibm_api_key_id=COS_APIKEY,
            ibm_service_instance_id=COS_RESOURCE_INSTANCE_ID,
            config=Config(signature_version="oauth"),
            endpoint_url=COS_ENDPOINT
        )
        with open(ruta_archivo, "rb") as archivo:
            cos.upload_fileobj(archivo, COS_BUCKET, nombre_objeto)
        print(f"Archivo subido a COS: {nombre_objeto}")
    except Exception as e:
        print(f"Problemas al subir a COS: {e}")

def pipeline_chicago_people(path: str):
    """Ejecuta el flujo principal: descarga de datos, inserción en la base, y guardado como CSV si hay nuevos registros.
    Llama a obtener_datos
    Si hay datos, inserta en la base
    Si se insertan nuevos, exporta a CSV
    Sirve para ejecutar el proceso completo de ETL (extracción, transformación, carga).."""

    print("Obteniendo todos los datos disponibles de la API...")
    df = obtener_datos()
    if not df.empty:
        # inserted = insert_to_database(df)
        ruta_csv = guardar_csv(df, path, datetime.now())
        if ruta_csv:
            ruta_txt = os.path.join(path, 'csv_path_people.txt')
            with open(ruta_txt, 'w') as f:
                f.write(ruta_csv + '\n')
                print("Ruta de csv guardado en text.")
            # Subir a COS
            nombre_objeto = os.path.basename(ruta_csv)
            subir_a_cos(ruta_csv, nombre_objeto)
        else:
            print("No hay datos nuevos para guardar en CSV.")
    else:
        print("No se encontraron datos en la API o ocurrió un error.")

# Punto de entrada si se ejecuta como script
if __name__ == "__main__":
    # Usar la ruta actual del proyecto
    current_dir = os.path.dirname(os.path.abspath(__file__))
    storage_path = os.path.join(current_dir, "storage")
    pipeline_chicago_people(path=storage_path)
