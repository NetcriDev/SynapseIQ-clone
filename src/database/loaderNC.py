

import os
import pandas as pd
import psycopg2
import logging
from datetime import datetime
from typing import Optional, List
from urllib.parse import urlparse
from src.utils.status_pdf_utils import save_estatus_pdf
import re

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Config:
    """Configuración de base de datos"""
    DB_NAME = os.getenv('DB_NAME', 'crash_records_001')
    DB_USER = os.getenv('DB_USER', 'synapseiq')
    DB_PASSWORD = os.getenv('DB_PASSWORD', 'SynapseIQ$2025')
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = os.getenv('DB_PORT', '5432')

class DataProcessor:
    """Procesa y normaliza datos para la base de datos"""
    
    @staticmethod
    def extract_city_from_address(address: str) -> Optional[str]:
        """Extrae la ciudad de una dirección"""
        if not isinstance(address, str):
            return None
        parts = [part.strip() for part in address.split(",")]
        if len(parts) >= 2:
            return parts[1] if len(parts) >= 2 else parts[0]
        return None

    @staticmethod
    def extract_year(date_str: str) -> Optional[int]:
        """Extrae el año de una fecha"""
        try:
            if not isinstance(date_str, str):
                return None
            cleaned = date_str.strip().lower()
            if cleaned in ("null", "n/a", "none", ""):
                return None
            # Intentar diferentes formatos de fecha (NC usa DD/M/YYYY HH:MM)
            for fmt in ["%d/%m/%Y %H:%M", "%m/%d/%Y %H:%M", "%Y-%m-%d %H:%M", "%d/%m/%Y", "%m/%d/%Y", "%Y-%m-%d"]:
                try:
                    return datetime.strptime(cleaned, fmt).year
                except ValueError:
                    continue
            return None
        except (ValueError, TypeError):
            return None

    @staticmethod
    def clean_str(value) -> Optional[str]:
        """Limpia strings"""
        if pd.isna(value) or str(value).strip().lower() in {"null", "", "none", "n/a"}:
            return None
        return str(value).strip()

    @staticmethod
    def to_int(value) -> Optional[int]:
        """Convierte a entero"""
        try:
            if isinstance(value, str) and value.strip().lower() in ("n/a", "na", "none", ""):
                return None
            return int(float(value))
        except (ValueError, TypeError):
            return None

    @staticmethod
    def to_datetime(value):
        """Convierte a datetime - adaptado para formato NC"""
        try:
            if pd.isna(value):
                return None
            
            # NC format: "14/5/2025 18:23"
            date_str = str(value).strip()
            
            # Intentar diferentes formatos
            formats = [
                "%d/%m/%Y %H:%M",  # Formato principal NC
                "%m/%d/%Y %H:%M",  # Formato alternativo
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d %H:%M",
                "%Y-%m-%d"
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue
            
            # Si ninguno funciona, intentar pandas
            return pd.to_datetime(value)
        except:
            return None

    @staticmethod
    def extract_pdf_filename(pdf_url: str) -> Optional[str]:
        """Extrae el nombre del archivo PDF de la URL"""
        if not isinstance(pdf_url, str):
            return None
        try:
            # Extraer el nombre del archivo de la URL
            parsed_url = urlparse(pdf_url)
            filename = os.path.basename(parsed_url.path)
            # Remover la extensión .pdf
            if filename.endswith('.pdf'):
                filename = filename[:-4]
            return filename
        except:
            return None

class DatabaseManager:
    """Maneja las operaciones de base de datos para reportes de North Carolina"""
    
    def __init__(self):
        self.config = Config()
        logger.info("DatabaseManager inicializado para North Carolina (Forsyth County)")
    
    def get_connection(self):
        """Obtiene conexión a la base de datos"""
        try:
            conn = psycopg2.connect(
                dbname=self.config.DB_NAME,
                user=self.config.DB_USER,
                password=self.config.DB_PASSWORD,
                host=self.config.DB_HOST,
                port=self.config.DB_PORT
            )
            return conn
        except Exception as e:
            logger.error(f"Error conectando a la base de datos: {e}")
            raise

    def insert_dataframe_to_database(self, df: pd.DataFrame, path_pdf_folder: Optional[str] = None) -> bool:
        """
        Inserta DataFrame en la base de datos
        
        Args:
            df: DataFrame con los datos procesados
            path_pdf_folder: Ruta a la carpeta donde se encuentran los PDFs (opcional)

        Returns:
            bool: True si la inserción fue exitosa
        """
        logger.info(f"Insertando {len(df)} registros en la base de datos")
        
        if df.empty:
            logger.warning("DataFrame está vacío")
            return False
        
        conn = self.get_connection()
        cur = conn.cursor()
        
        try:
            # Agrupar por reporte para evitar duplicados
            for report_group in df.groupby('ReportNumber'):
                report_number, group_df = report_group
                
                if pd.isna(report_number) or report_number is None:
                    logger.warning("Registro sin número de caso, omitiendo")
                    continue
                
                logger.info(f"Procesando reporte: {report_number}")
                
                # Procesar cada fila del grupo
                for _, row in group_df.iterrows():
                    self._insert_single_record(cur, row, path_pdf_folder=path_pdf_folder)
            
            conn.commit()
            logger.info("Datos insertados exitosamente")
            return True
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Error insertando datos: {e}")
            return False
        finally:
            cur.close()
            conn.close()
    
    def _insert_single_record(self, cur, row, path_pdf_folder: Optional[str] = None):
        """Inserta un registro individual - adaptado para datos NC"""
        # Extraer y limpiar datos básicos
        report_number = DataProcessor.clean_str(row.get("ReportNumber"))
        crash_date = DataProcessor.to_datetime(row.get("CrashDate"))
        
        # Información de ubicación DEL ACCIDENTE (incident_reports)
        accident_city = DataProcessor.clean_str(row.get("Jurisdiction"))  # Ciudad donde ocurrió el accidente
        accident_street = None  # No tenemos dirección específica del accidente
        state = "NC"  # North Carolina
        zip_code = DataProcessor.clean_str(row.get("Zip"))  # ZIP del conductor
        jurisdiction = DataProcessor.clean_str(row.get("Jurisdiction"))
        dept = DataProcessor.clean_str(row.get("Dept"))
        generation_date = datetime.now()
        
        # Información de ubicación DEL CONDUCTOR (passengers)
        conductor_address = DataProcessor.clean_str(row.get("Address"))  # Domicilio del conductor
        conductor_city = DataProcessor.clean_str(row.get("City"))        # Ciudad del conductor
        conductor_state = DataProcessor.clean_str(row.get("State"))      # Estado del conductor
        
        # Información de persona
        person_type = "driver"  # Asumimos que es conductor por defecto
        first_name = DataProcessor.clean_str(row.get("FirstName"))
        last_name = DataProcessor.clean_str(row.get("LastName"))
        
        # Construir nombre completo
        name = first_name + ' ' + last_name if first_name and last_name else None
        
        # Teléfonos - mapeo directo a tabla passengers
        phone1 = DataProcessor.clean_str(row.get("Phone-1"))  # Phone-1 → phone1
        phone2 = DataProcessor.clean_str(row.get("Phone-2"))  # Phone-2 → phone2
        
        # Elimina decimales y limpia el formato, pero preserva los números de teléfono
        phone1 = re.sub(r'(\.0+)$', '', str(phone1))  # Quita el ".0" si lo tiene
        phone2 = re.sub(r'(\.0+)$', '', str(phone2))  # Quita el ".0" si lo tiene
        # Información de seguro
        insurance_company = DataProcessor.clean_str(row.get("Insurance Company"))
        
        # PDF información - formato específico para NC
        pdf_url = DataProcessor.clean_str(row.get("PDFLINK"))
        pdf_filename = DataProcessor.extract_pdf_filename(pdf_url)
        # Formato: /home/data/NC/{report_number}.pdf
        original_document_location = f"{path_pdf_folder}/{report_number}.pdf" if report_number else None
        
        # source_url: PDF URL sin la extensión .pdf
        source_url = pdf_url.replace('.pdf', '') if pdf_url else None
        
        # Campos adicionales para NC
        original_format = ".pdf"
        website = "northcaroline"
        
        # Construir notas con información adicional de NC (sin phone2 ya que va en campo separado)
        notes_parts = []
        if dept:
            notes_parts.append(f"Department: {dept}")
        if jurisdiction:
            notes_parts.append(f"Jurisdiction: {jurisdiction}")
        if zip_code:
            notes_parts.append(f"ZIP: {zip_code}")
        
        notes = "; ".join(notes_parts) if notes_parts else None
        
        # Construir passenger_notes
        passenger_notes_parts = []
        if person_type:
            passenger_notes_parts.append(f"Person Type: {person_type}")
        if zip_code:
            passenger_notes_parts.append(f"ZIP: {zip_code}")
        
        passenger_notes = "; ".join(passenger_notes_parts) if passenger_notes_parts else None
        
        # Narrative básico
        narrative = f"Crash report from {dept} - {jurisdiction}" if dept and jurisdiction else None
        
        # Verificar/insertar incidente con ubicación del ACCIDENTE
        incident_id = self._get_or_create_incident(
            cur, report_number, crash_date, accident_city, accident_street, 
            generation_date, state, original_document_location, narrative,
            source_url, original_format, website, zip_code
        )
        
        # Verificar/insertar vehículo (unit_number = 1 por defecto)
        vehicle_id = self._get_or_create_vehicle(
            cur, incident_id, 1, insurance_company, 
            None, notes, name, first_name, None, last_name
        )
        
        # Verificar/insertar pasajero - con insurance_company agregado
        self._insert_passenger_if_not_exists(
            cur, vehicle_id, name, None, phone1, phone2, None, None, 
            passenger_notes, first_name, None, last_name,
            conductor_state, conductor_city, conductor_address, 
            person_type, 1, report_number, insurance_company
        )
    
    def _get_or_create_incident(self, cur, report_number, crash_date, city, street, 
                               generation_date, state, original_document_location, narrative,
                               source_url, original_format, website, zip_code):
        """Obtiene o crea un incidente"""
        # Verificar si existe el incidente
        cur.execute("""
            SELECT id FROM incident_reports 
            WHERE report_number = %s AND accident_datetime = %s
        """, (report_number, crash_date))
        
        incident = cur.fetchone()
        if incident:
            incident_id = incident[0]
            # Si existe, actualizar la narrativa si no está vacía
            if narrative and narrative != 'N/A':
                cur.execute("""
                    UPDATE incident_reports 
                    SET narrative = %s 
                    WHERE id = %s AND (narrative IS NULL OR narrative = 'N/A' OR narrative = '')
                """, (narrative, incident_id))
            logger.debug(f"Incidente existente encontrado: {incident_id}")
            
            save_result = save_estatus_pdf(
                file_name=f"{report_number}.pdf",
                report_number=report_number,
                number_passagers=0,
                status="already inserted",
                agency="northcarolina",
                website="northcarolina",
                state="NC",
                city=None,
                created_by="frontend"
            )
            return incident_id
        
        # Si no existe, crear nuevo incidente
        internal_report_number = f"nc{report_number}" if report_number else None
        is_external = "yes"  # Campo específico para NC
        
        cur.execute("""
            INSERT INTO incident_reports (
                report_number, accident_datetime, city, street, generation_date, 
                state, internal_report_number, original_document_location, narrative, 
                is_external, source_url, original_format, website, zip
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (report_number, crash_date, city, street, generation_date, 
              state, internal_report_number, original_document_location, narrative, 
              is_external, source_url, original_format, website, zip_code))
        
        incident_id = cur.fetchone()[0]
        
        save_result = save_estatus_pdf(
                file_name=f"{report_number}.pdf",
                report_number=report_number,
                number_passagers=0,
                status="inserted",
                agency="northcarolina",
                website="northcarolina",
                state="NC",
                city=None,
                created_by="frontend"
            )
        logger.debug(f"Nuevo incidente creado: {incident_id}")
        return incident_id
    
    def _get_or_create_vehicle(self, cur, incident_id, unit_number, insurance_company, 
                              policy_number, notes, name, first_name, middle_name, last_name):
        """Obtiene o crea un vehículo"""
        # Verificar por incident_id + unit_number + driver_name
        cur.execute("""
            SELECT id FROM vehicles 
            WHERE incident_report_id = %s AND unit_number = %s AND driver_name = %s
        """, (incident_id, unit_number, name))
        
        vehicle = cur.fetchone()
        if vehicle:
            logger.debug(f"Vehículo existente encontrado: {vehicle[0]}")
            return vehicle[0]
        
        # Si no existe, crear nuevo vehículo
        cur.execute("""
            INSERT INTO vehicles (
                incident_report_id, unit_number, license_plate_number, 
                insurance_company, policy_number, notes,
                driver_name, driver_first_name, driver_middle_name, driver_last_name
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) 
            RETURNING id
        """, (incident_id, unit_number, None, insurance_company, policy_number, 
              notes, name, first_name, middle_name, last_name))
        
        vehicle_id = cur.fetchone()[0]
        logger.debug(f"Nuevo vehículo creado: {vehicle_id}")
        return vehicle_id
    
    def _insert_passenger_if_not_exists(self, cur, vehicle_id, name, gender, phone1, phone2, age,
                                   year_birth, passenger_notes, first_name, middle_name, last_name,
                                   state, city, street, person_type, number_occupant, report_number, insurance_company):
        """Inserta pasajero si no existe - versión completa para NC"""
        # Verificar si ya existe
        cur.execute("""
            SELECT id FROM passengers
            WHERE vehicle_id = %s AND name = %s
        """, (vehicle_id, name))
        
        passenger = cur.fetchone()
        if not passenger:
            cur.execute("""
                INSERT INTO passengers (
                    vehicle_id, name, gender, phone1, phone2, age, year_birth, notes,
                    first_name, middle_name, last_name, state, city, street, role, 
                    number_occupant, report_number, insurance_company,
                    hasinsurance_details, hasname, over18
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (vehicle_id, name, gender, phone1, phone2, age, year_birth, passenger_notes,
                first_name, middle_name, last_name, state, city, street, 
                person_type, 
                number_occupant, 
                report_number, 
                insurance_company,
                str(bool(insurance_company)),  # hasinsurance_details
                str(bool(name) and name.upper() not in {"", "N/A", "KNOWN", "UNKNOWN"}),  # hasname
                str((age_value := (int(age) if str(age).isdigit() else None)) is not None and age_value > 17)
                ))
            logger.debug(f"Nuevo pasajero creado para vehículo: {vehicle_id}")
        else:
            logger.debug(f"Pasajero existente encontrado: {passenger[0]}")

def upload_excel_to_database(excel_path: str) -> bool:
    """
    Función principal para subir Excel de NC a base de datos
    
    Args:
        excel_path: Ruta al archivo Excel
        
    Returns:
        bool: True si la subida fue exitosa
    """
    try:
        logger.info(f"Leyendo archivo Excel: {excel_path}")
        
        # Leer archivo Excel
        df = pd.read_excel(excel_path)
        
        if df.empty:
            logger.warning("Excel está vacío")
            return False
        
        logger.info(f"Excel cargado con {len(df)} registros")
        logger.info(f"Columnas encontradas: {list(df.columns)}")
        
        # Verificar columnas requeridas
        required_columns = ['ReportNumber', 'CrashDate', 'FirstName', 'LastName']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            logger.error(f"Columnas faltantes: {missing_columns}")
            return False
        
        # Subir a base de datos
        db_manager = DatabaseManager()
        success = db_manager.insert_dataframe_to_database(df)
        
        if success:
            logger.info("Excel subido exitosamente a la base de datos")
        else:
            logger.error("Error subiendo Excel a la base de datos")
        
        return success
        
    except Exception as e:
        logger.error(f"Error procesando Excel: {str(e)}")
        return False

def upload_dataframe_to_database(df: pd.DataFrame, path_pdf_folder: Optional[str] = None) -> bool:
    """
    Función para subir DataFrame directamente
    
    Args:
        df: DataFrame con los datos procesados
        
    Returns:
        bool: True si la subida fue exitosa
    """
    try:
        if df.empty:
            logger.warning("DataFrame está vacío")
            return False
        
        logger.info(f"Recibido DataFrame con {len(df)} registros")
        logger.info(f"Columnas: {list(df.columns)}")
        
        # Subir a base de datos
        db_manager = DatabaseManager()
        success = db_manager.insert_dataframe_to_database(df, path_pdf_folder=path_pdf_folder)
        
        if success:
            logger.info("DataFrame subido exitosamente a la base de datos")
        else:
            logger.error("Error subiendo DataFrame a la base de datos")
        
        return success
        
    except Exception as e:
        logger.error(f"Error procesando DataFrame: {str(e)}")
        return False

# Función para usar desde otros scripts
def loader_df_to_db(df: pd.DataFrame, path_pdf_folder: Optional[str] = None) -> bool:
    """
    Función principal para llamar desde otros scripts
    
    Args:
        df: DataFrame con los datos de NC
        path_pdf_folder: Ruta a la carpeta donde se encuentran los PDFs (opcional)
    """
    success = upload_dataframe_to_database(df, path_pdf_folder=path_pdf_folder)
    return success



# excel_path = "C:/Users/spss/OneDrive - INGELSI CIA LTDA/Documentos/SynapseIQ/data/NC/NC List UPLD/NC List  4-14-25.xlsx"
# df = pd.read_excel(excel_path)
# success = loader_df_to_db(df)
