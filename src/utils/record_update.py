
from config.config import get_connection
from src.utils.split_name import split_driver_name


def process_names_in_db():
    conn = get_connection()
    cur = conn.cursor()

    # Primero, actualizar los nombres en vehicles
    cur.execute("SELECT id, driver_name, owner_name FROM vehicles")
    vehicles = cur.fetchall()

    for vehicle in vehicles:
        vehicle_id, driver_name, owner_name = vehicle

        driver_first, driver_middle, driver_last = split_driver_name(driver_name)
        owner_first, owner_middle, owner_last = split_driver_name(owner_name)

        cur.execute("""
            UPDATE vehicles
            SET driver_first_name = %s,
                driver_middle_name = %s,
                driver_last_name = %s,
                owner_first_name = %s,
                owner_middle_name = %s,
                owner_last_name = %s
            WHERE id = %s
        """, (driver_first, driver_middle, driver_last, owner_first, owner_middle, owner_last, vehicle_id))

    # Luego actualizamos los nombres en passengers
    cur.execute("SELECT id, name FROM passengers")
    passengers = cur.fetchall()

    for passenger in passengers:
        passenger_id, name = passenger

        first_name, middle_name, last_name = split_driver_name(name)

        cur.execute("""
            UPDATE passengers
            SET first_name = %s,
                middle_name = %s,
                last_name = %s
            WHERE id = %s
        """, (first_name, middle_name, last_name, passenger_id))

    conn.commit()
    cur.close()
    conn.close()

if __name__ == "__main__":
    process_names_in_db()
