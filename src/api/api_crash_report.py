from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import psycopg2
import os

app = FastAPI()

# Configuración de la base de datos
db_config = {
    "dbname": "crash_records",
    "user": "synapseiq",
    "password": "SynapseIQ$2025",
    "host": "localhost",
    "port": "5432"
}

# Modelos Pydantic
class IncidentReport(BaseModel):
    id: int
    report_number: str
    accident_datetime: Optional[str]
    city: Optional[str]
    state: Optional[str]
    crash_severity: Optional[str]
    json: Optional[dict]

class Vehicle(BaseModel):
    id: int
    incident_report_id: int
    driver_name: Optional[str]
    driver_license: Optional[str]
    insurance_company: Optional[str]

class Passenger(BaseModel):
    id: int
    vehicle_id: int
    role: Optional[str]
    name: Optional[str]
    age: Optional[int]

# Utilidad para conectar y consultar

def get_connection():
    return psycopg2.connect(**db_config)

# Rutas
@app.get("/incidents", response_model=List[IncidentReport])
def get_incidents():
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, report_number, accident_datetime, city, state, crash_severity, json FROM incident_reports LIMIT 100")
        rows = cur.fetchall()
        conn.close()
        return [IncidentReport(
            id=r[0], report_number=r[1], accident_datetime=str(r[2]) if r[2] else None,
            city=r[3], state=r[4], crash_severity=r[5], json=r[6]) for r in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/vehicles", response_model=List[Vehicle])
def get_vehicles():
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, incident_report_id, driver_name, driver_license, insurance_company FROM vehicles LIMIT 100")
        rows = cur.fetchall()
        conn.close()
        return [Vehicle(
            id=r[0], incident_report_id=r[1], driver_name=r[2], driver_license=r[3], insurance_company=r[4]) for r in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/passengers", response_model=List[Passenger])
def get_passengers():
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, vehicle_id, role, name, age FROM passengers LIMIT 100")
        rows = cur.fetchall()
        conn.close()
        return [Passenger(
            id=r[0], vehicle_id=r[1], role=r[2], name=r[3], age=r[4]) for r in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
