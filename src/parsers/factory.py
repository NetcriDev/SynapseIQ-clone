from .pdf_parser import PdfParser
from .excel_parser import ExcelParser
from .image_parser import ImageParser
from .base import BaseProcessor

def get_processor(file_extension: str) -> BaseProcessor:
    match file_extension.lower():
        case ".pdf":
            return PdfParser()
        case ".xls" | ".xlsx":
            return ExcelParser()
        case ".png" | ".jpg":
            return ImageParser()
        case _:
            raise ValueError(f"No processor found for: {file_extension}")

