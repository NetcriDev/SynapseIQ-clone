import psycopg2
from typing import Optional
from src.services.api_geocode_distance import HopeCenterDistancer

def get_connection():
    """
    Retorna una conexión activa a la base de datos crash_records_001.
    """
    return psycopg2.connect(
        dbname="crash_records_001",
        user="synapseiq",
        password="SynapseIQ$2025",
        host="localhost",
        port="5433"
    )

def update_incident_nearest_hope(
    conn: psycopg2.extensions.connection,
    api_distance: 'HopeCenterDistancer'
) -> None:
    """
    Busca los 150 incidentes más recientes (sin importar si ya tienen nearest_hope)
    y actualiza los campos name_nearest_hope y nearest_hope_d con el centro más cercano.

    Args:
        conn: Conexión activa a la base de datos.
        api_distance: Instancia de HopeCenterDistancer con método .find_nearest_center(...)
    """
    try:
        with conn.cursor() as cur:
            # 1. Obtener los 150 incidentes más recientes que NO provengan de cris.dot.state.tx.us
            cur.execute("""
                SELECT id, city, state, street
                FROM incident_reports
                WHERE source_url NOT ILIKE %s
                ORDER BY generation_date DESC
                LIMIT 150
            """, ("%https://cris.dot.state.tx.us/public/Query/app/home%",))
            
            incidents = cur.fetchall()
            print(f"Found {len(incidents)} incidents to process.")

            for incident in incidents:
                incident_id, city, state, street = incident

                if not street and not city and not state:
                    print(f"Skipping incident ID {incident_id} due to incomplete address.")
                    continue

                try:
                    result = api_distance.find_nearest_center(
                        country="USA",
                        state=state,
                        city=city,
                        street=street,
                        address=""
                    )
                    if not result:
                        print(f"No nearest center found for incident ID {incident_id}")
                        continue

                    center_name, distance = result
                    print(f"Updating incident {incident_id} => {center_name}, {distance:.2f} miles")

                    cur.execute("""
                        UPDATE incident_reports
                        SET name_nearest_hope = %s,
                            nearest_hope_d = %s
                        WHERE id = %s
                    """, (center_name, distance, incident_id))

                except Exception as e:
                    print(f"Error processing incident ID {incident_id}: {e}")

            conn.commit()
            print("Update completed and committed.")

    except Exception as e:
        conn.rollback()
        print(f"Transaction failed: {e}")

api_distance = HopeCenterDistancer()
conn = get_connection()
update_incident_nearest_hope(conn, api_distance)
conn.close()





