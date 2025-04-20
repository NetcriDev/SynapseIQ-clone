
import httpx
import json
import time
import re, os, sys
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from config.config_api_contact import BASE_URL, ACCESS_TOKEN, CREDENTIALS
from typing import Union, Optional
from src.utils.utils_api_contact import extract_initial, lookup_data_state, normalize_gender, normalize_state
from src.utils.logger_config import setup_logger

main_script_path = sys.path[0]
logger = setup_logger("Session_api_contact", main_script_path)

class DataIrisSession:

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(DataIrisSession, cls).__new__(cls)
        return cls._instance

    def __init__(self, token: str = None, token_file_path: str = None):
        """
        token_file_path: is path a file. For example, '/home/SynapseIQ/config/json_token.json'
        """
        if hasattr(self, '_initialized') and self._initialized:
            return
        self._initialized = True
        self.token_id = token
        self.token_expiration = None
        self.token_file_path = token_file_path
        if token:
            self.token_expiration = datetime.now() + timedelta(hours=8)

    def authenticate(self):
        """
        Requests a new token and stores estimated expiration time.
        Optionally saves token and expiration in a JSON file if path is given.
        """
        url = f"{BASE_URL}/auth/subscriber/?AccessToken={ACCESS_TOKEN}"
        response = httpx.get(url, headers=CREDENTIALS)
        response.raise_for_status()

        data = response.json()
        self.token_id = data["Response"]["responseDetails"]["TokenID"]
        self.token_expiration = datetime.now() + timedelta(hours=10)

        logger.info("Token obtained:", self.token_id)

        if self.token_file_path:
            with open(self.token_file_path, "w") as f:
                json.dump({
                    "token_id": self.token_id,
                    "token_expiration": self.token_expiration.isoformat()
                }, f)

    def is_token_valid(self):
        """Check if the current token is still valid"""
        return self.token_id is not None and self.token_expiration and datetime.now() < self.token_expiration


    def ensure_authenticated(self):
        """
        Validates token. If a valid path is given, loads the token from file and reuses it if valid.
        If invalid or expired, re-authenticates and updates the file.
        """
        if self.token_id is not None and self.token_expiration is not None:
            if not self.is_token_valid():
                self.authenticate()
        elif self.token_file_path and os.path.exists(self.token_file_path):
            try:
                with open(self.token_file_path, "r") as f:
                    data = json.load(f)
                    token = data.get("token_id")
                    expiration_str = data.get("token_expiration")
                    expiration = datetime.fromisoformat(expiration_str) if expiration_str else None

                    if token and expiration and datetime.now() < expiration:
                        self.token_id = token
                        self.token_expiration = expiration
                        return
                    else:
                        logger.error("Token missing or expired. Reauthenticating...")
                        self.authenticate()
            except Exception as e:
                logger.error("Error reading token file. Reauthenticating...", str(e))
        else:
            logger.error("Token missing or expired. Reauthenticating...")
            self.authenticate()

    def reset_criteria(self, database_type: str):
        self.ensure_authenticated()
        url = f"{BASE_URL}/criteria/search/deleteall/{database_type}"
        response = httpx.delete(url, headers={"TokenID": self.token_id})
        response.raise_for_status()

    def add_criteria(self, database_type: str, filters: dict, reset_cri: bool = True):
        self.ensure_authenticated()
        if reset_cri:
            self.reset_criteria({database_type})
        url = f"{BASE_URL}/criteria/search/addall/{database_type}"
        response = httpx.put(url, headers={"TokenID": self.token_id}, json=filters)
        response.raise_for_status()

    def get_results(self, database_type: str, start: int = 1, end: int = 5): 
        self.ensure_authenticated()
        url = f"{BASE_URL}/search/{database_type}?Start={start}&End={end}"
        response = httpx.get(url, headers={"TokenID": self.token_id})
        response.raise_for_status()
        return response.json()
    
    def get_count_consumer(self) -> int:
        self.ensure_authenticated()
        url = f"{BASE_URL}/search/count/consumer"
        response = httpx.get(url, headers={"TokenID": self.token_id})
        response.raise_for_status()
        return int(response.json()["Response"]["responseDetails"]["SearchCount"])

    def get_metadata(self, database_type: str, summary: bool = True):
        """
        Gets the list of fields available for searches in a specific database type.
        """
        self.ensure_authenticated()
        url = f"{BASE_URL}/search/metadata/{database_type}"
        headers = {"TokenID": self.token_id}
        response = httpx.get(url, headers=headers)
        response.raise_for_status()

        if summary:
            metadata = response.json()["Response"]["responseDetails"]["Metadata"]
            campos = []
            for campo in metadata:
                campos.append({
                    "fieldID": campo.get("id"),
                    "fieldAlias": campo.get("dbFieldAliasName"),
                    "nombre": campo.get("displayName", {}).get("value", ""),
                    "tipo": campo.get("dataType", ""),
                    "esOculto": campo.get("isHiddenField", {}).get("value", "") == "true",
                    "esBuscable": bool(campo.get("queryExpression", {}).get("queryFormatExpression"))
                })
            return campos
        return response.json()

    def json_to_table_consumer(self, data: dict) -> pd.DataFrame:
        """
        Converts DataIris search results JSON to a table.
        """
        records = data["Response"]["responseDetails"]["SearchResult"]["searchResultRecord"]
        rows = []

        for record in records:
            row = {field["fieldID"]: field["fieldValue"] for field in record["resultFields"]}
            rows.append(row)

        df = pd.DataFrame(rows)
        return df

    def search_person_by_name(self,
        database_type: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        middle_name: Optional[str] = None,
        age: Optional[Union[int, str]] = None,
        state: Optional[str] = None,
        city: Optional[str] = None,
        gender: Optional[str] = None,
        start: int = 1,
        end: int = 10
    ) -> List[Dict[str, str]]:
        """
        All 'null-like' values (e.g., 'null', 'NULL', '', ' ') are treated as None.
        """
        
        self.ensure_authenticated()
        # 1. Reset previous criteria
        self.reset_criteria(database_type)

        def clean(value):
            if isinstance(value, str) and value.strip().lower() in {"null", "", " ", ".", ","}:
                return None
            return value

        # Normalize all inputs
        first_name = clean(first_name)
        last_name = clean(last_name)
        middle_name = clean(middle_name)
        #print(f"middle name: {middle_name}")
        state = clean(state)
        city = clean(city)
        gender = clean(gender)
        age = None if isinstance(age, str) and age.strip().lower() in {"null", ""} else age

        # 2. Prepare filters
        filters = {}

        if first_name:
            filters["First_Name"] = first_name
        if last_name:
            filters["Last_Name"] = last_name
        if middle_name:
            filters["Middle_Initial"] = extract_initial(middle_name)
        if state:
            filters["Physical_State"] = normalize_state(state,lookup_data=lookup_data_state)
        if city:
            filters["Physical_City"] = city
        if gender:
            filters["Ind_Gender_Code"] = normalize_gender(gender.upper())
        if age:
            filters["Ind_Age"] = f"{int(age)-2},{int(age)-1},{int(age)},{int(age)+1}"

        logger.info(f"filters:{filters}")
        # 3. Enviar criterios
        self.add_criteria(database_type,filters)

        # 4. Obtener resultados
        data = self.get_results(database_type,start,end)

        # 5. Procesar resultados y extraer dirección y teléfonos
        try:
            registros = data["Response"]["responseDetails"]["SearchResult"]["searchResultRecord"]
        except KeyError:
            return []
        
        resultados = []

        for registro in registros:
            fields = {f["fieldID"]: f["fieldValue"] for f in registro.get("resultFields", [])}
            resultados.append({
                "Id": fields.get("Id", ""),
                "First_Name": fields.get("First_Name", ""),
                "Last_Name": fields.get("Last_Name", ""),
                "Middle_Initial": fields.get("Middle_Initial", ""),
                "Address": fields.get("Physical_Address", ""),
                "City": fields.get("Physical_City", ""),
                "State": fields.get("Physical_State", ""),
                "Zip": fields.get("Physical_Zip", ""),
                "Phone": fields.get("Phone", ""),
                "CellPhone": fields.get("CellPhone", ""),
                "Gender": fields.get("Ind_Gender_Code", ""),
                "Email": fields.get("Email", ""),
                "Age": fields.get("Ind_Age", "")
            })
        return resultados

    def get_record_detail(self, database_type: str, field_name: str = "id", field_value: str = None) -> dict:
        """ 
        Returns the full details of a single record in the specified database.
        """
        self.ensure_authenticated()

        url = f"{BASE_URL}/search/recordDetail/{database_type}/{field_name}/{field_value}"
        headers = {"TokenID": self.token_id}

        response = httpx.get(url, headers=headers)

        if response.status_code == 200:
            return response.json()["Response"]["responseDetails"]
        elif response.status_code == 401:
            raise Exception("Token inválido o expirado.")
        elif response.status_code == 404:
            raise Exception(f"Registro no encontrado para {field_name} = {field_value}.")
        else:
            raise Exception(f"Error {response.status_code}: {response.text}")
        
        # detalle = obtener_detalle_registro(
        #     database_type="consumer",
        #     field_name="Id",
        #     field_value="15002006660373"
        # )

        # for campo in detalle["recordDetailFields"]:
        #     print(f"{campo['fieldID']:30} => {campo['fieldValue']}")


    def get_lookup_values(self, database_type: str, field: str, value: str = " ", start: int = 0, end: int = 100) -> list:
        """
        Query valid values ​​for a search field (e.g. Physical_State, Physical_City).
        """
        url = (
            f"{BASE_URL}/lookup/metadata/{database_type}"
            f"?Search={field}&Field={value}&Start={start}&End={end}"
        )
        self.reset_criteria(database_type)
        headers = {"TokenID": self.token_id}
        response = httpx.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data


    def get_contact_resolution(
        self,
        database_type: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        middle_name: Optional[str] = None,
        age: Optional[Union[int, str]] = None,
        state: Optional[str] = None,
        city: Optional[str] = None,
        gender: Optional[str] = None,
        start: int = 1,
        end: int = 10
    ) -> dict:
        """
        Performs a contact resolution search on the DataIRIS API and returns a summary result.

        Rules:
        - 'state' is mandatory.
        - At least 2 of the following criteria must be provided: first_name, last_name, middle_name.
        - At least 1 of the following criteria must also be provided: age, city, or gender.

        Returns:
            dict: {
                "record_count": int,
                "sufficient_criteria": bool,
                "result": list
            }
        """
        # Criteria validation
        name_fields = [first_name, last_name, middle_name]
        optional_fields = [age, city, gender]
        valid_names = sum(1 for val in name_fields if val)
        has_optional = any(val is not None for val in optional_fields)
        state_valid = state is not None

        sufficient_criteria = valid_names >= 2 and has_optional and state_valid

        if not state_valid:
            raise ValueError("The 'state' field is required to perform a search.")

        result = self.search_person_by_name(
            database_type=database_type,
            first_name=first_name,
            last_name=last_name,
            middle_name=middle_name,
            age=age,
            state=state,
            city=city,
            gender=gender,
            start=start,
            end=end
        )
        logger.info(result)
        return {
            "record_count": len(result),
            "sufficient_criteria": sufficient_criteria,
            "result": result
        }
        
    def safe_get_contact_resolution(self, 
        database_type: str, 
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        middle_name: Optional[str] = None,
        age: Optional[Union[int, str]] = None,
        state: Optional[str] = None,
        city: Optional[str] = None,
        gender: Optional[str] = None,
        start: int = 1,
        end: int = 10) -> Optional[dict]:

        """
        Intenta ejecutar get_contact_resolution hasta max_retries veces con pausa entre intentos.

        Args:
            session (DataIrisSession): instancia válida.
            max_retries (int): número máximo de reintentos.
            wait_seconds (int): segundos de espera entre cada intento.
            **kwargs: parámetros que se pasan a get_contact_resolution.

        Returns:
            dict: resultado si tiene éxito, o None si todos los intentos fallan.
        """
        self.ensure_authenticated()
        max_retries=4
        wait_seconds=2

        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"tried #{attempt}...")
                return self.get_contact_resolution(database_type,
                                                   first_name,
                                                   last_name,
                                                   middle_name,
                                                   age,
                                                   state,
                                                   city,
                                                   gender,
                                                   start,
                                                   end
                                                   )
            except Exception as e:
                logger.error(f"failed attempt #{attempt}...")
                if attempt < max_retries:
                    time.sleep(wait_seconds)
        return None


    @staticmethod
    def print_consumer_records(data: dict):
        """
        Prints to console the search results from the 'consumer' database.

        This function iterates over a list of records retrieved from the DataIRIS API,
        specifically from the 'searchResultRecord' field, and displays each available 
        field from 'resultFields' in a readable format.

        Args:
            data (dict): List of records returned by the DataIRIS search anda 'consumer'.
                        Each element must contain a dictionary with a 'resultFields' key,
                        which is a list of fields including 'fieldID' and 'fieldValue'.

        Output:
            Prints to the console the content of each field per record, 
            numbering them in increasing order (Record #1, #2, ...).
        """
        for i, registro in enumerate(data, start=1):
            print(f"\n Registro #{i}")
            for campo in registro.get("resultFields", []):
                field = campo.get("fieldID", "")
                valor = campo.get("fieldValue", "")
                print(f"{field:30} : {valor}")
    
    @staticmethod
    def extract_phone_if_valid(data: dict) -> dict:
        """
        Returns phone and cellphone from the first result if conditions are met:
        - record_count <= 5
        - sufficient_criteria == True
        - result not empty
        """
        if not data or not isinstance(data, dict):
            return {
                    "CellPhone": None,
                    "Phone": None,
                    "contact_resolution": None
                }
        
        if data.get("record_count") == 0:
            return {
                    "CellPhone": None,
                    "Phone": None,
                    "contact_resolution": "[]"
                }

        if data.get("record_count", 0) <= 5 and data.get("sufficient_criteria") is True:
            results = data.get("result", [])
            if results:
                first = results[0]
                return {
                    "CellPhone": first.get("Phone", ""),
                    "Phone": first.get("CellPhone", ""),
                    "contact_resolution": data.get("result", [])
                }
        return {
                    "CellPhone": None,
                    "Phone": None,
                    "contact_resolution": None
                }