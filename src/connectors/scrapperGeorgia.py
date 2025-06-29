import re
import pandas as pd
import pdfplumber
import os
from typing import Dict, List, Union
import logging
from pathlib import Path
#from src.parsers.loaderGeorgia import loader_df_to_db


# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PDFToCsvProcessor:
    """
    Clase para procesar reportes de accidentes de PDF a CSV
    """
    
    def __init__(self):
        self.blacklist_words = {"BIKE", "ADDRESS", "PED", "UNKNOWN"}
    
    def clean_value(self, value: Union[str, None]) -> Union[str, None]:
        """Limpia valores eliminando palabras de la blacklist"""
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return None
            words = value.split()
            cleaned = [w for w in words if w.upper() not in self.blacklist_words]
            return " ".join(cleaned) if cleaned else None
        return value
    
    def extract_report_details(self, pdf_text: str) -> Dict:
        """Extrae detalles básicos del reporte"""
        report_data = {}
        
        # Número de caso
        agency_case_match = re.search(r"Agency Case Number.*?(\bGP\d+\b)", pdf_text, re.DOTALL)
        report_data['agency_case_number'] = agency_case_match.group(1) if agency_case_match else None
        
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
        
        # Narrativa
        narrative_match = re.search(
            r"NARRATIVE\s*\n(.*?)(?=\nDIAGRAM|\nADMINISTRATIVE|\nSUPPLEMENT|\nGDOT-523|\Z)",
            pdf_text, re.DOTALL
        )
        if narrative_match:
            narrative_text = narrative_match.group(1).strip()
            narrative_text = re.sub(r"Page _\d+__ of _\d+__\s*", "", narrative_text).strip()
            narrative_text = re.sub(r"\n\s*\n", "\n", narrative_text).strip()
            report_data['narrative'] = narrative_text
        else:
            report_data['narrative'] = None
            
        return report_data
    
    def extract_drivers(self, pdf_text: str) -> List[Dict]:
        """Extrae información de conductores"""
        drivers = []
        drivers_dict = {}
        
        unit_block_pattern = re.compile(
            r"(Unit # Driver LAST NAME FIRST MIDDLE\s*(?:Unit # Driver LAST NAME FIRST MIDDLE\s*)?\n.*?)" +
            r"(?=\n*COMMERCIAL MOTOR VEHICLES ONLY|\n*OCCUPANT INFORMATION|ADMINISTRATIVE|SUPPLEMENT|GDOT-523|\Z)",
            re.DOTALL
        )
        
        for block_match in unit_block_pattern.finditer(pdf_text):
            current_block_text = block_match.group(1)
            
            name_line_match = re.search(
                r"Unit # Driver LAST NAME FIRST MIDDLE\s*\n"
                r"(?P<left_unit_num>\d+)\s+Ped\s+(?P<left_last>\S+)\s+(?P<left_first>\S+)(?:\s+(?P<left_middle>(?!\d+\s+Ped)\S+))?"
                r"(?:\s+(?P<right_unit_num>\d+)\s+Ped\s+(?P<right_last>\S+)\s+(?P<right_first>\S+)(?:\s+(?P<right_middle>\S+))?)?",
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
                    "middle_name": self.clean_value(name_line_match.group("left_middle")) if name_line_match.group("left_middle") and name_line_match.group("left_middle").istitle() else ""
                }
                drivers_dict[ul] = left_driver
                drivers.append(left_driver)
                current_block_unit_numbers.append(ul)
                
                # Conductor derecho (si existe)
                if name_line_match.group("right_unit_num"):
                    ur = name_line_match.group("right_unit_num")
                    right_driver = {
                        "unit_number": ur,
                        "last_name": self.clean_value(name_line_match.group("right_last")),
                        "first_name": self.clean_value(name_line_match.group("right_first")),
                        "middle_name": self.clean_value(name_line_match.group("right_middle")) if name_line_match.group("right_middle") and name_line_match.group("right_middle").istitle() else ""
                    }
                    drivers_dict[ur] = right_driver
                    drivers.append(right_driver)
                    current_block_unit_numbers.append(ur)
            
            # Extraer información adicional
            self._extract_additional_driver_info(current_block_text, drivers_dict, current_block_unit_numbers)
        
        return sorted(drivers_dict.values(), key=lambda x: int(x['unit_number']))
    
    def _extract_additional_driver_info(self, block_text: str, drivers_dict: Dict, unit_numbers: List[str]):
        """Extrae información adicional de conductores"""
        # Dirección
        addr_match = re.search(
            r"Bike Address\s*(\d+)\s*(.+?)(?:Bike Address\s*(\d+)\s*(.+?))?\s*\n",
            block_text, re.DOTALL
        )
        if addr_match:
            g1, g2, g3, g4 = addr_match.group(1), addr_match.group(2), addr_match.group(3), addr_match.group(4)
            if g1 in drivers_dict: 
                drivers_dict[g1]['address'] = self.clean_value(g2)
            if g3 and g3 in drivers_dict: 
                drivers_dict[g3]['address'] = self.clean_value(g4)
        
        # Ciudad, estado, zip, fecha de nacimiento
        city_dob_match = re.search(
            r"City State Zip DOB\s*\n\s*(\S+)\s+(\S+)\s+(\S+)\s+(\d{2}/\d{2}/\d{4})"
            r"(?:\s+(\S+)\s+(\S+)\s+(\S+)\s+(\d{2}/\d{2}/\d{4}))?",
            block_text
        )
        if city_dob_match and unit_numbers:
            ul = unit_numbers[0]
            drivers_dict[ul].update({
                'city': self.clean_value(city_dob_match.group(1)),
                'state': city_dob_match.group(2),
                'zip': city_dob_match.group(3),
                'dob': city_dob_match.group(4)
            })
            if len(unit_numbers) > 1 and city_dob_match.group(5):
                ur = unit_numbers[1]
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
            drivers_dict[ul]['driver_license_no'] = dl_match.group(1)
            if len(unit_numbers) > 1 and dl_match.group(2):
                ur = unit_numbers[1]
                drivers_dict[ur]['driver_license_no'] = dl_match.group(2)
        
        # Información del seguro
        ins_match = re.search(
            r"Insurance Co\. Policy No\. Telephone No\.\s*\n\s*(.+?)\s+(\S+)\s+\((\d{3})\)\s*(\d{3}-\d{4})"
            r"(?:\s+(.+?)\s+(\S+)\s+\((\d{3})\)\s*(\d{3}-\d{4}))?",
            block_text
        )
        if ins_match and unit_numbers:
            ul = unit_numbers[0]
            drivers_dict[ul].update({
                'insurance_company': self.clean_value(ins_match.group(1)),
                'policy_no': ins_match.group(2),
                'telephone_no': f"({ins_match.group(3)}) {ins_match.group(4)}"
            })
            if len(unit_numbers) > 1 and ins_match.group(5):
                ur = unit_numbers[1]
                drivers_dict[ur].update({
                    'insurance_company': self.clean_value(ins_match.group(5)),
                    'policy_no': ins_match.group(6),
                    'telephone_no': f"({ins_match.group(7)}) {ins_match.group(8)}"
                })
    
    def extract_occupants(self, pdf_text: str) -> List[Dict]:
        """Extrae información de ocupantes"""
        occupants = []
        
        occupant_sections_matches = re.finditer(
            r"(OCCUPANT INFORMATION|ADDITIONAL OCCUPANT INFORMATION)\s*\n(.*?)(?=\nADMINISTRATIVE|\nSUPPLEMENT|\nGDOT-523|\Z)",
            pdf_text, re.DOTALL
        )
        
        occupant_entry_pattern = re.compile(
            r"Name \(Last, First\):\s*(?P<full_name>[^\n]+?)\s*Address:\s*(?P<address>[^\n]+)\s*\n"
            r"Age:\s*(?P<age>\d+)\s+Sex:\s*(?P<sex>\S+)\s+Unit\s+#\s*(?P<unit_num>\d+)\s+Position:\s*(?P<position>\S+)\s+Safety\s+Eq:\s*(?P<safety_eq>\S+)\s+Ejected:(?P<ejected>\S+)\s+Extricated:\s*(?P<extricated>\S+)\s+Air\s+Bag:(?P<air_bag>\S+)\s+Injury:(?P<injury>\S+)\s+Taken\s+for\s*(?P<taken_for>[^\n]+?)\s*\n"
            r"(?P<treatment_line>.*?)(?=(?:Name \(Last, First\):|Injured Taken To:|Injured Taken To: By:|Age:|\Z))",
            re.DOTALL
        )
        
        for section_match in occupant_sections_matches:
            occupant_section_text = section_match.group(2)
            
            for occupant_match in occupant_entry_pattern.finditer(occupant_section_text):
                occupant_details = {}
                full_name_str = occupant_match.group('full_name').strip()
                
                if ',' in full_name_str:
                    parts = [s.strip() for s in full_name_str.split(',', 1)]
                    occupant_details['last_name'] = self.clean_value(parts[0])
                    occupant_details['first_name'] = self.clean_value(parts[1])
                else:
                    name_parts = full_name_str.split()
                    if len(name_parts) > 1:
                        occupant_details['last_name'] = self.clean_value(name_parts[-1])
                        occupant_details['first_name'] = self.clean_value(' '.join(name_parts[:-1]))
                    else:
                        occupant_details['last_name'] = None
                        occupant_details['first_name'] = self.clean_value(full_name_str)
                
                occupant_details.update({
                    'address': self.clean_value(occupant_match.group('address')),
                    'age': int(occupant_match.group('age')),
                    'sex': occupant_match.group('sex'),
                    'unit_number': occupant_match.group('unit_num'),
                    'position': occupant_match.group('position'),
                    'safety_equipment': occupant_match.group('safety_eq'),
                    'ejected': occupant_match.group('ejected'),
                    'extricated': occupant_match.group('extricated'),
                    'air_bag': occupant_match.group('air_bag'),
                    'injury': occupant_match.group('injury'),
                    'taken_for_treatment': occupant_match.group('taken_for').strip().split(' ')[0] if occupant_match.group('taken_for').strip() else None
                })
                
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
            logger.info(f"...Procesando PDF: {pdf_path}")
            
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
            
            # Extraer información
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
                    'age': None,
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
                    'middle_name': None,
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
            logger.error(f"Exception - Error procesando PDF {pdf_path}: {str(e)}")
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