import requests
import pandas as pd
import psycopg2
from psycopg2 import sql, extras
from datetime import datetime
import os
from dotenv import load_dotenv

# === Cargar variables desde archivo .env ===
load_dotenv()


API_URL_CRASHES_TRAFFIC = os.getenv('API_URL_CRASHES_TRAFFIC')
TABLE_NAME_CRASHES_TRAFFIC = os.getenv('TABLE_NAME_CRASHES_TRAFFIC')
# CSV_BASE_PATH = os.getenv('CSV_BASE_PATH')

def obtener_datos():
    """
    Consulta la API de accidentes y transforma la respuesta JSON en un DataFrame.
    Realiza un GET a la API
    Convierte el JSON a DataFrame
    Filtra columnas no válidas como identificadores SQL
    Convierte fechas (crash_date, date_police_notified)
    Transforma la columna location a WKT POINT (lon lat) si está disponible
    Esit se realiza para estructurar correctamente los datos antes de insertarlos o exportarlos.   """

    try:
        response = requests.get(API_URL_CRASHES_TRAFFIC)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"Error al obtener datos de la API: {e}")
        return pd.DataFrame()
    
    traffic_data = [
        {
            'crash_record_id': item.get('crash_record_id'),
            'crash_date': item.get('crash_date'),
            'posted_speed_limit': item.get('posted_speed_limit'),
            'traffic_control_device': item.get('traffic_control_device'),
            'device_condition': item.get('device_condition'),
            'weather_condition': item.get('weather_condition'),
            'lighting_condition': item.get('lighting_condition'),
            'first_crash_type': item.get('first_crash_type'),
            'trafficway_type': item.get('trafficway_type'),
            'alignment': item.get('alignment'),
            'roadway_surface_cond': item.get('roadway_surface_cond'),
            'road_defect': item.get('road_defect'),
            'crash_type': item.get('crash_type'),
            'intersection_related_i': item.get('intersection_related_i'),
            'hit_and_run_i': item.get('hit_and_run_i'),
            'damage': item.get('damage'),
            'prim_contributory_cause': item.get('prim_contributory_cause'),
            'sec_contributory_cause': item.get('sec_contributory_cause'),
            'street_no': item.get('street_no'),
            'street_direction': item.get('street_direction'),
            'street_name': item.get('street_name'),
            'beat_of_occurrence': item.get('beat_of_occurrence'),
            'photos_taken_i': item.get('photos_taken_i'),
            'statements_taken_i': item.get('statements_taken_i'),
            'dooring_i': item.get('dooring_i'),
            'work_zone_i': item.get('work_zone_i'),
            'work_zone_type': item.get('work_zone_type'),
            'workers_present_i': item.get('workers_present_i'),
            'num_units': item.get('num_units'),
            'most_severe_injury': item.get('most_severe_injury'),
            'injuries_total': item.get('injuries_total'),
            'injuries_fatal': item.get('injuries_fatal'),
            'injuries_incapacitating': item.get('injuries_incapacitating'),
            'injuries_non_incapacitating': item.get('injuries_non_incapacitating'),
            'injuries_reported_not_evident': item.get('injuries_reported_not_evident'),
            'injuries_no_indication': item.get('injuries_no_indication'),
            'injuries_unknown': item.get('injuries_unknown'),
            'crash_hour': item.get('crash_hour'),
            'crash_day_of_week': item.get('crash_day_of_week'),
            'crash_month': item.get('crash_month'),
            'latitude': item.get('latitude'),
            'longitude': item.get('longitude'),
            'location': item.get('location'),
            'report_type': item.get('report_type'),
            'date_police_notified': item.get('date_police_notified')
        }
        for item in data
            if item.get('crash_record_id')
    ]
    
    df = pd.DataFrame(traffic_data)
    df.columns = df.columns.str.lower()
    df['crash_date'] = pd.to_datetime(df['crash_date'], errors='coerce')
    return df



def guardar_csv(df, path, fecha):
    """
    Guarda el DataFrame como un archivo .csv con nombre basado en la fecha actual.
        Crea el directorio si no existe
        Genera el nombre del archivo con prefijo chicago_reportCrash_traffic
        Exporta como CSV usando separador ; y codificación UTF-8 (Sirve para separalos por columnas el ;)
        Asi mantenemos una copia histórica local de los datos procesados. """
    try:
        os.makedirs(path, exist_ok=True)
        nombre = f"chicago_reportCrash_traffic_{fecha.strftime('%Y_%m_%d')}.csv"
        ruta = os.path.join(path, nombre)
        df.to_csv(ruta, index=False, sep=';', encoding='utf-8')
        print(f"Datos exportados a {ruta}")
        return ruta
    except Exception as e:
        print(f"Error al guardar CSV: {e}")
        return None



def pipeline_chicago_traffic(path: str):
    """Ejecuta el flujo principal: descarga de datos, inserción en la base, y guardado como CSV si hay nuevos registros.
    Consulta a la API de accidentes de tráfico
    Si hay datos, inserta en la base
    Si se insertan nuevos, exporta a CSV
    Sirve para ejecutar el proceso completo de ETL (extracción, transformación, carga).."""

    print("Obteniendo todos los datos disponibles de la API...")
    df = obtener_datos()
    if not df.empty:
        ruta_csv = guardar_csv(df, path, datetime.now())
        if ruta_csv:
            ruta_txt = os.path.join(path, "csv_path_traffic.txt")
            with open(ruta_txt, 'w') as f:
                f.write(ruta_csv + '\n')
                print("Ruta de csv guardado en text.")
        else:
            print("No hay datos nuevos para guardar en CSV.")
    else:
        print("No se encontraron datos en la API o ocurrió un error.")

if __name__ == "__main__":
    pipeline_chicago_traffic(path="/home/data/chicago/traffic")
