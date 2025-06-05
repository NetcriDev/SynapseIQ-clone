from datetime import datetime

def parse_date(date_str: str) -> datetime:
    """Parses a date string in the format YYYY-MM-DD."""
    try:
        date_str = date_str.strip('"').strip("'")
        return datetime.strptime(date_str, "%Y-%m-%d")
    except Exception:
        print(date_str)
        raise ValueError(f"Fecha inválida: {date_str}. Formato esperado: YYYY-MM-DD")