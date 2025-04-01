from fastapi import FastAPI, Query, HTTPException, Response
from typing import List, Optional
from datetime import datetime, time
from src.models.models_api import Passenger, PassengerUpdatePhones, Vehicle, IncidentReport
from config.config import get_connection
from src.utils.util_pagination import paginate
from src.utils.parse_date import parse_date
import psycopg2
import psycopg2.extras
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

app = FastAPI()

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # o especifica ["https://tudexampleDOminio.com"]
    allow_credentials=True,
    allow_methods=["*"],  # o lista específica ["GET", "POST"]
    allow_headers=["*"],  # o lista específica ["Authorization", "Content-Type"]
)

# Endpoint: Search by report_number and fetch vehicles + passengers
@app.get("/incident/by-report", response_model=IncidentReport)
def get_incident_by_report_number(report_number: str,response: Response= None):
    response.headers["Access-Control-Allow-Origin"] = "*"
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute("SELECT * FROM incident_reports WHERE report_number = %s", (report_number,))
    incident = cur.fetchone()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    cur.execute("SELECT * FROM vehicles WHERE incident_report_id = %s", (incident['id'],))
    vehicles = cur.fetchall()
    for v in vehicles:
        cur.execute("SELECT * FROM passengers WHERE vehicle_id = %s", (v['id'],))
        v['passengers'] = cur.fetchall()

    incident['vehicles'] = vehicles
    conn.close()
    
    return incident

# Endpoint: Filtrado múltiple de incident_reports
@app.get("/incident/search", response_model=List[IncidentReport])
def search_incidents(
    generation_from: Optional[str] = None,
    generation_to: Optional[str] = None,
    accident_from: Optional[str] = None,
    accident_to: Optional[str] = None,
    zip: Optional[str] = None,
    state: Optional[str] = None,
    city: Optional[str] = None,
    crash_severity: Optional[str] = None,
    page: int = 1,
    page_size: int = 15,
    response: Response = None
):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    filters = []
    params = []

    if generation_from:
        filters.append("generation_date >= %s")
        params.append(parse_date(generation_from))
    if generation_to:
        end_of_day = datetime.combine(parse_date(generation_to), time(23, 59, 59))
        filters.append("generation_date <= %s")
        params.append(end_of_day)
    if accident_from:
        filters.append("accident_datetime >= %s")
        params.append(parse_date(accident_from))
    if accident_to:
        end_of_day = datetime.combine(parse_date(accident_to), time(23, 59, 59))
        filters.append("accident_datetime <= %s")
        params.append(end_of_day)
    if zip:
        filters.append("zip ILIKE %s")
        params.append(f"%{zip}%")
    if state:
        filters.append("state ILIKE %s")
        params.append(f"%{state}%")
    if city:
        filters.append("city ILIKE %s")
        params.append(f"%{city}%")
    if crash_severity:
        filters.append("crash_severity ILIKE %s")
        params.append(f"%{crash_severity}%")

    query = "SELECT * FROM incident_reports"
    if filters:
        query += " WHERE " + " AND ".join(filters)
    query += " ORDER BY generation_date DESC"

    cur.execute(query, tuple(params))
    incidents = cur.fetchall()

    for incident in incidents:
        cur.execute("SELECT * FROM vehicles WHERE incident_report_id = %s", (incident['id'],))
        vehicles = cur.fetchall()
        for v in vehicles:
            cur.execute("SELECT * FROM passengers WHERE vehicle_id = %s", (v['id'],))
            v['passengers'] = cur.fetchall()
        incident['vehicles'] = vehicles

    conn.close()
    if response:
        response.headers["Access-Control-Allow-Origin"] = "*"
    return incidents

# Endpoint: Buscar pasajeros por nombre, edad o license
@app.get("/passengers/search", response_model=List[Passenger])
def search_passengers(
    name: Optional[str] = None,
    age: Optional[int] = None,
    license_number: Optional[str] = None,
    page: int = 1,
    page_size: int = 10,
    response: Response = None
):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    filters = []
    params = []
    if name:
        filters.append("name ILIKE %s")
        params.append(f"%{name}%")
    if age is not None:
        filters.append("age = %s")
        params.append(age)
    if license_number:
        filters.append("license_number ILIKE %s")
        params.append(f"%{license_number}%")

    query = "SELECT * FROM passengers"
    if filters:
        query += " WHERE " + " AND ".join(filters)
    query += " ORDER BY id DESC"

    cur.execute(query, tuple(params))
    passengers = cur.fetchall()
    conn.close()
    if response:
        response.headers["Access-Control-Allow-Origin"] = "*"
    return passengers

# Endpoint: Editar teléfonos de un pasajero
@app.put("/passenger/{passenger_id}/phones")
def update_passenger_phones(passenger_id: int, phones: PassengerUpdatePhones, response: Response = None):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE passengers SET phone1 = %s, phone2 = %s WHERE id = %s
    """, (phones.phone1, phones.phone2, passenger_id))
    if cur.rowcount == 0:
        conn.rollback()
        raise HTTPException(status_code=404, detail="Passenger not found")
    conn.commit()
    conn.close()
    if response:
        response.headers["Access-Control-Allow-Origin"] = "*"
    return {"message": "Phone numbers updated successfully"}

# Endpoint: Buscar vehículos con filtros y unir incidentes y pasajeros
@app.get("/vehicles/search", response_model=List[Vehicle])
def search_vehicles(
    license_plate_number: Optional[str] = None,
    license_plate_state: Optional[str] = None,
    driver_name: Optional[str] = None,
    driver_license: Optional[str] = None,
    owner_name: Optional[str] = None,
    page: int = 1,
    page_size: int = 10,
    response: Response=None
):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    filters = []
    params = []
    if license_plate_number:
        filters.append("license_plate_number ILIKE %s")
        params.append(f"%{license_plate_number}%")
    if license_plate_state:
        filters.append("license_plate_state = %s")
        params.append(license_plate_state)
    if driver_name:
        filters.append("driver_name ILIKE %s")
        params.append(f"%{driver_name}%")
    if driver_license:
        filters.append("driver_license ILIKE %s")
        params.append(f"%{driver_license}%")
    if owner_name:
        filters.append("owner_name ILIKE %s")
        params.append(f"%{owner_name}%")

    query = "SELECT * FROM vehicles"
    if filters:
        query += " WHERE " + " AND ".join(filters)
    query += " ORDER BY id DESC"

    cur.execute(query, tuple(params))
    vehicles = cur.fetchall()

    for v in vehicles:
        cur.execute("SELECT * FROM passengers WHERE vehicle_id = %s", (v['id'],))
        v['passengers'] = cur.fetchall()
        cur.execute("SELECT * FROM incident_reports WHERE id = %s", (v['incident_report_id'],))
        v['incident'] = cur.fetchone()

    conn.close()
    if response:
        response.headers["Access-Control-Allow-Origin"] = "*"
    return vehicles
