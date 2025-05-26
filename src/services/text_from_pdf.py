import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))  # Ajusta según nivel
os.chdir(PROJECT_ROOT)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from typing import Union
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Optional
from io import BytesIO
from huggingface_hub import snapshot_download
from docling.datamodel.pipeline_options import PdfPipelineOptions, RapidOcrOptions
from docling.document_converter import (
    ConversionResult,
    DocumentConverter,
    InputFormat,
    PdfFormatOption,
)
from config.config import get_connection
from src.utils.logger_config import setup_logger

main_script_path = sys.path[0]
logger = setup_logger("Texto_from_pdf", main_script_path)

def save_to_postgres(report_number: str, state: str, extracted_text: str):
    """
    Guarda el texto extraído en la columna text_from_pdf de la tabla incident_reports.
    """
    try:
        conn = get_connection()
        cur = conn.cursor()

        # Update del texto OCR
        cur.execute("""
            UPDATE incident_reports
            SET text_from_pdf = %s
            WHERE report_number = %s AND state = %s
            
        """, (extracted_text, report_number, state))

        conn.commit()
        cur.close()
        conn.close()
        logger.info("Texto guardado exitosamente en la base de datos.")
        
    except Exception as e:
        logger.error("Error guardando en la base de datos:", e)


class PdfProcessor:
    def __init__(self, local_model_path: Union[str, Path] = "/home/ocr_models"):
        """
        Inicializa el procesador de PDFs OCR. Si no se encuentra el path a los modelos
        localmente, los descargará desde HuggingFace.

        Parámetros:
        - local_model_path (str | Path): Ruta base donde se encuentran los modelos. Si no se pasa o están incompletos, se descargan automáticamente.

        Excepciones:
        - FileNotFoundError si los modelos requeridos no están ni pueden descargarse.
        - Exception si ocurre un error inesperado en la inicialización del convertidor.
        """
        try:
            # Ruta del directorio
            ocr_models_path = Path(local_model_path)
            ocr_models_path.mkdir(parents=True, exist_ok=True)
            # Verifica existencia o descarga
            self.model_base_path = self._download_models(Path(local_model_path) if local_model_path else None)
            self.converter = self._initialize_converter()
        except Exception as e:
            raise RuntimeError(f"Error inicializando PdfProcessor: {e}") from e

    def _download_models(self, candidate_path: Path = None) -> Path:
        """
        Verifica si los modelos OCR existen localmente en `candidate_path`, y si no, los descarga.

        Parámetros:
        - candidate_path (Path | None): Ruta donde se esperan los modelos. Si es None o están incompletos, se descargan.

        Retorna:
        - Path a la carpeta base que contiene los modelos OCR.

        Excepciones:
        - FileNotFoundError si tras la descarga no se encuentran los modelos requeridos.
        """
        def model_files_exist(base_path: Path) -> bool:
            return all([
                (base_path / "PP-OCRv4" / "en_PP-OCRv3_det_infer.onnx").exists(),
                (base_path / "PP-OCRv4" / "ch_PP-OCRv4_rec_server_infer.onnx").exists(),
                (base_path / "PP-OCRv3" / "ch_ppocr_mobile_v2.0_cls_train.onnx").exists(),
            ])

        # Verificar modelos locales si se proporcionó una ruta
        if candidate_path and model_files_exist(candidate_path):
            print(f"Usando modelos locales en: {candidate_path}")
            return candidate_path

        # Descargar desde HuggingFace si no están presentes
        print("Modelos locales no encontrados o incompletos. Descargando desde HuggingFace...")
        try:
            downloaded_path = Path(snapshot_download(repo_id="SWHL/RapidOCR", local_dir=candidate_path, local_dir_use_symlinks=False))
        except Exception as e:
            raise RuntimeError("Error descargando modelos desde HuggingFace") from e

        # Verificar que la descarga fue exitosa
        if not model_files_exist(downloaded_path):
            raise FileNotFoundError("Los modelos OCR descargados están incompletos o corruptos.")

        return downloaded_path

    def _initialize_converter(self) -> DocumentConverter:
        """Inicializa y configura los modelos OCR para la conversión."""
        det_model_path = self.model_base_path / "PP-OCRv4" / "en_PP-OCRv3_det_infer.onnx"
        rec_model_path = self.model_base_path / "PP-OCRv4" / "ch_PP-OCRv4_rec_server_infer.onnx"
        cls_model_path = self.model_base_path / "PP-OCRv3" / "ch_ppocr_mobile_v2.0_cls_train.onnx"

        for path in [det_model_path, rec_model_path, cls_model_path]:
            if not path.exists():
                raise FileNotFoundError(f"Modelo faltante: {path}")

        ocr_options = RapidOcrOptions(
            det_model_path=str(det_model_path),
            rec_model_path=str(rec_model_path),
            cls_model_path=str(cls_model_path),
        )

        pipeline_options = PdfPipelineOptions(ocr_options=ocr_options)

        return DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options),
            }
        )

    def process_pdf_from_path(self, report_number: str, state: str, file_path: Union[str, Path], narrative: str) -> str:
        """Procesa un PDF desde una ruta local."""
        print(f"Procesando archivo local: {file_path}")
        return self._convert_and_store(report_number, state, str(file_path), narrative)

    def process_pdf_from_ibm_cos(self, stream: BytesIO, report_number: str) -> Optional[str]:
        """
        Procesa un PDF recibido como stream BytesIO desde IBM COS.
        Guarda el archivo en disco temporalmente y aplica OCR.

        Parámetros:
        - stream: objeto BytesIO que representa el PDF.
        - report_number: número de reporte para asociar en BD.

        Retorna:
        - Texto extraído del PDF (en markdown), o None si hubo error.

        example:
            cos = IBMCOSManager()
            stream = cos.get_object_stream(bucket="pdfs", key="2025/report.pdf")

            processor = PdfProcessor()
            markdown = processor.process_pdf_from_ibm_cos(stream, report_number="2515892")
        """
        try:
            with NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
                tmp_file.write(stream.read())
                tmp_path = tmp_file.name

            return self._convert_and_store(tmp_path, report_number)

        except Exception as e:
            print(f"Error procesando PDF desde stream IBM COS: {e}")
            return None

    def process_pdf_from_api_upload(self, uploaded_file, report_number: str) -> str:
        """Procesa un PDF desde un objeto tipo UploadFile (FastAPI, etc)."""
        with NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            content = uploaded_file.file.read()
            tmp.write(content)
            tmp_path = tmp.name

        print(f"Procesando archivo subido vía API: {tmp_path}")
        return self._convert_and_store(tmp_path, report_number)

    def _convert_and_store(self, report_number: str, state: str ,source_path: str, narrative: str) -> str:
        """Convierte el PDF a texto y lo guarda en la base de datos."""
        try:
            result: ConversionResult = self.converter.convert(source=source_path)
            markdown = result.document.export_to_markdown()
            save_to_postgres(report_number, state, str(markdown) + "\n\n" + narrative)
            return markdown
        except Exception as e:
            print(f"Error al procesar el PDF: {e}")
            raise
