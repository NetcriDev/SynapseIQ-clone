import psycopg2
#from config.config import get_connection

try:
    # Establecer conexión y cursor
    conexion = psycopg2.connect(
        dbname="crash_records_001",
        user="synapseiq",
        password="SynapseIQ$2025",
        host="localhost",
        port="5432"
    )
    cursor = conexion.cursor()

    # !!!!Ya Implementado!!!
    # 1. Agregar columnas state, city, street  
    # alter_table_sql = """
    # ALTER TABLE passengers
    # ADD COLUMN contact_resolution TEXT,
    # ADD COLUMN state TEXT,
    # ADD COLUMN city TEXT,
    # ADD COLUMN street TEXT;
    # """

    # !!! Ya Implementado!!!
    #2. Agregar name_nearest hope in incident_reports
    # alter_table_sql = """ 
    # ALTER TABLE incident_reports
    # ADD COLUMN name_nearest_hope TEXT
    # """

    # #3. Agregar report_number TEXT in table vehicules
    # alter_table_sql = """ 
    # ALTER TABLE vehicles
    # ADD COLUMN report_number TEXT
    # """

    #!!! Ya Implementado!!!
    #4. Agregar report_number TEXT in table passengers
    # alter_table_sql = """ 
    # ALTER TABLE passengers
    # ADD COLUMN report_number TEXT
    # """

    # !!! Ya Implementado!!!
    # alter_table_sql = """ 
    # ALTER TABLE incident_reports
    # ADD COLUMN is_external  TEXT
    # """

    # !!! Ya Implementado!!!
    # alter_table_sql = """ 
    # ALTER TABLE incident_reports
    # ADD COLUMN website  TEXT
    # """

    # !!! Ya Implementado!!!
    # alter_table_sql = """ 
    # ALTER TABLE incident_reports
    # ADD COLUMN document_location_ibm TEXT
    # """

    # !!! Ya Implementado!!!
    #Agregar sitio web, en lugar de state
    # alter_table_sql = """ 
    # ALTER TABLE passengers
    # ADD COLUMN website TEXT
    # """

    # !!! Ya Implementado!!!
    #Agregar sitio web, en lugar de state
    # alter_table_sql = """ 
    # ALTER TABLE vehicles
    # ADD COLUMN website TEXT
    # """


    # !!! Ya Implementado!!!
    #Agregar address
    # alter_table_sql = """ 
    # ALTER TABLE passengers
    # ADD COLUMN address TEXT
    # """

    # #Agregar address
    # alter_table_sql = """ 
    # ALTER TABLE incident_reports
    # ADD COLUMN address TEXT
    # """

    # #Agregar address
    # alter_table_sql = """ 
    # ALTER TABLE passengers
    # ADD COLUMN insurance_company TEXT,
    # ADD COLUMN hasphone TEXT,
    # ADD COLUMN hasinsurance_details TEXT,
    # ADD COLUMN hasname TEXT,
    # ADD COLUMN over18 TEXT,
    # ADD COLUMN hotlead TEXT;
    # """

    #Agregar website a tablas de chat
    alter_table_sql = """ 
    ALTER TABLE chat_session
    ADD COLUMN website TEXT
    """

    # alter_table_sql = """
    # ALTER TABLE chat_messages
    # ADD COLUMN website TEXT;
    # """


    cursor.execute(alter_table_sql)
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
