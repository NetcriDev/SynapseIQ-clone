
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import psycopg2
import psycopg2.extras
from datetime import datetime
from dotenv import load_dotenv
from pathlib import Path

# Ya tienes esta clase definida:
# from tu_modulo.watson_handler import WatsonXModelHandler

# Ruta absoluta o relativa al archivo .env
dotenv_path = Path("/Users/cristianb/Documents/Python/rel8ed/SynapseIQ_staging/.env")

# Instancia global (reutilizable)
watson_handler = WatsonXModelHandler(
    api_key="TU_API_KEY",
    project_id="TU_PROJECT_ID",
    url="https://us-south.ml.cloud.ibm.com",
    default_model_id="meta-llama/llama-3-2-11b-vision-instruct"
)

# Conexión a DB
def get_db_conn():
    return psycopg2.connect(
        dbname="crash_records_001",
        user="synapseiq",
        password="SynapseIQ$2025",
        host="localhost",
        port="5432"
    )

# FastAPI
app = FastAPI()

# Pydantic models
class ChatRequest(BaseModel):
    report_number: str
    question: str
    text_content: str
    model_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    session_id: int

class MessageRecord(BaseModel):
    role: str
    content: str
    created_at: datetime

# Endpoint principal de chat
@app.post("/chat", response_model=ChatResponse)
async def chat_with_model(request: ChatRequest):
    conn = get_db_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Buscar sesión activa o crear una nueva
    cur.execute("""
        SELECT * FROM chat_session 
        WHERE report_number = %s AND status = 'active'
        ORDER BY started_at DESC LIMIT 1
    """, (request.report_number,))
    session = cur.fetchone()

    if not session:
        cur.execute("""
            INSERT INTO chat_session (report_number, status, model_id, text_from_pdf) 
            VALUES (%s, 'active', %s, %s) RETURNING id
        """, (request.report_number, request.model_id or watson_handler.default_model_id, request.text_content))
        session_id = cur.fetchone()["id"]
        conn.commit()
    else:
        session_id = session["id"]

    # Cargar historial
    cur.execute("""
        SELECT role, content, created_at 
        FROM chat_messages 
        WHERE session_id = %s
        ORDER BY created_at ASC
    """, (session_id,))
    history = cur.fetchall()

    # Guardar pregunta
    cur.execute("""
        INSERT INTO chat_messages (report_number, session_id, role, content) 
        VALUES (%s, %s, 'user', %s)
    """, (request.report_number, session_id, request.question))
    conn.commit()

    # Enviar a modelo
    try:
        result = await watson_handler.query(
            question=request.question,
            text_content=request.text_content,
            model_id=request.model_id
        )
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    # Guardar respuesta
    cur.execute("""
        INSERT INTO chat_messages (report_number, session_id, role, content) 
        VALUES (%s, %s, 'assistant', %s)
    """, (request.report_number, session_id, result["response"]))
    conn.commit()
    conn.close()

    return ChatResponse(response=result["response"], session_id=session_id)













##############################################################








@app.post("/chat", response_model=List[ChatMessage])
def chat_endpoint(data: ChatRequest):
    try:
        conn = db()
        with conn.cursor() as cur:
            # Buscar o crear sesión activa
            cur.execute("""
                SELECT id, text_from_pdf FROM chat_session
                WHERE report_number = %s AND status = 'active'
                ORDER BY started_at DESC LIMIT 1
            """, (data.report_number,))
            session = cur.fetchone()

            if session:
                session_id, text_from_pdf = session
            else:
                # Buscar texto original en incident_reports
                cur.execute("""
                    SELECT text_from_pdf FROM incident_reports WHERE report_number = %s
                """, (data.report_number,))
                res = cur.fetchone()
                if not res or not res[0]:
                    raise HTTPException(status_code=404, detail="Reporte sin texto.")
                text_from_pdf = res[0]
                cur.execute("""
                    INSERT INTO chat_session (report_number, text_from_pdf)
                    VALUES (%s, %s) RETURNING id
                """, (data.report_number, text_from_pdf))
                session_id = cur.fetchone()[0]

            now = datetime.utcnow()

            # Si la pregunta es "__init__", solo devuelve historial o saludo
            if data.question.strip() == "__init__":
                cur.execute("""
                    SELECT role, content, created_at
                    FROM chat_messages
                    WHERE session_id = %s
                    ORDER BY created_at ASC
                """, (session_id,))
                rows = cur.fetchall()
                if not rows:
                    return [
                        ChatMessage(
                            role="assistant",
                            message=f"Bienvenido. Este es el reporte {data.report_number}. Puedes preguntarme lo que necesites sobre el accidente.",
                            timestamp=now
                        )
                    ]
                return [
                    ChatMessage(role=row[0], message=row[1], timestamp=row[2]) for row in rows
                ]

            # Si es pregunta real: guardar y generar respuesta
            cur.execute("""
                INSERT INTO chat_messages (report_number, session_id, role, content, created_at)
                VALUES (%s, %s, 'user', %s, %s)
            """, (data.report_number, session_id, data.question, now))

            prompt = f"""
You are an expert in interpreting traffic accident reports.

Here is the report:

{text_from_pdf}

Now answer this question clearly:

{data.question}
"""

            response = model.generate(prompt=prompt)
            answer = response["results"][0]["generated_text"]

            cur.execute("""
                INSERT INTO chat_messages (report_number, session_id, role, content, created_at)
                VALUES (%s, %s, 'assistant', %s, %s)
            """, (data.report_number, session_id, answer, now))

            # Actualizar sesión
            cur.execute("""
                UPDATE chat_session
                SET message_count = message_count + 2, last_interaction = %s
                WHERE id = %s
            """, (now, session_id))

            # Retornar historial actualizado
            cur.execute("""
                SELECT role, content, created_at
                FROM chat_messages
                WHERE session_id = %s
                ORDER BY created_at ASC
            """, (session_id,))
            rows = cur.fetchall()

        conn.commit()
        return [
            ChatMessage(role=row[0], message=row[1], timestamp=row[2]) for row in rows
        ]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        if conn:
            conn.close()
