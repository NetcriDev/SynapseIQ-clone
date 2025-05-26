import psycopg2
from datetime import datetime, timedelta
from config.config import get_connection

def is_invalid_string(value: str) -> bool:
    """Valida si un string es considerado nulo o inválido."""
    if not isinstance(value, str):
        return True
    normalized = value.strip().lower()
    return normalized in {"", "n/a", "null", "none", "unknown", "unk", " , ", ",", "na"}

def is_qualified_hot_lead(
    hasinsurance_details: str,
    hasphone: str,
    nearest_center_d: float,
    accident_datetime: datetime,
    injury_severity: str
) -> str:
    """
    Evaluates whether a passenger qualifies as a hot lead based on the defined criteria.

    Parameters:
    - hasinsurance_details: str ("True"/"False" or variants)
    - hasphone: str ("True"/"False" or variants)
    - nearest_center_d: float (distance in miles to the nearest center)
    - accident_datetime: datetime (date and time of the accident)
    - injury_severity: str (description of the injury severity)

    Returns: "True" or "False"
    """

    try:
        # Validar seguro
        has_insurance = not is_invalid_string(hasinsurance_details) and hasinsurance_details.strip().lower() == "true"

        # Validar teléfono
        has_phone = not is_invalid_string(hasphone) and hasphone.strip().lower() == "true"

        # Validar distancia
        within_distance = nearest_center_d is not None and nearest_center_d <= 20

        # Validar fecha de accidente
        recent_accident = isinstance(accident_datetime, datetime) and \
                          (datetime.utcnow() - accident_datetime) <= timedelta(hours=48)

        # Validar severidad crítica
        is_critical = not is_invalid_string(injury_severity) and "critical" in injury_severity.strip().lower()

        all_conditions = all([
            has_insurance,
            has_phone,
            within_distance,
            recent_accident,
            is_critical
        ])

        return "True" if all_conditions else "False"

    except Exception as e:
        print(f"Error en evaluación de hot lead: {e}")
        return "False"


def update_hotlead_flags():
    conn = get_connection()
    cur = conn.cursor()

    # Obtener información de pasajeros con datos del incidente
    cur.execute("""
        SELECT 
            p.id AS passenger_id,
            p.hasinsurance_details,
            p.hasphone,
            p.injury_severity,
            ir.accident_datetime,
            ir.nearest_center_d
        FROM passengers p
        JOIN vehicles v ON p.vehicle_id = v.id
        JOIN incident_reports ir ON v.incident_report_id = ir.id
        WHERE ir.state IS DISTINCT FROM 'Texas'
        AND (p.hotlead IS NULL OR TRIM(p.hotlead) = '')
        LIMIT 200;
    """)

    passengers = cur.fetchall()

    for row in passengers:
        passenger_id, hasinsurance_details, hasphone, injury_severity, accident_datetime, nearest_center_d = row

        flag = is_qualified_hot_lead(
            hasinsurance_details,
            hasphone,
            nearest_center_d,
            accident_datetime,
            injury_severity
        )

        # Actualizar valor en la base de datos
        cur.execute("""
            UPDATE passengers
            SET hotlead = %s
            WHERE id = %s
        """, (flag, passenger_id))

    conn.commit()
    cur.close()
    conn.close()
