import pdfplumber
import pandas as pd
import re
import os
from typing import Tuple, Dict, List
import pdfplumber
import pandas as pd
import re
import os
from typing import Tuple, Dict, List


def extract_traffic_data_from_pdf(pdf_path: str) -> pd.DataFrame:
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"El archivo {pdf_path} no existe")

    report_number, crash_datetime, unit_in_error, dict_cars, list_people, narrative_text = _parse_pdf_content(pdf_path)
    df = _build_dataframe(list_people, dict_cars, report_number, crash_datetime, unit_in_error, narrative_text)
    df_processed = _process_dataframe(df)
    return df_processed


def _parse_pdf_content(pdf_path: str) -> Tuple[str, str, str, Dict, List, str]:
    report_number = 'N/A'
    crash_datetime = 'N/A'
    unit_in_error = 'N/A'
    dict_cars = {}
    list_people = []
    narrative_text = ''

    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                partial_text = page.extract_text()
                if not partial_text:
                    continue

                # EXTRAER NARRATIVA
                if 'NARRATIVE' in partial_text.upper() and not narrative_text:
                    match = re.search(r'NARRATIVE\s*\n(.+?)(?=\n[A-Z ]{3,}|\Z)', partial_text, re.DOTALL)
                    if match:
                        narrative_text = match.group(1).strip().replace('\n', ' ')

                # BLOQUE 1: Info básica del reporte
                if '*DENOTES MANDATORY FIELD FOR SUPPLEMENT REPORT LOCAL REPORT NUMB' in partial_text.upper():
                    report_match = re.search(r'LOCAL INFORMATION\s+.+[A-Za-z0-9-]+', partial_text)
                    report_number_list = re.findall('[A-Za-z0-9-]*\d[A-Za-z0-9-]*', report_match[0]) if report_match else []
                    report_number = report_number_list[0] if report_number_list else 'N/A'

                    datas_horas = re.finditer(r'(\d{2}/\d{2}/\d{4} \d{2}:\d{2})', partial_text)
                    posicao_report_match = re.search(r'LOCAL INFORMATION\s+(\S+)', partial_text)
                    if posicao_report_match:
                        posicao_report = posicao_report_match.start()
                        menor_distancia = float('inf')
                        for match in datas_horas:
                            posicao_data = match.start()
                            distancia = abs(posicao_data - posicao_report)
                            if distancia < menor_distancia:
                                menor_distancia = distancia
                                crash_datetime = match.group(1)

                    unit_in_error_match = re.search(r'(\d+)\s+9\s+98\s+9\s+-\s+-', partial_text)
                    unit_in_error = unit_in_error_match.group(1) if unit_in_error_match else 'N/A'

                # BLOQUE 2: Info de vehículos
                elif 'UNIT' in partial_text.upper() and 'OWNER NAME:' in partial_text.upper():
                    unit = partial_text.split('OWNER NAME:')[-1].split('\n')[1][:2].strip()
                    license_plate = ''
                    insurance_policy = ''
                    insurance_company = ''

                    content_partial = re.findall('\n.*\n.*VEHICLE MODEL.*\n.*\n', partial_text)
                    has_insurance_content = 'X VERIFIED' in str(content_partial) or 'XVERIFIED' in str(content_partial)

                    if content_partial:
                        for content_subpartial in content_partial:
                            try:
                                if not license_plate:
                                    lp_parts = content_subpartial.strip().split('\n')[0].split(' ')
                                    license_plate = lp_parts[1] if len(lp_parts) > 1 and lp_parts[1].strip() != 'STATE' else ''
                                    if not license_plate:
                                        continue

                                if has_insurance_content and not insurance_policy:
                                    policy_info = content_subpartial.strip().split('\n')[0].split(license_plate)[1].strip() if license_plate else ''
                                    year_match = re.findall(r'\d{4}', policy_info)
                                    year = year_match[-1] if year_match else ''

                                    policy_split = content_subpartial.split('X VERIFIED')
                                    if len(policy_split) > 1:
                                        policy_details = policy_split[-1].strip()
                                        insur_number_match = re.search(r' \w*\d\w* ', policy_details)
                                        insur_number = insur_number_match.group(0).strip() if insur_number_match else ''

                                        if insur_number:
                                            try:
                                                policy_text = policy_details.strip()
                                                insurance_company = policy_text.split(insur_number)[0].strip()
                                                tail = policy_text.split(insurance_company)[-1].strip()
                                                first_token = tail.split()[0] if tail else ''
                                                if re.search(r'\d{6,}', first_token):
                                                    insurance_policy = first_token
                                            except:
                                                insurance_company = 'N/A'
                                                insurance_policy = 'N/A'
                                break
                            except:
                                pass

                    dict_cars[unit] = {
                        'license_plate': license_plate if license_plate else 'N/A',
                        'insurance_policy': insurance_policy if insurance_policy else 'N/A',
                        'insurance_company': insurance_company if insurance_company else 'N/A'
                    }

                # BLOQUE 3: Personas
                elif ('OTORIST / ON- OTORIST' in partial_text.upper()) or ('ITNESS' in partial_text.upper() and 'DDENDUM' in partial_text.upper()):
                    person_type = "DRIVER" if 'OTORIST / ON- OTORIST' in partial_text.upper() else "OCCUPANT"
                    regex = r"UNIT # NAME: LAST, FIRST, MIDDLE DATE OF BIRTH AGE GENDER\n(\d)+\s+([^,]+),\s+([^,\n]+)(?:,\s+([^,\n]+))?\s+(\d{2}/\d{2}/\d{4})\s+(\d+)\s+([MF])\nADDRESS: STREET, CITY, STATE, ZIP CONTACT PHONE - INCLUDE AREA CODE\n([^\n]+)"
                    matches = re.findall(regex, partial_text)

                    for match in matches:
                        unit, last_name, first_name, middle_name, dob, age, gender, address = match
                        list_people.append({
                            'unit': unit.strip(),
                            'last_name': last_name.strip(),
                            'first_name': first_name.strip(),
                            'middle_name': middle_name.strip() if middle_name else '',
                            'dob': dob.strip(),
                            'age': age.strip(),
                            'gender': gender.strip(),
                            'address': address.strip(),
                            'person_type': person_type.strip(),
                        })

    except Exception as e:
        print(f"Error procesando el PDF {pdf_path}: {e}")

    return report_number, crash_datetime, unit_in_error, dict_cars, list_people, narrative_text


def _build_dataframe(list_people: List, dict_cars: Dict, report_number: str, crash_datetime: str, unit_in_error: str, narrative_text: str) -> pd.DataFrame:
    columns = [
        "TYPE", "Accident Report Number", "Crash Date", "Unit", "Unit at Fault",
        "Name", "Birth", "Age", "Gender", "Address", "License Plate",
        "Insurance Policy", "Insurance Company", "Narrative"
    ]

    df_final = pd.DataFrame(columns=columns)
    list_cars_found = []

    for person in list_people:
        unit = person['unit']
        license_plate = ''
        insurance_policy = ''
        insurance_company = ''

        if unit in dict_cars:
            list_cars_found.append(unit)
            license_plate = dict_cars[unit]['license_plate']
            insurance_policy = dict_cars[unit]['insurance_policy']
            insurance_company = dict_cars[unit]['insurance_company']

        name = " ".join([
            person['first_name'],
            person['middle_name'] if person['middle_name'] else '',
            person['last_name']
        ]).strip()

        df_final.loc[len(df_final)] = [
            person['person_type'],
            report_number,
            crash_datetime,
            unit,
            unit_in_error,
            name,
            person['dob'],
            int(person['age']) if person['age'].isdigit() else None,
            person['gender'],
            person['address'],
            license_plate,
            insurance_policy,
            insurance_company,
            narrative_text
        ]

    for unit, car_info in dict_cars.items():
        if unit not in list_cars_found:
            df_final.loc[len(df_final)] = [
                '', report_number, crash_datetime, unit, unit_in_error,
                '', '', None, '', '',
                car_info['license_plate'], car_info['insurance_policy'], car_info['insurance_company'],
                narrative_text
            ]

    return df_final


def _process_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    def preencher_policy_company(grupo):
        unit_at_fault = grupo['Unit at Fault'].iloc[0]
        culpado = grupo[grupo['Unit'] == unit_at_fault]
        policy = culpado['Insurance Policy'].iloc[0] if not culpado.empty else None
        company = culpado['Insurance Company'].iloc[0] if not culpado.empty else None
        grupo['Unit at Fault Policy'] = policy
        grupo['Unit at Fault Company'] = company
        return grupo

    df = df[df['TYPE'].str.strip() != '']
    df = df[~df['Unit at Fault'].isin(['98', '99', 98, 99])]
    return df.groupby('Accident Report Number', group_keys=False).apply(preencher_policy_company)

pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
pd.set_option('display.max_colwidth', None)



# import pandas as pd
# import psycopg2
# from datetime import datetime


# path= "/Users/cristianb/Documents/Python/rel8ed/Data/ohio/Dayton_Ohio.pdf"
# df = extract_traffic_data_from_pdf(path)
# #print(df)
# print(df[["Unit","License Plate","Insurance Company","Insurance Policy"]])
# df.to_csv('/Users/cristianb/Documents/Python/rel8ed/Data/ohio/out_put4.csv',index=False)

