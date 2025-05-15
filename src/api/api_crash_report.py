import psycopg2
import os
import psycopg2.extras
from fastapi import FastAPI, Query, HTTPException, Response, Depends, WebSocket, WebSocketDisconnect
from typing import List, Optional, Dict
from datetime import datetime, time
from src.models.models_api import Passenger, PassengerUpdatePhones, Vehicle, IncidentReport, ChatRequest, ChatResponse
from config.config import get_connection
from src.utils.util_pagination import paginate
from src.utils.parse_date import parse_date
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.responses import FileResponse
from psycopg2.extras import RealDictCursor
from src.models.models_api import CrashReportWithPassengers  # Define este modelo pydantic si no existe aún
from src.api.notification_manager import connected_clients
from src.services.ibm_fundational_models import WatsonXModelHandler
from dotenv import load_dotenv
from pathlib import Path

# Ruta absoluta o relativa al archivo .env
#dotenv_path = Path("/Users/cristianb/Documents/Python/rel8ed/SynapseIQ_staging/.env")
dotenv_path = Path("/home/SynapseIQ/.env")

# Cargar el archivo .env desde la ruta específica
load_dotenv(dotenv_path=dotenv_path)

# Leer valores
api_key = os.getenv("API_KEY")
project_id = os.getenv("PROJECT_ID")
url = os.getenv("URL")


# Global instance (reusable)
watson_handler = WatsonXModelHandler(
    api_key=api_key,
    project_id=project_id,
    url=url,
    default_model_id="meta-llama/llama-3-2-11b-vision-instruct"
)

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


@app.get("/incident/pdf/{report_number}")
def get_incident_pdf(report_number: str, response: Response = None):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT original_document_location FROM incident_reports WHERE report_number = %s", (report_number,))
    result = cur.fetchone()
    conn.close()

    if result is None or result=="None" or str(result).strip() == '' or str(result).lower().strip() == 'null':
        raise HTTPException(status_code=404, detail="Report not found")

    pdf_path = result[0]

    # validamos que pdf_path sea un valor correcto
    if not pdf_path or str(pdf_path).strip().lower() == 'null':
        raise HTTPException(status_code=404, detail="Invalid PDF path")

    if not os.path.isfile(pdf_path):
        raise HTTPException(status_code=404, detail="PDF file not found on disk")

    response.headers["Access-Control-Allow-Origin"] = "*"
    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename=os.path.basename(pdf_path)
    )


@app.get("/incident/pdf/view/{report_number}")
def view_incident_pdf(report_number: str, response: Response = None):
    conn = get_connection()
    cur = conn.cursor()

    # Obtener la ruta del archivo PDF desde la base de datos
    cur.execute("SELECT original_document_location FROM incident_reports WHERE report_number = %s", (report_number,))
    result = cur.fetchone()
    conn.close()

    if result is None or str(result).strip() == '' or str(result).lower().strip() == 'null':
        raise HTTPException(status_code=404, detail="Report not found")

    pdf_path = result[0]

    # validamos que pdf_path sea un valor correcto
    if not pdf_path or str(pdf_path).strip().lower() == 'null':
        raise HTTPException(status_code=404, detail="Invalid PDF path")

    if not os.path.isfile(pdf_path):
        raise HTTPException(status_code=404, detail="PDF file not found on disk")

    #'inline' para que se visualice en el navegador
    response.headers["Access-Control-Allow-Origin"] = "*"

    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "font-src 'self' https://assets.ngrok.com; "
        "style-src 'self' 'unsafe-inline'; "
        "script-src 'self';"
    )

    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename=os.path.basename(pdf_path),
        headers={"Content-Disposition": f'inline; filename="{os.path.basename(pdf_path)}"'}
    )


# Endpoint: Filtrado múltiple de incident_reports con paginación
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

    base_query = "FROM incident_reports"
    if filters:
        base_query += " WHERE " + " AND ".join(filters)

    # Obtener total si deseas usarlo (opcional)
    count_query = f"SELECT COUNT(*) {base_query}"
    cur.execute(count_query, tuple(params))
    total_rows = cur.fetchone()["count"]

    # Agregar paginación al query final
    offset = (page - 1) * page_size
    select_query = f"""
        SELECT * {base_query}
        ORDER BY accident_datetime DESC
        LIMIT %s OFFSET %s
    """
    cur.execute(select_query, tuple(params + [page_size, offset]))
    incidents = cur.fetchall()

    # Agregar vehículos y pasajeros
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
        response.headers["X-Total-Count"] = str(total_rows)
        response.headers["X-Page"] = str(page)
        response.headers["X-Page-Size"] = str(page_size)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "font-src 'self' https://assets.ngrok.com; "
            "style-src 'self' 'unsafe-inline'; "
            "script-src 'self';"
        )

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

#texas endpoint
@app.get("/list-reports-texas/search", response_model=List[CrashReportWithPassengers])
def search_crash_reports(
    crash_id: Optional[str] = None,
    state: Optional[str] = None,
    city: Optional[str] = None,
    county: Optional[str] = None,
    agency: Optional[str] = None,
    crash_date: Optional[datetime] = None,
    crash_severity: Optional[str] = None,
    page: int = 1,
    page_size: int = 10,
    response: Response = None
):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    filters = []
    params = []

    if crash_id:
        filters.append("crash_id ILIKE %s")
        params.append(f"%{crash_id}%")
    if state:
        filters.append("state ILIKE %s")
        params.append(f"%{state}%")
    if city:
        filters.append("city ILIKE %s")
        params.append(f"%{city}%")
    if county:
        filters.append("county ILIKE %s")
        params.append(f"%{county}%")
    if agency:
        filters.append("agency ILIKE %s")
        params.append(f"%{agency}%")
    if crash_date:
        filters.append("DATE(crash_date) = %s")
        params.append(crash_date)
    if crash_severity:
        filters.append("crash_severity ILIKE %s")
        params.append(f"%{crash_severity}%")

    query = """
    SELECT * FROM list_of_accident_report
    """

    if filters:
        query += " WHERE " + " AND ".join(filters)

    query += " ORDER BY crash_date DESC"

    # Paginación
    offset = (page - 1) * page_size
    query += f" LIMIT {page_size} OFFSET {offset}"

    cur.execute(query, tuple(params))
    crashes = cur.fetchall()

    for crash in crashes:
        cur.execute("""
            SELECT * FROM passenger_report_list WHERE crash_report_id = %s
        """, (crash['id'],))
        passengers = cur.fetchall()
        crash['passengers'] = passengers

    conn.close()

    if response:
        response.headers["Access-Control-Allow-Origin"] = "*"

    return crashes


def get_text_from_pdf(report_number: str, state: str) -> str:
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT text_from_pdf FROM incident_reports
            WHERE report_number = %s AND state = %s
            ORDER BY id DESC LIMIT 1
        """, (report_number, state))
        result = cur.fetchone()
        conn.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    if not result:
        return "No incident report found for this report number and state"

    text = result[0]
    if not text or str(text).strip().lower() in [""," ", "none", "null"]:
        return "There is no text obtained from the crash report"
    print(".>>>>>>>>",text)
    return text


# Endpoint principal de chat
@app.post("/chat", response_model=ChatResponse)
async def chat_with_model(request: ChatRequest):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Obtener texto si no se proporciona
    text_content = get_text_from_pdf(request.report_number, request.state)

    # Buscar sesión activa o crear una nueva
    cur.execute("""
        SELECT * FROM chat_session 
        WHERE report_number = %s AND state = %s AND status = 'active'
        ORDER BY started_at DESC LIMIT 1
    """, (request.report_number, request.state))
    session = cur.fetchone()

    if not session:
        cur.execute("""
            INSERT INTO chat_session (report_number, state, status, model_id) 
            VALUES (%s, %s ,'active', %s) RETURNING id
        """, (request.report_number, request.state, watson_handler.default_model_id))
        session_id = cur.fetchone()["id"]
        conn.commit()
    else:
        session_id = session["id"]

    # Guardar Pregunta
    cur.execute("""
        INSERT INTO chat_messages (report_number, state ,session_id, role, content) 
        VALUES (%s, %s, %s, 'user', %s)
    """, (request.report_number, request.state ,session_id, request.question))
    conn.commit()

    # Enviar a modelo
    try:
        result = await watson_handler.query(
            question=request.question,
            text_content=text_content
        )
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    # Guardar respuesta
    cur.execute("""
        INSERT INTO chat_messages (report_number, state, session_id, role, content) 
        VALUES (%s, %s, %s, 'assistant', %s)
    """, (request.report_number, request.state, session_id, result["response"]))
    conn.commit()
    conn.close()

    return ChatResponse(response=result["response"], session_id=session_id)


@app.get("/chat/history", response_model=Dict)
def get_chat_history(report_number: str, state: str):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute("""
        SELECT id, report_number, state FROM chat_session
        WHERE report_number = %s AND state = %s AND status = 'active'
        ORDER BY started_at DESC LIMIT 1
    """, (report_number, state))
    session = cur.fetchone()

    if not session:
        raise HTTPException(status_code=404, detail="No active session found")

    session_id = session["id"]

    cur.execute("""
        SELECT role, content, created_at FROM chat_messages
        WHERE session_id = %s
        ORDER BY created_at ASC
    """, (session_id,))
    messages = cur.fetchall()
    conn.close()

    return {
        "session_id": session_id,
        "report_number": session["report_number"],
        "state": session["state"],
        "history": messages
    }



# @app.websocket("/ws/notifications")
# async def websocket_notifications(websocket: WebSocket):
#     await websocket.accept()
#     connected_clients.append(websocket)
#     try:
#         while True:
#             await websocket.receive_text()  # Mantiene la conexión activa
#     except WebSocketDisconnect:
#         connected_clients.remove(websocket)

