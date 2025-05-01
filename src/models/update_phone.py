import psycopg2
from typing import Optional
from src.services.api_contact import DataIrisSession
from src.utils.utils_api_contact import DatabaseType
import os

def update_passenger_phones(
    conn: psycopg2.extensions.connection,
    session: 'DataIrisSession'  # Instancia de la clase DataIrisSession
) -> None:
    """
    Updates the 'phone2' field in the 'passengers' table by querying phone numbers
    using DataIrisSession.safe_get_contact_resolution and extracting them with extract_phone_if_valid.

    Args:
        conn: Active PostgreSQL database connection.
        session: Instance of DataIrisSession with methods safe_get_contact_resolution and extract_phone_if_valid.
    """
    try:
        with conn.cursor() as cur:
            # Step 1: Fetch passengers that need phone2 update
            cur.execute("""
                SELECT id, first_name, middle_name, last_name, age, state
                FROM passengers
                WHERE (phone2 IS NULL OR phone2 = '' OR phone2 = ',' OR phone2 = ' , ') and notes NOT LIKE 'Person Number:%'
            """)
            passengers = cur.fetchall()

            print(f"Found {len(passengers)} passengers to process.")

            for passenger in passengers:
                id_, first_name, middle_name, last_name, age, state = passenger

                if not first_name or not last_name:
                    continue  # First and last name are necessary

                # Step 2: Query the DataIris API
                api_response = session.safe_get_contact_resolution(
                    database_type="consumer",  # Ajusta si tu base es distinta
                    first_name=first_name or "",
                    last_name=last_name or "",
                    middle_name=middle_name or "",
                    age=str(age) if age is not None else "",
                    state=state or ""
                )

                if not api_response:
                    print(f"No API response for passenger ID {id_}.")
                    continue

                # Step 3: Extract phone using standardized method
                phone_info = session.extract_phone_if_valid(api_response)

                phone_number = (phone_info.get("CellPhone") or "") + ", " + (phone_info.get("Phone") or "")

                if phone_number:
                    print(f"Updating passenger ID {id_} with phone: {phone_number}")
                    # Step 4: Update the database
                    cur.execute("""
                        UPDATE passengers
                        SET phone2 = %s
                        WHERE id = %s
                    """, (phone_number, id_))
                else:
                    print(f"No valid phone found for passenger ID {id_}.")

            conn.commit()
            print("All phone updates committed successfully.")

    except Exception as e:
        conn.rollback()
        print(f"Error updating phones: {e}")


home_path = "/Users/cristianb/Documents/Python/rel8ed/SynapseIQ_staging"
sesion = DataIrisSession(token_file_path= os.path.join(home_path ,"config/token.json"))

# Ejemplo de uso:
conn = psycopg2.connect(
    dbname="crash_records_001",
    user="synapseiq",
    password="SynapseIQ$2025",
    host="localhost",
    port="5433"
)

# Tu objeto 'session' debe ser ya una instancia de DataIrisSession
update_passenger_phones(conn, sesion)

conn.close()


