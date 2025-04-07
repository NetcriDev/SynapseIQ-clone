import psycopg2
from config.config import get_connection
# Establishing the connection to the database
conexion = get_connection()

# Create a cursor to execute SQL commands
cursor = conexion.cursor()

# Define the SQL statement to add two new columns
alter_table_sql = """
ALTER TABLE incident_reports
ADD COLUMN gender TEXT,
ADD COLUMN nearest_center_d NUMERIC(10,2),
ADD COLUMN nearest_hope_d NUMERIC(10,2);
"""
# Ejecutar la sentencia SQL
cursor.execute(alter_table_sql)

# Confirmar los cambios en la base de datos
conexion.commit()
# Cerrar el cursor y la conexión
cursor.close()
conexion.close()