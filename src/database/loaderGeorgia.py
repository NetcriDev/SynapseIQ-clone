import os
import pandas as pd
import psycopg2
import logging
from datetime import datetime
from typing import Optional, List

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Config:
    """Configuración de base de datos"""
    DB_NAME = os.getenv('DB_NAME', 'crash_records_001')
    DB_USER = os.getenv('DB_USER', 'synapseiq')
    DB_PASSWORD = os.getenv('DB_PASSWORD', 'SynapseIQ$2025')
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = os.getenv('DB_PORT', '5432')  ########################## ojo

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
            # Intentar diferentes formatos de fecha
            for fmt in ["%m/%d/%Y", "%Y-%m-%d", "%m-%d-%Y"]:
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
        """Convierte a datetime"""
        try:
            if pd.isna(value):
                return None
            return pd.to_datetime(value)
        except:
            return None

class DatabaseManager:
    """Maneja las operaciones de base de datos para reportes de Georgia"""
    
    def __init__(self):
        self.config = Config()
        logger.info("DatabaseManager inicializado para Georgia")
    
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

    def insert_dataframe_to_database(self, df: pd.DataFrame, path_file_saved: str) -> bool:
        """
        Inserta DataFrame en la base de datos
        
        Args:
            df: DataFrame con los datos procesados
            path_file_saved: Ruta del archivo guardado (no se usa en esta función, pero se puede extender)

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
            for report_group in df.groupby('agency_case_number'):
                agency_case_number, group_df = report_group
                
                if pd.isna(agency_case_number) or agency_case_number is None:
                    logger.warning("Registro sin número de caso, omitiendo")
                    continue
                
                logger.info(f"Procesando reporte: {agency_case_number}")
                
                # Procesar cada fila del grupo
                for _, row in group_df.iterrows():
                    self._insert_single_record(cur, row, path_file_saved)

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

    def _insert_single_record(self, cur, row, path_file_saved):
        """Inserta un registro individual"""
        # Extraer y limpiar datos básicos
        report_number = DataProcessor.clean_str(row.get("agency_case_number"))
        crash_date = DataProcessor.to_datetime(row.get("estimated_crash_date_time"))
        narrative = DataProcessor.clean_str(row.get("narrative"))
        
        # Información de ubicación
        full_address = DataProcessor.clean_str(row.get("address"))
        city = DataProcessor.extract_city_from_address(full_address) or DataProcessor.clean_str(row.get("city"))
        street = full_address
        state = "GA"  # Georgia
        generation_date = datetime.now()
        
        # Información de persona
        person_type = DataProcessor.clean_str(row.get("person_type"))  # 'driver' o 'occupant'
        first_name = DataProcessor.clean_str(row.get("first_name"))
        middle_name = DataProcessor.clean_str(row.get("middle_name"))
        last_name = DataProcessor.clean_str(row.get("last_name"))
        
        # Construir nombre completo
        name_parts = [first_name, middle_name, last_name]
        name = " ".join([part for part in name_parts if part]).strip()
        name = name if name else None
        
        # Datos específicos
        gender = DataProcessor.clean_str(row.get("sex"))
        phone1 = DataProcessor.clean_str(row.get("telephone_no"))
        age = DataProcessor.to_int(row.get("age"))
        year_birth = DataProcessor.extract_year(row.get("dob"))
        unit_number = DataProcessor.to_int(row.get("unit_number"))
        
        # Información de vehículo/seguro
        insurance_company = DataProcessor.clean_str(row.get("insurance_company"))
        policy_number = DataProcessor.clean_str(row.get("policy_no"))
        
        # Construir notas con información adicional
        notes_parts = []
        if row.get("driver_license_no"):
            notes_parts.append(f"Driver License: {DataProcessor.clean_str(row.get('driver_license_no'))}")
        if row.get("position"):
            notes_parts.append(f"Position: {DataProcessor.clean_str(row.get('position'))}")
        if row.get("safety_equipment"):
            notes_parts.append(f"Safety Equipment: {DataProcessor.clean_str(row.get('safety_equipment'))}")
        if row.get("ejected"):
            notes_parts.append(f"Ejected: {DataProcessor.clean_str(row.get('ejected'))}")
        if row.get("extricated"):
            notes_parts.append(f"Extricated: {DataProcessor.clean_str(row.get('extricated'))}")
        if row.get("air_bag"):
            notes_parts.append(f"Air Bag: {DataProcessor.clean_str(row.get('air_bag'))}")
        if row.get("injury"):
            notes_parts.append(f"Injury: {DataProcessor.clean_str(row.get('injury'))}")
        if row.get("taken_for_treatment"):
            notes_parts.append(f"Taken for Treatment: {DataProcessor.clean_str(row.get('taken_for_treatment'))}")
        
        notes = "; ".join(notes_parts) if notes_parts else None
        
        # Construir passenger_notes
        passenger_notes = f"Person Type: {person_type}" if person_type else None
        if row.get("zip"):
            zip_code = DataProcessor.clean_str(row.get("zip"))
            if zip_code:
                passenger_notes = f"{passenger_notes}; ZIP: {zip_code}" if passenger_notes else f"ZIP: {zip_code}"
        
        # Construir original_document_location desde pdf_filename
        pdf_filename = DataProcessor.clean_str(row.get("pdf_filename"))
        original_document_location = f"{pdf_filename}.pdf" if pdf_filename else None
        
        # Verificar/insertar incidente
        incident_id = self._get_or_create_incident(
            cur, report_number, crash_date, city, street, 
            generation_date, state, path_file_saved, narrative
        )
        
        # Verificar/insertar vehículo
        vehicle_id = self._get_or_create_vehicle(
            cur, incident_id, unit_number, insurance_company, 
            policy_number, notes, name, first_name, middle_name, last_name
        )
        
        # Verificar/insertar pasajero
        self._insert_passenger_if_not_exists(
            cur, vehicle_id, name, gender, phone1, age, year_birth, 
            passenger_notes, first_name, middle_name, last_name,
            state, city, street, person_type
        )
    
    def _get_or_create_incident(self, cur, report_number, crash_date, city, street, 
                               generation_date, state, original_document_location, narrative):
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
            return incident_id
        
        # Si no existe, crear nuevo incidente
        internal_report_number = f"ga{report_number}" if report_number else None
        
        cur.execute("""
            INSERT INTO incident_reports (
                report_number, accident_datetime, city, street, generation_date, 
                state, internal_report_number, original_document_location, narrative, 
                is_external, website
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (report_number, crash_date, city, street, generation_date, 
              state, internal_report_number, original_document_location, narrative, "yes", "georgia"))
        
        incident_id = cur.fetchone()[0]
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
                driver_name, driver_first_name, driver_middle_name, driver_last_name, website
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (incident_id, unit_number, None, insurance_company, policy_number, 
              notes, name, first_name, middle_name, last_name, "georgia"))
        
        vehicle_id = cur.fetchone()[0]
        logger.debug(f"Nuevo vehículo creado: {vehicle_id}")
        return vehicle_id
    
    def _insert_passenger_if_not_exists(self, cur, vehicle_id, name, gender, phone1, age,
                                       year_birth, passenger_notes, first_name, middle_name, last_name,
                                       state, city, street, person_type):
        """Inserta pasajero si no existe"""
        # Verificar si ya existe
        cur.execute("""
            SELECT id FROM passengers
            WHERE vehicle_id = %s AND name = %s AND gender = %s
        """, (vehicle_id, name, gender))
        
        passenger = cur.fetchone()
        if not passenger:
            cur.execute("""
                INSERT INTO passengers (
                    vehicle_id, name, gender, phone1, age, year_birth, notes,
                    first_name, middle_name, last_name, state, city, street, role, website
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (vehicle_id, name, gender, phone1, age, year_birth, passenger_notes,
                  first_name, middle_name, last_name, state, city, street, person_type, "georgia"))
            logger.debug(f"Nuevo pasajero creado para vehículo: {vehicle_id}")
        else:
            logger.debug(f"Pasajero existente encontrado: {passenger[0]}")

def upload_dataframe_to_database(df: pd.DataFrame, path_file_saved: str) -> bool:
    """
    Función principal para subir DataFrame a base de datos
    
    Args:
        df: DataFrame con los datos procesados
        path_file_saved: Ruta del archivo guardado (no se usa en esta función, pero se puede extender)
        
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
        success = db_manager.insert_dataframe_to_database(df, path_file_saved)
        
        if success:
            logger.info("DataFrame subido exitosamente a la base de datos")
        else:
            logger.error("Error subiendo DataFrame a la base de datos")
        
        return success
        
    except Exception as e:
        logger.error(f"Error procesando DataFrame: {str(e)}")
        return False

# Función para usar desde otros scripts
def loader_df_to_db(df: pd.DataFrame, path_file_saved: str) -> bool:
    """
    Función principal para llamar desde otros scripts
    
    Args:
        df: DataFrame con los datos
        path_file_saved: Ruta del archivo guardado (no se usa en esta función, pero se puede extender)
    Returns:
        bool: True si la subida fue exitosa
    """
    success = upload_dataframe_to_database(df, path_file_saved)
    return success

# if __name__ == "__main__":
#     # Ejemplo de uso directo
#     import pandas as pd
    
#     # Crear DataFrame de ejemplo
#     df_example = pd.DataFrame({
#         'agency_case_number': ['GP12345'],
#         'estimated_crash_date_time': ['01/15/2024 14:30'],
#         'narrative': ['Sample crash narrative'],
#         'person_type': ['driver'],
#         'first_name': ['John'],
#         'last_name': ['Doe'],
#         'unit_number': [1]
#     })
    
#     success = upload_dataframe_to_database(df_example)
    
#     if success:
#         print("✅ DataFrame subido exitosamente")
#     else:
#         print("❌ Error subiendo DataFrame")