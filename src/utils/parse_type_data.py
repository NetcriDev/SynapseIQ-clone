from typing import Any, Optional
from datetime import datetime

# Lista de entradas consideradas como "nulas"
INVALID_ENTRIES = {"", " ", "-", ".", ",", "n/a", "null", "none", "unknown"}

def parse_int(value: Any) -> Optional[int]:
    """
    Intenta convertir el valor a entero.
    Retorna None si es un valor inválido o no convertible.
    """
    if value is None:
        return None

    str_value = str(value).strip().lower()

    if str_value in INVALID_ENTRIES:
        return None

    try:
        return int(float(str_value))
    except (ValueError, TypeError):
        return None

def parse_float(value: Any) -> Optional[float]:
    """
    Intenta convertir el valor a flotante (decimal).
    Retorna None si es un valor inválido o no convertible.
    """
    if value is None:
        return None

    str_value = str(value).strip().lower()

    if str_value in INVALID_ENTRIES:
        return None

    try:
        return float(str_value)
    except (ValueError, TypeError):
        return None

def parse_str(value: Any) -> Optional[str]:
    """
    Limpia y convierte cualquier entrada a string, o None si es inválido.
    """
    if value is None:
        return None

    str_value = str(value).strip()

    if str_value.lower() in INVALID_ENTRIES:
        return None

    return str_value

def parse_date(value: Any, date_formats: Optional[list[str]] = None) -> Optional[datetime]:
    """
    Intenta convertir el valor a objeto datetime.
    date_formats: Lista de formatos posibles de fecha para intentar parsear.
    """
    if value is None:
        return None

    str_value = str(value).strip()

    if str_value.lower() in INVALID_ENTRIES:
        return None

    # Formatos comunes si no se especifican
    if date_formats is None:
        date_formats = [
            "%Y-%m-%d",    # 2025-04-26
            "%d/%m/%Y",    # 26/04/2025
            "%d-%m-%Y",    # 26-04-2025
            "%m/%d/%Y",    # 04/26/2025
            "%d/%m/%y",    # 26/04/25
        ]

    for fmt in date_formats:
        try:
            return datetime.strptime(str_value, fmt)
        except ValueError:
            continue

    return None
