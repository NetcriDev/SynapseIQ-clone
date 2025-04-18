import psycopg2
from config.config import get_connection

try:
    # Establecer conexión y cursor
    conexion = get_connection()
    cursor = conexion.cursor()

    # 1. Agregar columnas state, city, street
    alter_table_sql = """
    ALTER TABLE passengers
    ADD COLUMN contact_resolution TEXT,
    ADD COLUMN state TEXT,
    ADD COLUMN city TEXT,
    ADD COLUMN street TEXT;

    """
    cursor.execute(alter_table_sql)

    # 2. Agregar columna adicional opcional (descomenta si se requiere)
    # alter_table_sql_p = """
    # ALTER TABLE passengers
    # ADD COLUMN number_occupant INTEGER;
    # """
    # cursor.execute(alter_table_sql_p)

    # Confirmar cambios
    conexion.commit()

except Exception as e:
    print("Error ejecutando ALTER TABLE:", e)
    if conexion:
        conexion.rollback()
finally:
    # Cierre seguro de recursos
    if cursor:
        cursor.close()
    if conexion:
        conexion.close()
