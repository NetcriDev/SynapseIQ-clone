import os
import pandas as pd
import psycopg2
import logging
from datetime import datetime
from typing import Optional
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

class OhioLoader:
    """Cargador simple para datos de Ohio"""
    
    def __init__(self):
        self.config = Config()
        logger.info("OhioLoader inicializado")
    
    def extract_city(self, filename: str) -> str:
        """Extrae ciudad del nombre del archivo"""
        if not filename:
            return "Unknown"
        
        base_name = os.path.splitext(os.path.basename(filename))[0]
        cities = ['Cincinnati', 'Columbus', 'Cleveland', 'Toledo', 'Akron', 'Dayton']
        
        # Buscar ciudad conocida
        for city in cities:
            if city.lower() in base_name.lower():
                return city
        
        # Si no encuentra, tomar primera palabra válida
        words = base_name.replace('_', ' ').replace('#', ' ').split()
        for word in words:
            if word.lower() not in ['brandon', 'data', 'file'] and len(word) > 3:
                return word.title()
        
        return "Unknown"
    
    def calculate_age(self, dob_str: str, crash_date_str: str = None) -> Optional[int]:
        """Calcula edad desde fecha de nacimiento"""
        try:
            if not dob_str or pd.isna(dob_str):
                return None
            
            # Parsear DOB
            for fmt in ["%m/%d/%Y", "%d/%m/%Y", "%Y-%m-%d"]:
                try:
                    birth_date = datetime.strptime(str(dob_str).strip(), fmt)
                    break
                except ValueError:
                    continue
            else:
                return None
            
            # Fecha de referencia
            ref_date = datetime.now()
            if crash_date_str:
                try:
                    ref_date = pd.to_datetime(crash_date_str)
                except:
                    pass
            
            age = ref_date.year - birth_date.year
            if ref_date.month < birth_date.month or (ref_date.month == birth_date.month and ref_date.day < birth_date.day):
                age -= 1
            
            return age if 0 <= age <= 120 else None
        except:
            return None
    
    def get_connection(self):
        """Obtiene conexión a la base de datos"""
        return psycopg2.connect(
            dbname=self.config.DB_NAME,
            user=self.config.DB_USER,
            password=self.config.DB_PASSWORD,
            host=self.config.DB_HOST,
            port=self.config.DB_PORT
        )
    
    def load_data(self, df: pd.DataFrame, filename: str = None) -> bool:
        """
        Función principal para cargar datos de Ohio
        
        Args:
            df: DataFrame con los 9 campos de Ohio
            filename: Nombre del archivo para extraer ciudad
        """
        try:
            logger.info(f"Cargando {len(df)} registros de Ohio")
            
            if df.empty:
                logger.warning("DataFrame vacío")
                return False
            
            # Verificar columnas requeridas (con variaciones para DOB)
            required_cols = [
                'input_Reporting_number', 'input_firstName', 'input_lastName', 
                'Phone1', 'Phone2', 'Phone3', 'Crash_Date', 'At_Fault_Insurance'
            ]
            
            # Verificar que al menos una variación de DOB existe
            dob_variants = ['DOB', 'dob', 'input_DOB']
            has_dob = any(col in df.columns for col in dob_variants)
            
            missing = [col for col in required_cols if col not in df.columns]
            if missing:
                logger.error(f"Columnas faltantes: {missing}")
                return False
            
            if not has_dob:
                logger.error(f"Campo DOB no encontrado. Variaciones esperadas: {dob_variants}")
                return False
            
            # Extraer ciudad
            city = self.extract_city(filename)
            logger.info(f"Ciudad extraída: {city}")
            
            conn = self.get_connection()
            cur = conn.cursor()
            
            try:
                # Procesar cada registro
                for _, row in df.iterrows():
                    self._process_record(cur, row, city)
                
                conn.commit()
                logger.info("Datos cargados exitosamente")
                return True
                
            except Exception as e:
                conn.rollback()
                logger.error(f"Error cargando datos: {e}")
                return False
            finally:
                cur.close()
                conn.close()
                
        except Exception as e:
            logger.error(f"Error general: {e}")
            return False
    
    def _process_record(self, cur, row, city):
        """Procesa un registro individual"""
        
        # Extraer datos del Excel - con variaciones de nombres de columnas
        report_number = str(row.get("input_Reporting_number", "")).strip()
        first_name = str(row.get("input_firstName", "")).strip()
        last_name = str(row.get("input_lastName", "")).strip()
        
        # Buscar DOB con diferentes nombres posibles
        dob = None
        for dob_field in ["DOB", "dob", "input_DOB"]:
            if dob_field in row and pd.notna(row[dob_field]):
                dob = str(row[dob_field]).strip()
                break
        
        phone1 = str(row.get("Phone1", "")).strip() or None
        phone2 = str(row.get("Phone2", "")).strip() or None
        phone3 = str(row.get("Phone3", "")).strip() or None
        crash_date = pd.to_datetime(row.get("Crash_Date"))
        insurance = str(row.get("At_Fault_Insurance", "")).strip()
        
        # Calcular campos derivados
        name = f"{first_name} {last_name}".strip()
        age = self.calculate_age(dob, row.get("Crash_Date"))
        year_birth = None
        if dob:
            try:
                year_birth = datetime.strptime(dob, "%m/%d/%Y").year
            except:
                pass
        
        # 1. Insertar/actualizar incidente
        incident_id = self._get_or_create_incident(cur, report_number, crash_date, city)
        
        # 2. Insertar/actualizar vehículo
        vehicle_id = self._get_or_create_vehicle(cur, incident_id, insurance, name, first_name, last_name)
        
        # 3. Insertar/actualizar pasajero
        self._insert_passenger(cur, vehicle_id, name, first_name, last_name, phone1, phone2, phone3, 
                              age, year_birth, city, report_number, insurance, dob)
    
    def _get_or_create_incident(self, cur, report_number, crash_date, city):
        """Crear o obtener incidente"""
        cur.execute("SELECT id FROM incident_reports WHERE report_number = %s", (report_number,))
        result = cur.fetchone()
        
        if result:
            return result[0]
        
        # Crear nuevo incidente
        cur.execute("""
            INSERT INTO incident_reports (
                report_number, accident_datetime, city, state, generation_date,
                internal_report_number, original_document_location, source_url,
                original_format, website, is_external
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            report_number, crash_date, city, "OH", datetime.now(),
            f"oh{report_number}", f"/home/data/OH/{city}/{report_number}.pdf",
            f"ohio/{city.lower()}/{report_number}", ".pdf", "ohio", "yes"
        ))
        
        return cur.fetchone()[0]
    
    def _get_or_create_vehicle(self, cur, incident_id, insurance, name, first_name, last_name):
        """Crear o obtener vehículo"""
        cur.execute("SELECT id FROM vehicles WHERE incident_report_id = %s AND driver_name = %s", 
                   (incident_id, name))
        result = cur.fetchone()
        
        if result:
            return result[0]
        
        # Crear nuevo vehículo
        cur.execute("""
            INSERT INTO vehicles (
                incident_report_id, unit_number, insurance_company,
                driver_name, driver_first_name, driver_last_name
            ) VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (incident_id, 1, insurance, name, first_name, last_name))
        
        return cur.fetchone()[0]
    
    def _insert_passenger(self, cur, vehicle_id, name, first_name, last_name, phone1, phone2, phone3,
                         age, year_birth, city, report_number, insurance, dob):
        """Insertar pasajero"""
        # Verificar si existe
        cur.execute("SELECT id FROM passengers WHERE vehicle_id = %s AND name = %s", (vehicle_id, name))
        if cur.fetchone():
            return  # Ya existe
        
        # Crear notas con info adicional
        notes_parts = []
        if age:
            notes_parts.append(f"Age: {age}")
        if year_birth:
            notes_parts.append(f"Birth Year: {year_birth}")
        if phone3:
            notes_parts.append(f"Phone3: {phone3}")
        if dob:
            notes_parts.append(f"DOB: {dob}")
        
        notes = "; ".join(notes_parts) if notes_parts else None
        
        # Insertar pasajero
        cur.execute("""
            INSERT INTO passengers (
                vehicle_id, name, first_name, last_name, phone1, phone2,
                age, year_birth, notes, state, city, role, number_occupant,
                report_number, insurance_company
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            vehicle_id, name, first_name, last_name, phone1, phone2,
            age, year_birth, notes, "OH", city, "driver", 1,
            report_number, insurance
        ))

# Función principal de interfaz
def load_ohio_data(df: pd.DataFrame, filename: str = None) -> bool:
    """
    Función principal para cargar datos de Ohio
    
    Args:
        df: DataFrame con campos de Ohio
        filename: Nombre del archivo para extraer ciudad
    
    Returns:
        bool: True si fue exitoso
    """
    loader = OhioLoader()
    return loader.load_data(df, filename)

# Ejemplo de uso:
# df = pd.read_excel("Cincinnati 6_18 #2.xlsx")
# success = load_ohio_data(df, "Cincinnati 6_18 #2.xlsx")



# path_table="C:/Users/spss/OneDrive - INGELSI CIA LTDA/Documentos/SynapseIQ/data/Ohio/Cincinnati 6_18 #2.xlsx"
# df = pd.read_excel(path_table)
# success = load_ohio_data(df,path_table)