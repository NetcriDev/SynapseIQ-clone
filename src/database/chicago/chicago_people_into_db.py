# Solo agregar funcion que va tomar el dataframe como argumento e inserta en la base de datos (va la funcion pura)
import pandas as pd
import os
from psycopg2 import sql, extras
from dotenv import load_dotenv

from config.config import get_connection
load_dotenv()

# --- Configuración dinámica desde entorno 
# Esta es la configuración de la base de datos de Chicago Crashes People.
conn = get_connection()
cur = conn.cursor()
# Tipos específicos por columna en la tabla
# Esta es la configuración de los tipos de datos de las columnas de la tabla de Chicago Crashes People. """

SQL_TYPES = {
    'crash_date': 'TIMESTAMP',
    'age': 'INTEGER',
    'injuries_fatal': 'INTEGER',
    'injuries_incapacitating': 'INTEGER',
    'injuries_non_incapacitating': 'INTEGER',
    'injuries_no_indication': 'INTEGER',
    'injuries_reported_not_evident': 'INTEGER',
    'injuries_total': 'INTEGER',
    'injuries_unknown': 'INTEGER',
}

def insert_all_to_database(df, table_name):
    """
    Inserta todos los registros del DataFrame en la base de datos.
    Crea la tabla si no existe.
    """
    if df.empty:
        print("No hay datos para insertar.")
        return 0

    df.columns = df.columns.str.lower()
    columns = df.columns.tolist()

    fields_list = []
    for col in columns:
        col_type = SQL_TYPES.get(col, 'TEXT')
        fields_list.append(sql.SQL(f"{col} {col_type}"))

    create_table_query = sql.SQL(
        "CREATE TABLE IF NOT EXISTS {table} ({fields})"
    ).format(
        table=sql.Identifier(table_name),
        fields=sql.SQL(', ').join(fields_list)
    )

    inserted_count = 0
    try:
        with conn.cursor() as cur:
            cur.execute(create_table_query)
            conn.commit()

            insert_query = sql.SQL(
                """
                INSERT INTO {table} ({fields}) VALUES ({placeholders})
                """
            ).format(
                table=sql.Identifier(table_name),
                fields=sql.SQL(', ').join(map(sql.Identifier, columns)),
                placeholders=sql.SQL(', ').join(sql.Placeholder() * len(columns))
            )

            values = [
                tuple(None if pd.isna(val) else val for val in row)
                for row in df.itertuples(index=False, name=None)
            ]

            extras.execute_batch(cur, insert_query, values)
            inserted_count = len(values)
            conn.commit()

        print(f"Se insertaron {inserted_count} registros en la base de datos.")
        return inserted_count

    except Exception as e:
        print(f"Error al insertar en la base de datos: {e}")
        return 0

def insert_db_full_crashes(path_or_csv=None):
    """
    Si path_or_csv es un archivo CSV, lo carga directamente. Si es un directorio, busca csv_path_people.txt y carga el CSV desde ahí.
    """
    if path_or_csv is None:
        raise ValueError("Se requiere la ruta del archivo CSV o del directorio.")
    if os.path.isfile(path_or_csv):
        # Es un archivo CSV directo
        df = pd.read_csv(path_or_csv, sep=';')
        insert_all_to_database(df, "chicago_crashes_people")
    else:
        # Es un directorio, busca csv_path_people.txt
        ruta_txt = os.path.join(path_or_csv, "csv_path_people.txt")
        with open(ruta_txt, "r", encoding="utf-8") as f:
            primera_linea = f.readline().strip()
            df = pd.read_csv(primera_linea, sep=';')
            insert_all_to_database(df, "chicago_crashes_people")

if __name__ == "__main__":
    insert_db_full_crashes("/tmp/people.csv")