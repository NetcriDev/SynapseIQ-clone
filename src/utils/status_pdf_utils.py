from config.config import get_connection
from datetime import datetime

def save_estatus_pdf(report_number, agency, 
                     file_name = None, number_passagers = None,
                     status = None, website = None,
                     state = None, city=None, created_by="frontend") -> dict:
    """
    Saves the status of a PDF report in the database.
    Args:
        report_number (str): The report number.
        agency (str): The agency associated with the report.
        file_name (str, optional): The name of the file. Defaults to None.
        number_passagers (int, optional): The number of passengers. Defaults to None.
        status (str, obligatory): only three opcions: error, processed, pending.
        website (str, optional): The website associated with the report. Defaults to None.
        state (str, opctional): The state associated with the report. Defaults to None.
        city (str, optional): The city associated with the report. Defaults to None.
        created_by (str, optional): The user who created the record. Defaults to "frontend".
    Returns:
        dict: A dictionary containing the:
        upload_id, 
        report_number,
        status,
        message
    """
    conn = None
    cur = None

    try:
        conn = get_connection()
        cur = conn.cursor()

        # Insertar nuevo registro
        cur.execute("""
            INSERT INTO upload_pdf_status (
                file_name, agency, report_number, website, state, city,
                number_passagers, status, created_at, created_by
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            file_name,
            agency,
            report_number,
            website,
            state,
            city,
            number_passagers,
            status,
            datetime.now(),
            created_by
        ))
        upload_id = cur.fetchone()[0]
        conn.commit()

        return {
            "upload_id": upload_id,
            "report_number": report_number,
            "status": status,
            "message": f"Report {report_number} successfully processed as {status}."
        }

    except Exception as e:
        if conn:
            conn.rollback()
        return {
            "upload_id": None,
            "report_number": report_number,
            "status": str(e),
            "message": str(e)
        }

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()
