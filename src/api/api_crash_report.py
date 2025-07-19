import psycopg2
import os
import re
import psycopg2.extras
import shutil
from dotenv import load_dotenv
from pathlib import Path
from math import ceil
import pandas as pd
from typing import List, Optional, Dict
from datetime import datetime, time
from config.config import get_connection
from src.utils.parse_date import parse_date
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from psycopg2.extras import RealDictCursor
from src.models.models_api import CrashReportWithPassengers  # Define este modelo pydantic si no existe aún
from src.api.notification_manager import connected_clients
from src.services.ibm_fundational_models import WatsonXModelHandler
from src.utils.ohio_extraction import extract_traffic_data_from_pdf
from src.database.csv_ohio_into_db import insert_data_from_dataframe
from src.utils.status_pdf_utils import save_estatus_pdf
from src.utils.general_utils import convert_df_to_csv
from src.connectors.scrapperGeorgia import extract_df_from_georgia
from src.database.loaderGeorgia import loader_df_to_db
from src.utils.triggers_airflow import trigger_airflow_dag
from src.connectors.downloaderNC import download_pdfs_from_excel
from src.database.loaderNC import loader_df_to_db
from src.parsers.loaderOhio_xlsx import load_ohio_data
from passlib.context import CryptContext
from fastapi import (FastAPI, 
                     Query,
                     File,
                     UploadFile,
                     HTTPException, 
                     Response, 
                     Depends, 
                     WebSocket, 
                     WebSocketDisconnect, 
                     Body, 
                     Path as PathUrl)
from src.models.models_api import (
    Passenger,
    PassengerUpdatePhones,
    Vehicle,
    IncidentReport,
    ChatRequest,
    ChatResponse,
    MarketerUserCreate,
    MarketerUserRead,
    AssignMarketerUser,
    AssignmentUpdateRequest
)

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

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

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


@app.get("/incident/search")
def search_incidents(
    website: Optional[str] = None,
    generation_from: Optional[str] = None,
    generation_to: Optional[str] = None,
    accident_from: Optional[str] = None,
    accident_to: Optional[str] = None,
    zip: Optional[str] = None,
    state: Optional[str] = None,
    city: Optional[str] = None,
    crash_severity: Optional[str] = None,
    is_external: Optional[str] = None,
    hotlead: Optional[str] = None,
    hasphone: Optional[str] = None,
    hasinsurance_details: Optional[str] = None,
    hasname: Optional[str] = None,
    over18: Optional[str] = None,
    marketer_username: Optional[str] = None,
    page: int = 1,
    page_size: int = 15,
    response: Response = None
):
    conn = psycopg2.connect(
        dbname="crash_records_001",
        user="synapseiq",
        password="SynapseIQ$2025",
        host="localhost",
        port="5432"
    )
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    filters = []
    params = []

    # --- Filtros sobre incident_reports ---
    if website:
        filters.append("ir.website ILIKE %s")
        params.append(f"%{website}%")
    if generation_from:
        filters.append("ir.generation_date >= %s")
        params.append(parse_date(generation_from))
    if generation_to:
        filters.append("ir.generation_date <= %s")
        params.append(datetime.combine(parse_date(generation_to), time(23, 59, 59)))
    if accident_from:
        filters.append("ir.accident_datetime >= %s")
        params.append(parse_date(accident_from))
    if accident_to:
        filters.append("ir.accident_datetime <= %s")
        params.append(datetime.combine(parse_date(accident_to), time(23, 59, 59)))
    if zip:
        filters.append("ir.zip ILIKE %s")
        params.append(f"%{zip}%")
    if state:
        filters.append("ir.state ILIKE %s")
        params.append(f"%{state}%")
    if city:
        filters.append("ir.city ILIKE %s")
        params.append(f"%{city}%")
    if crash_severity:
        filters.append("ir.crash_severity ILIKE %s")
        params.append(f"%{crash_severity}%")
    if is_external:
        filters.append("ir.is_external ILIKE %s")
        params.append(f"%{is_external}%")

    # --- Filtros sobre passengers ---
    if hotlead:
        filters.append("p.hotlead ILIKE %s")
        params.append(f"%{hotlead}%")
    if hasphone:
        filters.append("p.hasphone ILIKE %s")
        params.append(f"%{hasphone}%")
    if hasinsurance_details:
        filters.append("p.hasinsurance_details ILIKE %s")
        params.append(f"%{hasinsurance_details}%")
    if hasname:
        filters.append("p.hasname ILIKE %s")
        params.append(f"%{hasname}%")
    if over18:
        filters.append("p.over18 ILIKE %s")
        params.append(f"%{over18}%")

    # --- Filtro por marketer (username o email) y rol ---
    if marketer_username:
        # Buscar marketer por username o email
        cur.execute("""
            SELECT id, role, username FROM marketer_users 
            WHERE username ILIKE %s OR email ILIKE %s
            LIMIT 1
        """, (marketer_username, marketer_username))
        marketer_info = cur.fetchone()

        if not marketer_info:
            conn.close()
            raise HTTPException(status_code=404, detail="Marketer user not found")

        marketer_id = marketer_info["id"]
        marketer_role = marketer_info["role"].lower()
        marketer_username = marketer_info["username"]

        if marketer_role != "admin":
            # Si no es admin, filtrar los resultados a los pasajeros asignados a ese marketer
            filters.append("pmu.marketer_user_id = %s")
            params.append(marketer_id)

    # --- Obtener IDs de incidentes filtrados ---
    base_query = """
        SELECT DISTINCT ir.id, ir.accident_datetime
        FROM incident_reports ir
        JOIN vehicles v ON v.incident_report_id = ir.id
        JOIN passengers p ON p.vehicle_id = v.id
        LEFT JOIN passenger_marketer_users pmu ON pmu.passenger_id = p.id
        LEFT JOIN marketer_users mu ON mu.id = pmu.marketer_user_id
    """
    if filters:
        base_query += " WHERE " + " AND ".join(filters)
    
    base_query += " ORDER BY ir.accident_datetime DESC"

    cur.execute(base_query, tuple(params))
    all_ids = [row["id"] for row in cur.fetchall()]
    total_rows = len(all_ids)
    paginated_ids = all_ids[(page - 1) * page_size : page * page_size]

    if not paginated_ids:
        conn.close()
        return []

    # --- Recuperar datos completos por incidente ---
    incidents = []
    for incident_id in paginated_ids:
        cur.execute("SELECT * FROM incident_reports WHERE id = %s", (incident_id,))
        incident = cur.fetchone()

        # Vehículos del incidente
        cur.execute("SELECT * FROM vehicles WHERE incident_report_id = %s", (incident_id,))
        vehicles = cur.fetchall()
        for v in vehicles:
            # Pasajeros filtrados
            passenger_query = """
                SELECT * FROM passengers
                WHERE vehicle_id = %s
            """
            passenger_filters = []
            passenger_params = [v["id"]]

            if hotlead:
                passenger_filters.append("hotlead ILIKE %s")
                passenger_params.append(f"%{hotlead}%")
            if hasphone:
                passenger_filters.append("hasphone ILIKE %s")
                passenger_params.append(f"%{hasphone}%")
            if hasinsurance_details:
                passenger_filters.append("hasinsurance_details ILIKE %s")
                passenger_params.append(f"%{hasinsurance_details}%")
            if hasname:
                passenger_filters.append("hasname ILIKE %s")
                passenger_params.append(f"%{hasname}%")
            if over18:
                passenger_filters.append("over18 ILIKE %s")
                passenger_params.append(f"%{over18}%")

            if passenger_filters:
                passenger_query += " AND " + " AND ".join(passenger_filters)

            cur.execute(passenger_query, tuple(passenger_params))
            passengers = cur.fetchall()

            for p in passengers:
                # Marketer users del pasajero (filtrados)
                marketer_query = """
                    SELECT mu.* FROM marketer_users mu
                    JOIN passenger_marketer_users pmu ON pmu.marketer_user_id = mu.id
                    WHERE pmu.passenger_id = %s
                """
                marketer_params = [p["id"]]
                if marketer_username:
                    marketer_query += " AND mu.username ILIKE %s"
                    marketer_params.append(f"%{marketer_username}%")

                cur.execute(marketer_query, tuple(marketer_params))
                p["marketer_users"] = cur.fetchall()

            v["passengers"] = passengers
        incident["vehicles"] = vehicles
        incidents.append(incident)

    # Headers
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

    conn.close()
    return incidents


# Endpoint: Buscar pasajeros por nombre, edad o license
@app.get("/passengers/search", response_model=List[Passenger])
def search_passengers(
    name: Optional[str] = None,
    age: Optional[int] = None,
    license_number: Optional[str] = None,
    hotlead: Optional[str] = None,
    hasphone: Optional[str] = None,
    hasinsurance_details: Optional[str] = None,
    hasname: Optional[str] = None,
    over18: Optional[str] = None,
    page: int = 1,
    page_size: int = 10,
    response: Response = None
):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    filters = []
    params = []


    if hotlead:
        filters.append("hotlead ILIKE %s")
        params.append(f"%{hotlead}%")
    if hasphone:
        filters.append("hasphone ILIKE %s")
        params.append(f"%{hasphone}%")
    if hasinsurance_details:
        filters.append("hasinsurance_details ILIKE %s")
        params.append(f"%{hasinsurance_details}%")
    if hasname:
        filters.append("hasname ILIKE %s")
        params.append(f"%{hasname}%")
    if over18:
        filters.append("over18 ILIKE %s")
        params.append(f"%{over18}%")
    if name:
        filters.append("name ILIKE %s")
        params.append(f"%{name}%")
    if age is not None:
        filters.append("age = %s")
        params.append(age)
    if license_number:
        filters.append("license_number ILIKE %s")
        params.append(f"%{license_number}%")

    where_clause = " WHERE " + " AND ".join(filters) if filters else ""

    # Count total rows
    count_query = f"SELECT COUNT(*) FROM passengers {where_clause}"
    cur.execute(count_query, tuple(params))
    total_items = cur.fetchone()["count"]
    total_pages = ceil(total_items / page_size) if page_size else 1
    offset = (page - 1) * page_size

    # Main paginated query
    query = f"""
        SELECT * FROM passengers
        {where_clause}
        ORDER BY id DESC
        LIMIT %s OFFSET %s
    """
    cur.execute(query, tuple(params + [page_size, offset]))
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


# ---------------- Endpoints de chat ----------------|

def get_text_from_pdf(report_number: str, website: str = None) -> str:
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT text_from_pdf FROM incident_reports
            WHERE report_number = %s
            ORDER BY id DESC LIMIT 1
        """, (report_number,))
        result = cur.fetchone()
        conn.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    if not result:
        return "No incident report found for this report number"

    text = result[0]
    if not text or str(text).strip().lower() in [""," ", "none", "null"]:
        return "There is no text obtained from the crash report"
    print(".>>>>>>>>",text)
    return text


# Endpoint principal de chat
@app.post("/chat", response_model=ChatResponse, tags=["Chat Model"])
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

    # Save Question
    cur.execute("""
        INSERT INTO chat_messages (report_number, state, session_id, role, content) 
        VALUES (%s, %s, %s, 'user', %s)
    """, (request.report_number, request.state, session_id, request.question))
    conn.commit()

    # Send to model
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


@app.get("/chat/history", response_model=Dict, tags=["Chat Model"])
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



# ======= Marketer Users =======

@app.post("/marketer-users/", response_model=MarketerUserRead, tags=["Marketer"])
def create_marketer_user(user: MarketerUserCreate):
    hashed_password = pwd_context.hash(user.password)
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("""
            INSERT INTO marketer_users (username, email, full_name, hashed_password, role)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, username, email, full_name, is_active, role
        """, (user.username, user.email, user.full_name, hashed_password, user.role))
        user_created = cur.fetchone()
        conn.commit()
        return user_created
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conn.close()


@app.get("/marketer-users/", response_model=List[MarketerUserRead], tags=["Marketer"])
def get_all_marketer_users():
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT id, username, email, full_name, is_active, role FROM marketer_users ORDER BY id")
    result = cur.fetchall()
    conn.close()
    return result


@app.get("/marketer-users/{user_id}", response_model=MarketerUserRead, tags=["Marketer"])
def get_marketer_user(user_id: int = PathUrl(...)):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT id, username, email, full_name, is_active, role FROM marketer_users WHERE id = %s", (user_id,))
    user = cur.fetchone()
    conn.close()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user



@app.put("/marketer-users/{user_id}", tags=["Marketer"])
def update_marketer_user(
    user_id: int,
    full_name: Optional[str] = Body(default=None),
    email: Optional[str] = Body(default=None),
    role: Optional[str] = Body(default=None),
    is_active: Optional[bool] = Body(default=None),
):
    conn = get_connection()
    cur = conn.cursor()
    updates = []
    values = []

    if full_name is not None:
        updates.append("full_name = %s")
        values.append(full_name)
    if email is not None:
        updates.append("email = %s")
        values.append(email)
    if role is not None:
        updates.append("role = %s")
        values.append(role)
    if is_active is not None:
        updates.append("is_active = %s")
        values.append(is_active)

    if not updates:
        raise HTTPException(status_code=400, detail="No fields provided for update")

    updates.append("updated_at = %s")
    values.append(datetime.now())

    values.append(user_id)

    cur.execute(f"""
        UPDATE marketer_users
        SET {', '.join(updates)}
        WHERE id = %s
    """, tuple(values))

    if cur.rowcount == 0:
        conn.rollback()
        raise HTTPException(status_code=404, detail="User not found")
    conn.commit()
    conn.close()
    return {"message": "User updated successfully"}


@app.delete("/marketer-users/{user_id}", tags=["Marketer"])
def delete_marketer_user(user_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM marketer_users WHERE id = %s", (user_id,))
    if cur.rowcount == 0:
        conn.rollback()
        raise HTTPException(status_code=404, detail="User not found")
    conn.commit()
    conn.close()
    return {"message": "User deleted successfully"}





# ======= Assign marketer to passenger =======

@app.post("/assign-marketer-users/", tags=["Marketer"])
def assign_marketer_users(data: AssignMarketerUser):
    conn = get_connection()
    cur = conn.cursor()
    try:
        for marketer_id in data.marketer_user_ids:
            cur.execute("""
                SELECT 1 FROM passenger_marketer_users 
                WHERE passenger_id = %s AND marketer_user_id = %s
            """, (data.passenger_id, marketer_id))
            if cur.fetchone():
                continue  # ya existe la asignación
            cur.execute("""
                INSERT INTO passenger_marketer_users (
                    passenger_id, marketer_user_id, assigned_at, status, created_by
                ) VALUES (%s, %s, %s, %s, %s)
            """, (data.passenger_id, marketer_id, datetime.now(), 'active', 'system'))
        conn.commit()
        return {"message": "Assignments processed successfully"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@app.get("/passenger/{passenger_id}/marketer-users", response_model=List[MarketerUserRead], tags=["Marketer"])
def get_marketers_for_passenger(passenger_id: int):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT mu.id, mu.username, mu.email, mu.full_name, mu.is_active, mu.role
        FROM marketer_users mu
        JOIN passenger_marketer_users pmu ON pmu.marketer_user_id = mu.id
        WHERE pmu.passenger_id = %s
    """, (passenger_id,))
    users = cur.fetchall()
    conn.close()
    return users


@app.put("/assign-marketer-users/update", summary="Update marketer assignment", tags=["Marketer"])
def update_assignment_status(
    payload: AssignmentUpdateRequest = Body(...)
):
    conn = get_connection()
    cur = conn.cursor()

    # Validar que la asignación original existe
    cur.execute("""
        SELECT id FROM passenger_marketer_users
        WHERE passenger_id = %s AND marketer_user_id = %s
    """, (payload.passenger_id, payload.current_marketer_user_id))
    assignment = cur.fetchone()
    
    if not assignment:
        conn.rollback()
        conn.close()
        raise HTTPException(status_code=404, detail="Asignación original no encontrada")

    # Si se desea reasignar a otro marketer
    if payload.new_marketer_user_id and payload.new_marketer_user_id != payload.current_marketer_user_id:
        # Validar que la nueva relación no exista ya (para evitar duplicados)
        cur.execute("""
            SELECT 1 FROM passenger_marketer_users
            WHERE passenger_id = %s AND marketer_user_id = %s
        """, (payload.passenger_id, payload.new_marketer_user_id))
        if cur.fetchone():
            conn.rollback()
            conn.close()
            raise HTTPException(status_code=400, detail="Ya existe una asignación con ese marketer_user")

        # Actualizar marketer_user_id y demás campos
        cur.execute("""
            UPDATE passenger_marketer_users
            SET marketer_user_id = %s, status = %s, updated_at = %s, updated_by = %s
            WHERE passenger_id = %s AND marketer_user_id = %s
        """, (
            payload.new_marketer_user_id,
            payload.status,
            datetime.now(),
            payload.updated_by,
            payload.passenger_id,
            payload.current_marketer_user_id
        ))
    else:
        # Solo actualizar status y metadatos
        cur.execute("""
            UPDATE passenger_marketer_users
            SET status = %s, updated_at = %s, updated_by = %s
            WHERE passenger_id = %s AND marketer_user_id = %s
        """, (
            payload.status,
            datetime.now(),
            payload.updated_by,
            payload.passenger_id,
            payload.current_marketer_user_id
        ))

    if cur.rowcount == 0:
        conn.rollback()
        conn.close()
        raise HTTPException(status_code=500, detail="No se pudo actualizar la asignación")
    
    conn.commit()
    conn.close()
    return {"message": "Asignación actualizada correctamente"}


@app.delete("/assign-marketer-users/", tags=["Marketer"])
def delete_assignment(passenger_id: int, marketer_user_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        DELETE FROM passenger_marketer_users
        WHERE passenger_id = %s AND marketer_user_id = %s
    """, (passenger_id, marketer_user_id))

    if cur.rowcount == 0:
        conn.rollback()
        raise HTTPException(status_code=404, detail="Assignment not found")
    conn.commit()
    conn.close()
    return {"message": "Assignment deleted successfully"}



@app.get("/incident/by-marketer/{marketer_user_id}", tags=["Marketer"])
def get_incidents_by_marketer(marketer_user_id: int):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        cur.execute("""
            SELECT DISTINCT ir.*
            FROM incident_reports ir
            JOIN vehicles v ON v.incident_report_id = ir.id
            JOIN passengers p ON p.vehicle_id = v.id
            JOIN passenger_marketer_users pmu ON pmu.passenger_id = p.id
            WHERE pmu.marketer_user_id = %s
            ORDER BY ir.accident_datetime DESC
        """, (marketer_user_id,))
        incidents = cur.fetchall()
        return incidents
    finally:
        conn.close()



# ======= Upload Pdfs Ohio =======

UPLOAD_DIR = os.getenv("OHIO_FILE_UPLOAD_PATH")
if not UPLOAD_DIR:
    raise RuntimeError("Falta definir OHIO_FILE_UPLOAD_PATH en el .env")
os.makedirs(UPLOAD_DIR, exist_ok=True)



@app.post("/upload-pdf-ohio", tags=["upload_pdf"])
async def upload_pdf_ohio(file: UploadFile = File(...), response: Response = None):
    # Headers
    if response:
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "font-src 'self' https://assets.ngrok.com; "
            "style-src 'self' 'unsafe-inline'; "
            "script-src 'self';"
        )
    try:
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="El archivo debe ser un PDF")

        # Guardar PDF temporal
        temp_pdf_path = os.path.join(UPLOAD_DIR, "temporal_name_fileUI.pdf")
        with open(temp_pdf_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Extraer datos
        df = extract_traffic_data_from_pdf(temp_pdf_path)

        if df.empty:
            raise HTTPException(status_code=422, detail="No se pudo extraer información del PDF")

        number_report = str(df["Accident Report Number"].iloc[0])
        if not number_report:
            raise HTTPException(status_code=422, detail="No se encontró un número de reporte válido")

        # Renombrar archivo PDF
        final_pdf_name = f"{number_report}.pdf"
        final_pdf_path = os.path.join(UPLOAD_DIR, final_pdf_name)
        os.rename(temp_pdf_path, final_pdf_path)

        # Guardar CSV con mismo nombre base
        csv_filename = f"{number_report}.csv"
        csv_path = os.path.join(UPLOAD_DIR, csv_filename)
        df.to_csv(csv_path, index=False)

        # Insertar en base de datos
        summary = insert_data_from_dataframe(df, UPLOAD_DIR)

        # Guardar en tabla de estatus de carga
        save_result = save_estatus_pdf(
            file_name=file.filename.lower(),
            report_number=number_report,
            number_passagers=len(df),
            status=summary.get("incident_report", "error"),
            agency="ohio",  # puedes parametrizar esto si lo necesitas
            website="ohio",
            state="OH",
            city=None,
            created_by="frontend"
        )


        try:
            trigger_response = trigger_airflow_dag("incident_services_common", conf={"source": "FastAPI", "date": str(datetime.now())})
        except Exception as e:
            pass

        return JSONResponse(status_code=200, content={
            "upload_id": save_result["upload_id"],
            "report_number": save_result["report_number"],
            "status": save_result["status"],
            "message": "rows_extracted -> " + str(len(df))
        })

    except Exception as e:
        # Guardar en tabla de estatus de carga
        save_result = save_estatus_pdf(
            file_name=file.filename.lower(),
            report_number="",
            number_passagers=len(df),
            status="error",
            agency="ohio",  # puedes parametrizar esto si lo necesitas
            website="ohio",
            state="OH",
            city=None,
            created_by="frontend"
        )      

        return JSONResponse(status_code=500, content={
        "upload_id": None,
        "report_number": " ",
        "status": "error",
        "message": str(e)
        })


@app.post("/upload-multiple-pdfs-ohio", tags=["upload_pdf"])
async def upload_multiple_pdfs(files: List[UploadFile] = File(...)):
    results = []

    for file in files:
        try:
            if not file.filename.lower().endswith(".pdf"):

                save_result = save_estatus_pdf(
                    file_name=file.filename.lower(),
                    report_number="",
                    number_passagers=0,
                    status="The file must be a PDF",
                    agency="ohio",
                    website="ohio",
                    state="OH",
                    city=None,
                    created_by="frontend"
                )

                results.append({
                    "upload_id": save_result.get("upload_id"),
                    "report_number": " ",
                    "status": "error",
                    "message": "The file must be a PDF"
                })
                continue

            temp_pdf_path = os.path.join(UPLOAD_DIR, f"temp_{file.filename}")
            with open(temp_pdf_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            # Extraer datos
            df = extract_traffic_data_from_pdf(temp_pdf_path)

            if df.empty:

                save_result = save_estatus_pdf(
                    file_name=file.filename.lower(),
                    report_number=" ",
                    number_passagers=0,
                    status="No data extracted",
                    agency="ohio",
                    website="ohio",
                    state="OH",
                    city=None,
                    created_by="frontend"
                )

                os.remove(temp_pdf_path)
                results.append({
                    "upload_id": save_result.get("upload_id"),
                    "report_number": save_result.get("report_number"),
                    "status": "No data extracted"
                })
                continue

            number_report = str(df["Accident Report Number"].iloc[0])

            if not number_report:

                save_result = save_estatus_pdf(
                    file_name=file.filename.lower(),
                    report_number="",
                    number_passagers=0,
                    status="number report not found in PDF",
                    agency="ohio",
                    website="ohio",
                    state="OH",
                    city=None,
                    created_by="frontend"
                )

                results.append({
                    "upload_id": save_result.get("upload_id"),
                    "report_number": save_result.get("report_number"),
                    "status": "error",
                    "message": "number report not found in PDF"
                })
                os.remove(temp_pdf_path)
                continue

            # Guardar PDF con nombre final
            final_pdf_name = f"{number_report}.pdf"
            final_pdf_path = os.path.join(UPLOAD_DIR, final_pdf_name)
            os.rename(temp_pdf_path, final_pdf_path)

            # Guardar CSV con mismo nombre base
            csv_filename = f"{number_report}.csv"
            csv_path = os.path.join(UPLOAD_DIR, csv_filename)
            df.to_csv(csv_path, index=False)

            # Insertar en base de datos
            summary = insert_data_from_dataframe(df, UPLOAD_DIR)

            save_result = save_estatus_pdf(
                file_name=file.filename.lower(),
                report_number=number_report,
                number_passagers=len(df),
                status=summary.get("incident_report"),
                agency="ohio",
                website="ohio",
                state="OH",
                city=None,
                created_by="frontend"
            )

            results.append({
                "upload_id": save_result.get("upload_id"),
                "report_number": number_report,
                "status": save_result.get("status"),
                "message": "rows count - >" + str(len(df))
            })

        except Exception as e:

            save_result = save_estatus_pdf(
                file_name=file.filename.lower(),
                report_number="",
                number_passagers=0,
                status="error",
                agency="ohio",
                website="ohio",
                state="OH",
                city=None,
                created_by="frontend"
            )
                        
            results.append({
                "upload_id": save_result.get("upload_id"),
                "report_number": save_result.get("report_number"),
                "status": "error",
                "message": f"Error procesando el archivo: {str(e)}"
            })

    try:
        trigger_response = trigger_airflow_dag("incident_services_common", conf={"source": "FastAPI", "date": str(datetime.now())})
    except Exception as e:
        pass

    return JSONResponse(status_code=207, content={"results": results})


@app.get("/report-status", tags=["upload_pdf"])
def get_report_status(report_number: Optional[str] = Query(None, description="Número de reporte a buscar")):
    """
    Endpoint to get the status of uploaded PDF reports.
    If `report_number` is provided, it will return the status of that specific report.
    If not provided, it will return the last 100 records.
    If no records are found, it will return a message indicating that.
    """
    conn = None
    cur = None

    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        if report_number:
            report_number = report_number.strip()
            cur.execute("""
                SELECT * FROM upload_pdf_status
                WHERE TRIM(report_number) = %s
                ORDER BY created_at DESC
            """, (report_number,))
        else:
            cur.execute("""
                SELECT * FROM upload_pdf_status
                ORDER BY created_at DESC
                LIMIT 100
            """)

        records = cur.fetchall()
        return {
            "report_number": report_number or "ALL",
            "records_found": len(records),
            "records": records,
            "message": "Records found." if records else "No records found."
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching records: {str(e)}")

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()



GEORGIA_UPLOAD_DIR = os.getenv("GEORGIA_FILE_UPLOAD_PATH")
if not GEORGIA_UPLOAD_DIR:
    raise RuntimeError("Falta definir GEORGIA_FILE_UPLOAD_PATH en el .env")
os.makedirs(GEORGIA_UPLOAD_DIR, exist_ok=True)
os.makedirs(os.path.join(GEORGIA_UPLOAD_DIR, "processed"), exist_ok=True)

@app.post("/upload-multiple-pdfs-georgia", tags=["upload_pdf"])
async def upload_multiple_pdfs(files: List[UploadFile] = File(...)):
    results = []
    print("/upload-multiple-pdfs-georgia")
    for file in files:
        try:
            if not file.filename.lower().endswith(".pdf"):

                save_result = save_estatus_pdf(
                    file_name=file.filename.lower(),
                    report_number="",
                    number_passagers=0,
                    status="uploaded file does not have a pdf extension",
                    agency="georgia",
                    website="georgia",
                    state="GA",
                    city=None,
                    created_by="frontend"
                )

                results.append({
                    "upload_id": save_result.get("upload_id"),
                    "report_number": " ",
                    "status": "uploaded file does not have a pdf extension",
                    "message": "The file must be a PDF"
                })
                continue

            clean_name = re.sub(r"[^a-zA-Z0-9_.-]", "_", file.filename).lower()
            temp_pdf_path = os.path.join(GEORGIA_UPLOAD_DIR, f"temp_{clean_name}")

            if os.path.exists(temp_pdf_path):
                os.remove(temp_pdf_path)
                
            with open(temp_pdf_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            # Extraer datos
            df = extract_df_from_georgia(temp_pdf_path)

            if df.empty:

                save_result = save_estatus_pdf(
                    file_name=file.filename.lower(),
                    report_number="",
                    number_passagers=0,
                    status="Information could not be extracted from the PDF.",
                    agency="georgia",
                    website="georgia",
                    state="GA",
                    city=None,
                    created_by="frontend"
                )

                os.remove(temp_pdf_path)
                results.append({
                    "upload_id": save_result.get("upload_id"),
                    "report_number": save_result.get("report_number"),
                    "status": "No data extracted"
                })
                continue

            number_report = str(df["agency_case_number"].iloc[0])

            if not number_report:

                save_result = save_estatus_pdf(
                    file_name=file.filename.lower(),
                    report_number="",
                    number_passagers=0,
                    status="The extracted report number is not valid.",
                    agency="georgia",
                    website="georgia",
                    state="GA",
                    city=None,
                    created_by="frontend"
                )

                results.append({
                    "upload_id": save_result.get("upload_id"),
                    "report_number": save_result.get("report_number"),
                    "status": "No data extracted",
                    "message": "number report not found in PDF"
                })
                os.remove(temp_pdf_path)
                continue

            # Guardar PDF con nombre final
            final_pdf_name = f"{number_report}.pdf"
            final_pdf_path = os.path.join(GEORGIA_UPLOAD_DIR, final_pdf_name)
            os.rename(temp_pdf_path, final_pdf_path)

            # Guardar CSV con mismo nombre base
            csv_filename = f"{number_report}.csv"
            csv_path = os.path.join(GEORGIA_UPLOAD_DIR, csv_filename)
            df.to_csv(csv_path, index=False)

            # Insertar en base de datos
            summary = loader_df_to_db(df, GEORGIA_UPLOAD_DIR)
            incident_status = "saved" if summary else "Error inserting into the database "

            save_result = save_estatus_pdf(
                file_name=file.filename.lower(),
                report_number=number_report,
                number_passagers=len(df),
                status=incident_status,
                agency="georgia",
                website="georgia",
                state="GA",
                city=None,
                created_by="frontend"
            )

            results.append({
                "upload_id": save_result.get("upload_id"),
                "report_number": save_result.get("report_number"),
                "status": "successful",
                "message": len(df)
            })

        except Exception as e:

            save_result = save_estatus_pdf(
                file_name=file.filename.lower(),
                report_number="",
                number_passagers=0,
                status="error",
                agency="georgia",
                website="georgia",
                state="GA",
                city=None,
                created_by="frontend"
            )
                        
            results.append({
                "upload_id": save_result.get("upload_id"),
                "report_number": save_result.get("report_number"),
                "status": "error",
                "message": f"Error processing file: {str(e)}"
            })

    try:
        trigger_response = trigger_airflow_dag("incident_services_common", conf={"source": "FastAPI", "date": str(datetime.now())})
    except Exception as e:
        pass

    return JSONResponse(status_code=207, content={"results": results})




# Ruta de destino donde se guardarán los archivos subidos
UPLOAD_DIR_NC = os.getenv("NC_FILE_UPLOAD_PATH")
PROCESSED_DIR_NC = os.getenv("NC_PROCESSED_PATH")

# Asegúrate de que el directorio exista
os.makedirs(UPLOAD_DIR_NC, exist_ok=True)
os.makedirs(PROCESSED_DIR_NC, exist_ok=True)

@app.post("/upload-multiple-xml-nc", tags=["upload_pdf"])
async def upload_xml(files: List[UploadFile] = File(...)):
    results = []
    for file in files:
        try:
            # Verificar que sea un archivo Excel
            if not file.filename.lower().endswith((".xlsx", ".xls")):
                save_result = save_estatus_pdf(
                    file_name=file.filename.lower(),
                    report_number="",
                    number_passagers=0,
                    status="uploaded file does not have a .xlsx or .xls extension",
                    agency="NorthCarolina",
                    website="northcarolina",
                    state="NC",
                    city=None,
                    created_by="frontend"
                )
                
                results.append({
                    "upload_id": save_result.get("upload_id"),
                    "report_number": " ",
                    "status": "uploaded file does not have a pdf extension",
                    "message": "The file must be a PDF"
                })
                continue

            # Limpiar el nombre del archivo y asegurarse de que sea único
            clean_name = re.sub(r"[^a-zA-Z0-9_.-]", "_", file.filename).lower()
            excel_path = os.path.join(UPLOAD_DIR_NC, clean_name)

            # Guardar el archivo Excel en la ruta especificada
            with open(excel_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            # Verificar que el archivo fue guardado correctamente
            if not os.path.isfile(excel_path):
                raise HTTPException(status_code=500, detail="Error al guardar el archivo Excel.")

            # Procesar el archivo
            download_pdfs_from_excel(excel_path, PROCESSED_DIR_NC)

            # Leer el archivo Excel en un DataFrame
            df = pd.read_excel(excel_path)

            if df.empty:
                raise HTTPException(status_code=422, detail="El archivo Excel está vacío o no contiene datos válidos.")

            # Obtener el nombre del archivo (sin la extensión)
            csv_name = Path(excel_path).stem

            # Convertir a CSV y guardar el archivo CSV procesado
            csv_path = convert_df_to_csv(df, PROCESSED_DIR_NC, csv_name)

            # Cargar los datos en la base de datos
            summary=loader_df_to_db(df, path_pdf_folder=PROCESSED_DIR_NC)
            incident_status = "saved" if summary else "Error inserting into the database "

            # Obtener el número de reporte del archivo Excel
            number_report = str(df.iloc[0]["ReportNumber"])
            if not number_report:
                raise HTTPException(status_code=422, detail="A valid report number could not be found in the Excel file.")

            # Guardar el estado del archivo procesado
            save_result = save_estatus_pdf(
                file_name=clean_name,
                report_number=number_report,
                number_passagers=len(df),
                status=incident_status,
                agency="northcarolina",
                website="northcarolina",
                state="NC",
                city=None,
                created_by="frontend"
            )

            results.append({
                "upload_id": save_result.get("upload_id"),
                "report_number": save_result.get("report_number"),
                "status": "success",
                "message": f"Se procesaron {len(df)} registros y se guardó el archivo CSV en: {csv_path}"
            })

        except Exception as e:
            # En caso de error, registrar el estado del error
            save_result = save_estatus_pdf(
                file_name=clean_name,
                report_number="",
                number_passagers=0,
                status="error",
                agency="northcarolina",
                website="northcarolina",
                state="NC",
                city=None,
                created_by="frontend"
            )

            results.append({
                "upload_id": save_result.get("upload_id"),
                "report_number": save_result.get("report_number"),
                "status": "error",
                "message": f"Error procesando el archivo {clean_name}: {str(e)}"
            })
            
    try:
        trigger_response = trigger_airflow_dag("incident_services_common", conf={"source": "FastAPI", "date": str(datetime.now())})
    except Exception as e:
        pass

    return {"results": results}





OHIO_DIR_XLSX = os.getenv("OHIO_XLSX_PATH")
if not OHIO_DIR_XLSX:
    raise RuntimeError("Dont Define OHIO_XLSX_PATH in the .env")
os.makedirs(OHIO_DIR_XLSX, exist_ok=True)


@app.post("/upload-multiple-xlsx-ohio", tags=["upload_xlsx"])
async def upload_multiple_xlsx_ohio(files: list[UploadFile] = File(...)):
    results = []

    for file in files:
        try:
            if not file.filename.lower().endswith(".xlsx"):
                save_result = save_estatus_pdf(
                    file_name=file.filename.lower(),
                    report_number="",
                    number_passagers=0,
                    status="uploaded file does not have an xlsx extension",
                    agency="ohio",
                    website="",
                    state="OH",
                    city=None,
                    created_by="frontend"
                )
                results.append({
                    "upload_id": save_result.get("upload_id"),
                    "report_number": " ",
                    "status": "invalid_extension",
                    "message": "The file must be a .xlsx file"
                })
                continue

            clean_name = re.sub(r"[^a-zA-Z0-9_.-]", "_", file.filename).lower()
            temp_xlsx_path = os.path.join(OHIO_DIR_XLSX, f"temp_{clean_name}")

            if os.path.exists(temp_xlsx_path):
                os.remove(temp_xlsx_path)

            with open(temp_xlsx_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            # Leer y procesar DataFrame
            df = pd.read_excel(temp_xlsx_path)

            if df.empty:
                save_result = save_estatus_pdf(
                    file_name=file.filename.lower(),
                    report_number="",
                    number_passagers=0,
                    status="xlsx file is empty",
                    agency="ohio",
                    website="ohio",
                    state="OH",
                    city=None,
                    created_by="frontend"
                )
                os.remove(temp_xlsx_path)
                results.append({
                    "upload_id": save_result.get("upload_id"),
                    "report_number": "",
                    "status": "Excel empty",
                    "message": "Empty xlsx file"
                })
                continue

            insert_ok = load_ohio_data(df, temp_xlsx_path)
            status = "saved" if insert_ok else "error_inserting"

            # Guardar CSV con mismo nombre base
            csv_filename = f"{Path(temp_xlsx_path).stem}.csv"
            csv_path = os.path.join(OHIO_DIR_XLSX, csv_filename)
            df.to_csv(csv_path, index=False)

            save_result = save_estatus_pdf(
                file_name=file.filename.lower(),
                report_number="several reports",
                number_passagers=len(df),
                status=status,
                agency="ohio",
                website="",
                state="OH",
                city=None,
                created_by="frontend"
            )

            results.append({
                "upload_id": save_result.get("upload_id"),
                "report_number": save_result.get("report_number"),
                "status": status,
                "message": f"{len(df)} rows processed"
            })

        except Exception as e:
            save_result = save_estatus_pdf(
                file_name=file.filename.lower(),
                report_number="",
                number_passagers=0,
                status="error",
                agency="ohio",
                website="",
                state="OH",
                city=None,
                created_by="frontend"
            )

            results.append({
                "upload_id": save_result.get("upload_id"),
                "report_number": "",
                "status": "error",
                "message": f"Error: {str(e)}"
            })

        finally:
            if os.path.exists(temp_xlsx_path):
                os.remove(temp_xlsx_path)

    try:
        trigger_response = trigger_airflow_dag("incident_services_common", conf={"source": "FastAPI", "date": str(datetime.now())})
    except Exception as e:
        pass
    
    return JSONResponse(status_code=207, content={"results": results})


# @app.websocket("/ws/notifications")
# async def websocket_notifications(websocket: WebSocket):
#     await websocket.accept()
#     connected_clients.append(websocket)
#     try:
#         while True:
#             await websocket.receive_text()  # Mantiene la conexión activa
#     except WebSocketDisconnect:
#         connected_clients.remove(websocket)

