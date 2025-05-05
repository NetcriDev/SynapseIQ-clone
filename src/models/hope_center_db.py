import psycopg2
hope_centers_data = [
    {
        "state": "Minnesota",
        "city": "",
        "name": "Minnesota Center",
        "address": "Minnesota - 7450 France Ave S Edina MN 55435",
        "latitude": 44.86768643594557,
        "longitude": -93.32968754065874,
        "state_abbreviation": "MN"
    },
    {
        "state": "Arizona",
        "city": "Tempe",
        "name": "Arizona - Tempe Center",
        "address": "Arizona - Tempe - Renew health Tempe 426 E Southern Ave Ste 101 Tempe AZ 85282",
        "latitude": 33.39326624199211,
        "longitude": -111.9328099134243,
        "state_abbreviation": "AZ"
    },
    {
        "state": "Arizona",
        "city": "Phoenix",
        "name": "Arizona - Phoenix Center",
        "address": "Arizona - Phoenix - Renew Health West, 2350N 75th Ave, Suite 113, Phoenix, AZ 85035",
        "latitude": 33.474183993336275,
        "longitude": -112.22233796504828,
        "state_abbreviation": "AZ"
    },
    {
        "state": "Texas",
        "city": "Houston",
        "name": "Texas Houston Center",
        "address": "4543 Post Oak Place Suite 223 Houston, TX 77027",
        "latitude": 29.749943138073178,
        "longitude": -95.44943709276627,
        "state_abbreviation": "TX"
    },
    {
        "state": "Ohio",
        "city": "Cincinnati",
        "name": "Cincinnati Ohio Center",
        "address": "3801 Sharon Park Ln Suite 150, Sharonville, OH 45241",
        "latitude": 39.285904787054996,
        "longitude": -84.39654556200719,
        "state_abbreviation": "OH"
    },
    {
        "state": "Ohio",
        "city": "Dayton",
        "name": "Dayton Ohio Center",
        "address": "Dayton Ohio - 7391 Brandt Pike Ste C, Dayton, OH 45424",
        "latitude": 39.85871316299059,
        "longitude": -84.1062360859886,
        "state_abbreviation": "OH"
    },
    {
        "state": "Illinois",
        "city": "Chicago",
        "name": "Chicago Center",
        "address": "Chicago - 1100 Lake Street Suite LL54 Oak Park, IL 60301",
        "latitude": 41.88871130782507,
        "longitude": -87.80308357703832,
        "state_abbreviation": "IL"
    },
    {
        "state": "NewMexico",
        "city": "Las Cruces",
        "name": "NewMexico Las Cruces Center",
        "address": "NewMexico Las Cruces- Esperanza Medical and Wellness 4420 N. Sonoma Ranch Blvd. Ste. B Las Cruces, NM 88011",
        "latitude": 32.36670516111531,
        "longitude": -106.73747488252057,
        "state_abbreviation": "NM"
    },
    {
        "state": "North Carolina",
        "city": "Winston Salem",
        "name": "Winston-Salem Center",
        "address": "1255 Creekshire Way, Unit 220, Winston-Salem, NC 27103",
        "latitude": 36.066557,
        "longitude": -80.325126,
        "state_abbreviation": "NC"
    }
]


# PostgreSQL connection parameters
db_params = {
    "dbname": "crash_records_001",
    "user": "synapseiq",
    "password": "SynapseIQ$2025",
    "host": "localhost",
    "port": "5432"
}

def create_hope_center_table():
    with psycopg2.connect(**db_params) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS hope_center (
                    id SERIAL PRIMARY KEY,
                    state TEXT,
                    city TEXT,
                    name TEXT,
                    address TEXT,
                    latitude DOUBLE PRECISION,
                    longitude DOUBLE PRECISION,
                    state_abbreviation TEXT
                )
            """)
        conn.commit()

def insert_hope_centers_from_list(data):
    with psycopg2.connect(**db_params) as conn:
        with conn.cursor() as cur:
            for center in data:
                cur.execute("""
                    INSERT INTO hope_center (state, city, name, address, latitude, longitude, state_abbreviation)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    center["state"],
                    center["city"],
                    center["name"],
                    center["address"],
                    center["latitude"],
                    center["longitude"],
                    center["state_abbreviation"]
                ))
        conn.commit()

# Run setup and insertion
create_hope_center_table()
insert_hope_centers_from_list(hope_centers_data)