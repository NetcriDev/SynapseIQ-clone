import os
from datetime import datetime

def extract_metadata(file_bytes: bytes, filename: str, source: str) -> dict:
    size = len(file_bytes)
    file_extension = os.path.splitext(filename)[1].lower()
    return {
        "filename": filename,
        "extension": file_extension,
        "size_bytes": size,
        "source": source,
        "timestamp": datetime
    }
