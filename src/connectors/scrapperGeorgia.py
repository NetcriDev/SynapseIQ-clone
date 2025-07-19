import re
import pandas as pd
import pdfplumber
import os
from typing import Dict, List, Union
import logging
from pathlib import Path

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PDFToCsvProcessor:
    """
    Clase para procesar reportes de accidentes de PDF a CSV
    """
    
    def __init__(self):
        # Expandida blacklist con más palabras de ruido
        self.blacklist_words = {
            "BIKE", "ADDRESS", "PED", "UNKNOWN", "WAY", "NW", "SW", "SE", "NE", "DR", "ST", "RD", "AVE", "BLVD",
            "LN", "TRCE", "CT", "PL", "HWY", "BRIDGE", "OFF", "RAMP", "TO", "A", "ON", "IN", "OUT", "OF", "THE",
            "FROM", "WAS", "FOR", "AND", "AS", "BY", "WITH", "NO", "RETE", "H", "GY", "N", "W", "DO", "UD", "NY", 
            "OG", "OA", "DB", "YL", "E", "GD", "AR", "S", "AL", "CE", "WT", "OR",
            "SCAR", "CL", "OE", "VT", "IT", "TR", "O", "NS", 
            "RIVE", "RR", "SC", "WL", "EI", "LF", "GR", 
            "T", "TA", "REK", "AE", "TN", "M", "F", "EO", "NR", "TREATMENT",
            "AUTO"
        }
    
    def clean_value(self, value: Union[str, None]) -> Union[str, None]:
        """Limpia valores eliminando palabras de la blacklist - versión mejorada"""
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return None
            # Unir números separados por espacios
            value = re.sub(r'(\d)\s+(\d)', r'\1\2', value) 
            words = value.split()
            cleaned = []
            for w in words:
                if w.isdigit():
                    cleaned.append(w)
                elif w.upper() not in self.blacklist_words:
                    # Remover caracteres especiales excepto espacios y letras/números
                    cleaned_word = re.sub(r'[^\w\s]', '', w)
                    if cleaned_word:
                        cleaned.append(cleaned_word)
            return " ".join([w for w in cleaned if w]).strip() if cleaned else None
        return value
    
    def extract_report_details(self, pdf_text: str) -> Dict:
        """Extrae detalles básicos del reporte - con regex mejoradas"""
        report_data = {}
        
        # Número de caso - regex mejorada para capturar más formatos
        agency_case_match = re.search(r"Agency Case Number.*?(\b(?:\d{10}|GP\d+)\b)", pdf_text, re.DOTALL)
        if agency_case_match:
            report_data['agency_case_number'] = agency_case_match.group(1).strip()
        else:
            report_data['agency_case_number'] = None
        
        # Fecha y hora del accidente
        estimated_crash_block_match = re.search(
            r"(Estimated Crash.*?)(?=Road of At Its)", pdf_text, re.DOTALL
        )
        if estimated_crash_block_match:
            crash_block_text = estimated_crash_block_match.group(1)
            date_time_match = re.search(r"(\d{2}/\d{2}/\d{4})\s+(\d{2}:\d{2})", crash_block_text)
            report_data['estimated_crash_date_time'] = f"{date_time_match.group(1)} {date_time_match.group(2)}" if date_time_match else None
        else:
            report_data['estimated_crash_date_time'] = None
        
        # Narrativa - mejorada para capturar continuaciones
        narrative_sections = []
        end_of_narrative_patterns = [
            r"\nDIAGRAM", r"\nADMINISTRATIVE", r"\nSUPPLEMENT", r"\nGDOT-523",
            r"\nADDITIONAL CITATION INFORMATION", r"\nPROPERTY DAMAGE INFORMATION", r"\Z"
        ]
        end_of_narrative_regex = "(?:" + "|".join(end_of_narrative_patterns) + ")"

        # Narrativa inicial
        initial_narrative_match = re.search(
            r"NARRATIVE\s*\n(.*?){}".format(end_of_narrative_regex),
            pdf_text, re.DOTALL
        )
        if initial_narrative_match:
            narrative_sections.append(initial_narrative_match.group(1).strip())

        # Narrativas continuadas
        continued_narrative_matches = re.finditer(
            r"(?:.*?\* \* Continued \* \*\s*\n)?NARRATIVE CONTINUED\s*\n(.*?){}".format(end_of_narrative_regex),
            pdf_text, re.DOTALL
        )
        for match in continued_narrative_matches:
            narrative_sections.append(match.group(1).strip())
        
        full_narrative = "\n".join(narrative_sections)
        
        if full_narrative:
            # Limpieza mejorada de la narrativa
            full_narrative = re.sub(r"PAGE\s*__\d+____\s*of\s*__\d+____\s*", "", full_narrative).strip()
            full_narrative = re.sub(r"Page _\d+__ of _\d+__\s*", "", full_narrative).strip()
            full_narrative = re.sub(r"\n\s*\n", "\n", full_narrative).strip()
            full_narrative = re.sub(r"\* \* Continued \* \*\s*", "", full_narrative).strip()
            full_narrative = re.sub(r"Ofc\. #\d+\s*", "", full_narrative).strip()
            full_narrative = re.sub(r"\* \* E N D \* \*\s*", "", full_narrative).strip()
            full_narrative = re.sub(r"ADDITIONAL CITATION INFORMATION.*", "", full_narrative, flags=re.DOTALL).strip()
            full_narrative = re.sub(r"victim rights pamphlet with a case number\.\s*", "", full_narrative).strip()
            report_data['narrative'] = full_narrative
        else:
            report_data['narrative'] = None
            
        return report_data
    
    def extract_drivers(self, pdf_text: str) -> List[Dict]:
        """Extrae información de conductores - con regex mejoradas"""
        drivers = []
        drivers_dict = {}
        
        # Patrón mejorado que incluye X?Driver para manejar variaciones
        unit_block_pattern = re.compile(
            r"(Unit # X?Driver LAST NAME FIRST MIDDLE\s*(?:Unit # X?Driver LAST NAME FIRST MIDDLE\s*)?\n.*?)" +
            r"(?=\n*COMMERCIAL MOTOR VEHICLES ONLY|\n*OCCUPANT INFORMATION|ADMINISTRATIVE|SUPPLEMENT|GDOT-523|\Z)",
            re.DOTALL
        )
        
        for block_match in unit_block_pattern.finditer(pdf_text):
            current_block_text = block_match.group(1)
            
            # Regex mejorada para nombres con mejor manejo de middle names
            name_line_match = re.search(
                r"Unit # X?Driver LAST NAME FIRST MIDDLE\s*(?:Unit # X?Driver LAST NAME FIRST MIDDLE\s*)?\n"
                r"(?P<left_unit_num>\d+)\s+Ped\s+(?P<left_last>\S+)\s+(?P<left_first>\S+)(?:\s+(?P<left_middle>(?!Ped|\d+)\S+))?\s*"
                r"(?P<right_unit_full>(?P<right_unit_num>\d+)\s+Ped\s+(?P<right_last>\S+)\s+(?P<right_first>\S+)(?:\s+(?P<right_middle>(?!Ped|\d+)\S+))?)?",
                current_block_text
            )
            
            current_block_unit_numbers = []
            if name_line_match:
                # Conductor izquierdo
                ul = name_line_match.group('left_unit_num')
                left_driver = {
                    "unit_number": ul,
                    "last_name": self.clean_value(name_line_match.group("left_last")),
                    "first_name": self.clean_value(name_line_match.group("left_first")),
                    "middle_name": self.clean_value(name_line_match.group("left_middle")) if name_line_match.group("left_middle") else None
                }
                drivers_dict[ul] = left_driver
                drivers.append(left_driver)
                current_block_unit_numbers.append(ul)
                
                # Conductor derecho (si existe)
                if name_line_match.group("right_unit_full"):
                    ur = name_line_match.group("right_unit_num")
                    right_driver = {
                        "unit_number": ur,
                        "last_name": self.clean_value(name_line_match.group("right_last")),
                        "first_name": self.clean_value(name_line_match.group("right_first")),
                        "middle_name": self.clean_value(name_line_match.group("right_middle")) if name_line_match.group("right_middle") else None
                    }
                    drivers_dict[ur] = right_driver
                    drivers.append(right_driver)
                    current_block_unit_numbers.append(ur)
            
            # Extraer información adicional
            self._extract_additional_driver_info(current_block_text, drivers_dict, current_block_unit_numbers)
        
        return sorted(drivers_dict.values(), key=lambda x: int(x['unit_number']))
    
    def _extract_additional_driver_info(self, block_text: str, drivers_dict: Dict, unit_numbers: List[str]):
        """Extrae información adicional de conductores - con regex mejoradas"""
        # Dirección - regex mejorada para Bike Address
        bike_address_matches = re.findall(
            r"Bike Address\s*(\d+)\s*(.+?)(?=\nCity State Zip DOB|Bike Address|\Z)",
            block_text, re.DOTALL
        )
        
        for match in bike_address_matches:
            unit_num = match[0]
            address = match[1].strip()
            # Limpieza mejorada de direcciones
            address = re.sub(r"Susp At Fault.*", "", address, flags=re.DOTALL).strip()
            address = re.sub(r"City State Zip DOB.*", "", address, flags=re.DOTALL).strip()
            address = address.replace('\n', ' ').strip()
            address = re.sub(r'(\d)\s+(\d)', r'\1\2', address) 
            if unit_num in drivers_dict:
                drivers_dict[unit_num]['address'] = self.clean_value(address)
        
        # Ciudad, estado, zip, fecha de nacimiento
        city_dob_match = re.search(
            r"City State Zip DOB\s*\n\s*(\S+)\s+(\S+)\s+(\S+)\s+(\d{2}/\d{2}/\d{4})"
            r"(?:\s+(\S+)\s+(\S+)\s+(\S+)\s+(\d{2}/\d{2}/\d{4}))?",
            block_text
        )
        if city_dob_match and unit_numbers:
            ul = unit_numbers[0]
            if ul in drivers_dict:
                drivers_dict[ul].update({
                    'city': self.clean_value(city_dob_match.group(1)),
                    'state': city_dob_match.group(2),
                    'zip': city_dob_match.group(3),
                    'dob': city_dob_match.group(4)
                })
            if len(unit_numbers) > 1 and city_dob_match.group(5):
                ur = unit_numbers[1]
                if ur in drivers_dict:
                    drivers_dict[ur].update({
                        'city': self.clean_value(city_dob_match.group(5)),
                        'state': city_dob_match.group(6),
                        'zip': city_dob_match.group(7),
                        'dob': city_dob_match.group(8)
                    })
        
        # Licencia de conducir
        dl_match = re.search(
            r"Driver's License No\. Class State Country\s*\n\s*(\S+)\s+\S+\s+\S+\s+\S+"
            r"(?:\s+(\S+)\s+\S+\s+\S+\s+\S+)?",
            block_text
        )
        if dl_match and unit_numbers:
            ul = unit_numbers[0]
            if ul in drivers_dict:
                drivers_dict[ul]['driver_license_no'] = dl_match.group(1)
            if len(unit_numbers) > 1 and dl_match.group(2):
                ur = unit_numbers[1]
                if ur in drivers_dict:
                    drivers_dict[ur]['driver_license_no'] = dl_match.group(2)
        
        # Información del seguro - regex mejorada
        ins_match = re.search(
            r"Insurance Co\. Policy No\. Telephone No\.\s*\n"
            r"(?P<ins_comp_left>.+?)\s+(?P<policy_left>[A-Z0-9]+)\s+(?P<phone_left>\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4})"
            r"(?:\s+(?P<ins_comp_right>.+?)\s+(?P<policy_right>[A-Z0-9]+)\s+(?P<phone_right>\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}))?",
            block_text, re.DOTALL
        )
        
        if ins_match and unit_numbers:
            ul = unit_numbers[0]
            if ul in drivers_dict:
                ins_comp_left = re.sub(r'\s*AUTO$', '', ins_match.group('ins_comp_left').strip())
                drivers_dict[ul].update({
                    'insurance_company': self.clean_value(ins_comp_left),
                    'policy_no': ins_match.group('policy_left').strip(),
                    'telephone_no': ins_match.group('phone_left')
                })
            if len(unit_numbers) > 1 and ins_match.group('ins_comp_right'):
                ur = unit_numbers[1]
                if ur in drivers_dict:
                    ins_comp_right = re.sub(r'\s*AUTO$', '', ins_match.group('ins_comp_right').strip())
                    drivers_dict[ur].update({
                        'insurance_company': self.clean_value(ins_comp_right),
                        'policy_no': ins_match.group('policy_right').strip(),
                        'telephone_no': ins_match.group('phone_right')
                    })
        
        # Post-procesamiento: separar insurance_company y policy_no si están unidos
        for unit_num in unit_numbers:
            if unit_num in drivers_dict:
                driver = drivers_dict[unit_num]
                raw = driver.get("insurance_company", "")
                if raw:
                    raw = raw.strip()
                    num_match = re.search(r"\d", raw)
                    if num_match:
                        split_idx = num_match.start()
                        driver["insurance_company"] = self.clean_value(raw[:split_idx].strip())
                        driver["policy_no"] = raw[split_idx:].strip()
                    else:
                        driver["insurance_company"] = self.clean_value(raw)
                        if not driver.get("policy_no"):
                            driver["policy_no"] = ""
    
    def extract_occupants(self, pdf_text: str) -> List[Dict]:
        """Extrae información de ocupantes - con regex mejoradas"""
        occupants = []
        
        occupant_sections_matches = re.finditer(
            r"(OCCUPANT INFORMATION|ADDITIONAL OCCUPANT INFORMATION)\s*\n(.*?)(?=\nADMINISTRATIVE|\nSUPPLEMENT|\nGDOT-523|\Z)",
            pdf_text, re.DOTALL
        )
        
        # Patrón mejorado y más flexible para ocupantes
        occupant_entry_pattern = re.compile(
            r"Name \(Last, First\):\s*(?P<full_name>[^\n]*)\s*Address(?::)?\s*(?P<address>[^\n]*)\n"
            r"(?P<rest>.*?)"
            r"(?:Injured Taken To:|ADMINISTRATIVE|ADDITIONAL OCCUPANT INFORMATION|Name \(Last, First\):|$)",
            re.DOTALL
        )
        
        for section_match in occupant_sections_matches:
            occupant_section_text = section_match.group(2)
            
            for occupant_match in occupant_entry_pattern.finditer(occupant_section_text):
                occupant_details = {}
                full_name_str = occupant_match.group('full_name').strip()
                
                # Manejo mejorado de nombres
                if full_name_str:
                    if ',' in full_name_str:
                        parts = [s.strip() for s in full_name_str.split(',', 1)]
                        occupant_details['last_name'] = self.clean_value(parts[0])
                        # Separar first y middle del segundo part
                        first_middle_parts = parts[1].split()
                        if len(first_middle_parts) > 1:
                            occupant_details['first_name'] = self.clean_value(first_middle_parts[0])
                            occupant_details['middle_name'] = self.clean_value(' '.join(first_middle_parts[1:]))
                        else:
                            occupant_details['first_name'] = self.clean_value(first_middle_parts[0]) if first_middle_parts else None
                            occupant_details['middle_name'] = None
                    else:
                        name_parts = full_name_str.split()
                        if len(name_parts) > 2:
                            occupant_details['last_name'] = self.clean_value(name_parts[-1])
                            occupant_details['first_name'] = self.clean_value(name_parts[0])
                            occupant_details['middle_name'] = self.clean_value(' '.join(name_parts[1:-1]))
                        elif len(name_parts) == 2:
                            occupant_details['last_name'] = self.clean_value(name_parts[-1])
                            occupant_details['first_name'] = self.clean_value(name_parts[0])
                            occupant_details['middle_name'] = None
                        else:
                            occupant_details['last_name'] = None
                            occupant_details['first_name'] = self.clean_value(full_name_str)
                            occupant_details['middle_name'] = None
                else:
                    occupant_details['last_name'] = None
                    occupant_details['first_name'] = None
                    occupant_details['middle_name'] = None
                
                occupant_details['address'] = self.clean_value(occupant_match.group('address').replace('\n', ' ').strip()) if occupant_match.group('address') else None
                
                # Extraer otros campos del bloque restante
                rest = occupant_match.group('rest')
                age_match = re.search(r'Age:\s*(\d+)', rest)
                sex_match = re.search(r'Sex:\s*([MF])', rest)
                unit_match = re.search(r'Unit\s*#\s*(\d+)', rest)
                position_match = re.search(r'Position:\s*(\S+)', rest)
                safety_eq_match = re.search(r'Safety Eq:\s*(\S+)', rest)
                ejected_match = re.search(r'Ejected:\s*(\S+)', rest)
                extricated_match = re.search(r'Extricat(?:ed|e 2d):\s*(\S+)', rest)
                air_bag_match = re.search(r'Air Bag:\s*(\S+)', rest)
                injury_match = re.search(r'Injury:\s*(\S+)', rest)
                taken_for_match = re.search(r'Taken\s+for\s*(\S+)', rest)
                
                occupant_details.update({
                    'age': int(age_match.group(1)) if age_match else None,
                    'sex': sex_match.group(1) if sex_match else None,
                    'unit_number': unit_match.group(1) if unit_match else None,
                    'position': position_match.group(1) if position_match else None,
                    'safety_equipment': safety_eq_match.group(1) if safety_eq_match else None,
                    'ejected': ejected_match.group(1) if ejected_match else None,
                    'extricated': extricated_match.group(1) if extricated_match else None,
                    'air_bag': air_bag_match.group(1) if air_bag_match else None,
                    'injury': injury_match.group(1) if injury_match else None,
                    'taken_for_treatment': taken_for_match.group(1) if taken_for_match else None
                })
                
                # Solo agregar si tiene información válida
                if occupant_details['first_name'] or occupant_details['address']:
                    occupants.append(occupant_details)
        
        return occupants
    
    def process_pdf_to_dataframe(self, pdf_path: str) -> pd.DataFrame:
        """
        Convierte un PDF de reporte de accidente a DataFrame
        
        Args:
            pdf_path (str): Ruta al archivo PDF
            
        Returns:
            pd.DataFrame: DataFrame con toda la información del reporte
        """
        try:
            logger.info(f"Procesando PDF: {pdf_path}")
            
            # Extraer texto del PDF
            all_text = ""
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        all_text += text
            
            if not all_text.strip():
                logger.warning(f"No se pudo extraer texto del PDF: {pdf_path}")
                return pd.DataFrame()
            
            # Extraer información usando métodos mejorados
            report_details = self.extract_report_details(all_text)
            drivers = self.extract_drivers(all_text)
            occupants = self.extract_occupants(all_text)
            
            # Obtener nombre del archivo PDF (sin extensión)
            pdf_filename = Path(pdf_path).stem
            
            # Crear lista de registros para el DataFrame
            records = []
            
            # Agregar conductores
            for driver in drivers:
                record = {
                    'pdf_filename': pdf_filename,
                    'person_type': 'driver',
                    'agency_case_number': report_details.get('agency_case_number'),
                    'estimated_crash_date_time': report_details.get('estimated_crash_date_time'),
                    'narrative': report_details.get('narrative'),
                    'unit_number': driver.get('unit_number'),
                    'last_name': driver.get('last_name'),
                    'first_name': driver.get('first_name'),
                    'middle_name': driver.get('middle_name'),
                    'address': driver.get('address'),
                    'city': driver.get('city'),
                    'state': driver.get('state'),
                    'zip': driver.get('zip'),
                    'dob': driver.get('dob'),
                    'driver_license_no': driver.get('driver_license_no'),
                    'insurance_company': driver.get('insurance_company'),
                    'policy_no': driver.get('policy_no'),
                    'telephone_no': driver.get('telephone_no'),
                    'age': None,  # Mantener como None para drivers como en el original
                    'sex': None,
                    'position': None,
                    'safety_equipment': None,
                    'ejected': None,
                    'extricated': None,
                    'air_bag': None,
                    'injury': None,
                    'taken_for_treatment': None
                }
                records.append(record)
            
            # Agregar ocupantes
            for occupant in occupants:
                record = {
                    'pdf_filename': pdf_filename,
                    'person_type': 'occupant',
                    'agency_case_number': report_details.get('agency_case_number'),
                    'estimated_crash_date_time': report_details.get('estimated_crash_date_time'),
                    'narrative': report_details.get('narrative'),
                    'unit_number': occupant.get('unit_number'),
                    'last_name': occupant.get('last_name'),
                    'first_name': occupant.get('first_name'),
                    'middle_name': occupant.get('middle_name'),
                    'address': occupant.get('address'),
                    'city': None,
                    'state': None,
                    'zip': None,
                    'dob': None,
                    'driver_license_no': None,
                    'insurance_company': None,
                    'policy_no': None,
                    'telephone_no': None,
                    'age': occupant.get('age'),
                    'sex': occupant.get('sex'),
                    'position': occupant.get('position'),
                    'safety_equipment': occupant.get('safety_equipment'),
                    'ejected': occupant.get('ejected'),
                    'extricated': occupant.get('extricated'),
                    'air_bag': occupant.get('air_bag'),
                    'injury': occupant.get('injury'),
                    'taken_for_treatment': occupant.get('taken_for_treatment')
                }
                records.append(record)
            
            df = pd.DataFrame(records)
            logger.info(f"DataFrame creado con {len(df)} registros del archivo: {pdf_filename}")
            return df
            
        except Exception as e:
            logger.error(f"Error procesando PDF {pdf_path}: {str(e)}")
            return pd.DataFrame()

def convert_pdf_to_csv(pdf_path: str, csv_output_path: str) -> bool:
    """
    Función principal para convertir PDF a CSV
    
    Args:
        pdf_path (str): Ruta al archivo PDF de entrada
        csv_output_path (str): Ruta completa donde guardar el CSV
        
    Returns:
        bool: True si la conversión fue exitosa, False en caso contrario
    """
    try:
        # Verificar que el PDF existe
        if not os.path.exists(pdf_path):
            logger.error(f"Archivo PDF no encontrado: {pdf_path}")
            return False
        
        # Verificar que sea un archivo PDF
        if not pdf_path.lower().endswith('.pdf'):
            logger.error(f"El archivo no es un PDF: {pdf_path}")
            return False
        
        # Crear directorio de salida si no existe
        output_dir = os.path.dirname(csv_output_path)
        if output_dir:  # Solo crear si hay directorio especificado
            os.makedirs(output_dir, exist_ok=True)
        
        # Procesar PDF
        processor = PDFToCsvProcessor()
        df = processor.process_pdf_to_dataframe(pdf_path)
        
        if df.empty:
            logger.error(f"No se pudieron extraer datos del PDF: {pdf_path}")
            return False
        
        # Guardar CSV
        df.to_csv(csv_output_path, index=False, encoding='utf-8')
        logger.info(f"CSV generado exitosamente: {csv_output_path}")
        logger.info(f"Total de registros: {len(df)}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error convirtiendo PDF a CSV: {str(e)}")
        return False



def consolidar_driver_occupant(df: pd.DataFrame) -> pd.DataFrame:
    """
    Consolida registros de tipo 'driver' y 'occupant' en reportes de accidentes,
    combinando los datos disponibles por persona (unidad + nombre completo).
    
    Parámetros:
        df (pd.DataFrame): DataFrame original con columnas esperadas del reporte.
    
    Retorna:
        pd.DataFrame: DataFrame consolidado, sin duplicados, con datos unificados.
    """

    # Crear nombre completo estandarizado
    df["first_name"] = df["first_name"].astype(str).str.upper().str.strip()
    df["last_name"] = df["last_name"].astype(str).str.upper().str.strip()
    df["full_name"] = (df["first_name"] + " " + df["last_name"]).str.replace(r"\s+", " ", regex=True).str.strip()

    # Crear clave única por persona
    df["key"] = df["unit_number"].astype(str) + "_" + df["full_name"]

    # Ordenar para priorizar los datos del conductor
    df_sorted = df.sort_values(by="person_type", ascending=True)

    # Agrupar por clave y consolidar datos (tomar primero no nulo)
    df_merged = (
        df_sorted
        .groupby("key")
        .agg(lambda x: x.dropna().replace("", pd.NA).ffill().bfill().iloc[0] if x.dropna().any() else "")
        .reset_index(drop=True)
    )

    return df_merged



def extract_df_from_georgia(outdata_file: str) -> pd.DataFrame:
    """
    Main simple para convertir PDF a CSV
    """
    print("PROCESADOR DE REPORTES DE ACCIDENTES")
    print("=" * 40)
    
    # Pedir ruta del PDF
    pdf_path = outdata_file
    ## directorio donde van a guardarse los pdfs
    csv_directory = os.path.join(os.path.dirname(pdf_path), "processed")

    # Generar ruta del CSV con el mismo nombre que el PDF
    pdf_name = Path(pdf_path).stem  # Nombre sin extensión
    csv_path = os.path.join(csv_directory, f"{pdf_name}.csv")

    print(f"Nombres de csv: {csv_path}")
    # Procesar
    #print(f"\n Procesando...")
    print(f" PDF: {pdf_path}")
    print(f"CSV: {csv_path}")
    
    success = convert_pdf_to_csv(pdf_path, csv_path)
    
    if success:
        print(f"CSV generado exitosamente en: {csv_path}")
    else:
        print("Error procesando el PDF")
    df=pd.read_csv(rf'{csv_path}')
    df=consolidar_driver_occupant(df)

    return df
    #loader_df_to_db(df)
    #print(df)


# if __name__ == "__main__":
    # # Ejemplo de uso directo
    # pdf_file = "C:/Users/spss/OneDrive - INGELSI CIA LTDA/Documentos/SynapseIQ/data/Georgia/GeorgiaReportsUPLD/GP250023838_2025-04-05.pdf"
    # csv_file = "output/Georgia.csv"
    
    # success = convert_pdf_to_csv(pdf_file, csv_file)
    
    # if success:
    #     print(f" Conversión exitosa: {csv_file}")
    # else:
    #     print(" Error en la conversión")

