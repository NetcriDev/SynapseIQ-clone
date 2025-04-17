


import psycopg2
from datetime import datetime

def insert_crash_report_to_db():
    try:
        conn = psycopg2.connect(
            dbname="crash_records_001",
            user="synapseiq",
            password="SynapseIQ$2025",
            host="localhost",
            port="5432"
        )
        cur = conn.cursor()

        # Insertar en incident_reports
        cur.execute("""
            INSERT INTO incident_reports (
                report_number,
                internal_report_number,
                accident_datetime,
                city,
                street,
                state,
                latitude,
                longitude,
                weather_condition,
                road_condition,
                crash_severity,
                number_of_units,
                narrative,
                generation_date,
                responsible,
                original_document_location
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            '2025040462',
            'il2025040462',
            datetime(2025, 4, 10, 1, 31),
            'Joliet',
            'Plainfield Rd & Ingalls',
            'IL',
            None,
            None,
            'Clear',
            'Dry',
            'B Injury and / or Tow Due To Crash',
            3,
            'On todays date at approximately 1331 hours I, Officer Long #139 and Officer Ceja #111 responded to a 3 car accident with no injuries. Unit 2 could not avoid a collision and hit Unit 1. Then, Unit 2 struck a guard rail. Unit 3, approaching from the opposite direction, collided with Unit 1 after it spun into her lane. All units were towed. Driver of Unit 1 was cited for failing to yield from a private drive.',
            datetime.now(),
            'Long, M',
            '/home/data/illinois/2025040462.a147bec0.pdf'
        ))
        incident_report_id = cur.fetchone()[0]

        # Insertar vehículos
        vehicles = [
            {
                "unit_number": 1,
                "make": "CHEVROLET",
                "model": "COBALT",
                "year": 2008,
                "color": "RED",
                "license_plate_number": "ILP2821685",
                "license_plate_state": "IL",
                "vin": "1G1AM18B487129827",
                "damage_severity": "DISABLING DAMAGE",
                "insurance_company": "UNIQUE INSURANCE COMPANY",
                "policy_number": "M226-6459-1949",
                "driver": ("ORLAIDY", "", "MESIAS ARRAEZ"),
                "driver_address": "106 HIGHPOINT DR APT 107, ROMEOVILLE, IL 60446",
                "driver_state": "IL",
                "owner": ("ORLAIDY", "", "MESIAS ARRAEZ"),
                "owner_address": "106 HIGHPOINT DR APT 107, ROMEOVILLE, IL 60446"
            },
            {
                "unit_number": 2,
                "make": "KIA",
                "model": "OPTIMA",
                "year": 2013,
                "color": "PURPLE",
                "license_plate_number": "K495145",
                "license_plate_state": "IL",
                "vin": "KNAGM4AD8D5061145",
                "damage_severity": "DISABLING DAMAGE",
                "insurance_company": "DIRECTAUTO",
                "policy_number": "M260-0005-1218",
                "driver": ("TERICA", "", "FRANKLIN"),
                "driver_address": "550 FULLER, BOLINGBROOK, IL 60440",
                "driver_state": "IL",
                "owner": ("TERICA", "", "FRANKLIN"),
                "owner_address": "550 FULLER, BOLINGBROOK, IL 60440"
            },
            {
                "unit_number": 3,
                "make": "GMC",
                "model": "ACADIA SLE",
                "year": 2015,
                "color": "BLACK",
                "license_plate_number": "AB80183",
                "license_plate_state": "IL",
                "vin": "1GKKRNED4FJ203164",
                "damage_severity": "DISABLING DAMAGE",
                "insurance_company": "SAFEWAY INSURANCE COMPANY",
                "policy_number": "M650-6407-5675",
                "driver": ("OBDULIA", "", "MARIN"),
                "driver_address": "715 CLEMENT ST, JOLIET, IL 60435",
                "driver_state": "IL",
                "owner": ("OBDULIA", "", "MARIN"),
                "owner_address": "715 CLEMENT ST, JOLIET, IL 60435"
            }
        ]

        vehicle_ids = []
        for v in vehicles:
            cur.execute("""
                INSERT INTO vehicles (
                    incident_report_id,
                    unit_number,
                    make,
                    model,
                    year,
                    color,
                    license_plate_number,
                    license_plate_state,
                    vin,
                    damage_severity,
                    insurance_company,
                    policy_number,
                    driver_name,
                    driver_first_name,
                    driver_middle_name,
                    driver_last_name,
                    driver_address,
                    driver_state,
                    owner_name,
                    owner_first_name,
                    owner_middle_name,
                    owner_last_name,
                    owner_address
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                incident_report_id,
                v["unit_number"],
                v["make"],
                v["model"],
                v["year"],
                v["color"],
                v["license_plate_number"],
                v["license_plate_state"],
                v["vin"],
                v["damage_severity"],
                v["insurance_company"],
                v["policy_number"],
                f"{v['driver'][2]}, {v['driver'][0]}, {v['driver'][1]}",
                v["driver"][0],
                v["driver"][1],
                v["driver"][2],
                v["driver_address"],
                v["driver_state"],
                f"{v['owner'][2]}, {v['owner'][0]}, {v['owner'][1]}",
                v["owner"][0],
                v["owner"][1],
                v["owner"][2],
                v["owner_address"]
            ))
            vehicle_ids.append(cur.fetchone()[0])

        # Insertar pasajeros
        passengers = [
            ("MESIAS ARRAEZ", "ORLAIDY", "", 44, "F", 1980),
            ("FRANKLIN", "TERICA", "", 34, "F", 1991),
            ("MARIN", "OBDULIA", "", 49, "F", 1975)
        ]

        for i, p in enumerate(passengers):
            cur.execute("""
                INSERT INTO passengers (
                    vehicle_id,
                    name,
                    first_name,
                    middle_name,
                    last_name,
                    age,
                    gender,
                    year_birth
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                vehicle_ids[i if i < len(vehicle_ids) else -1],
                f"{p[0]}, {p[1]}, {p[2]}",
                p[1],
                p[2],
                p[0],
                p[3],
                p[4],
                p[5]
            ))

        conn.commit()
        cur.close()
        conn.close()
        print("Datos insertados exitosamente.")

    except Exception as e:
        print("Error durante la inserción:", e)

# Llamar directamente la función
insert_crash_report_to_db()
