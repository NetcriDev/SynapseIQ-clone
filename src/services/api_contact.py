

import httpx
from datetime import datetime, timedelta
from typing import Optional, List, Dict

BASE_URL = "https://www.datairis.co/V1"
ACCESS_TOKEN = "1f1cb-be386-49d3"  # Este es el token fijo de acceso de app

# Credenciales
CREDENTIALS = {
    "SubscriberID": "249",
    "subscriberUsername": "rel8edsub",
    "SubscriberPassword": "95GiYIhghsjCfUQW0Q7d",
    "AccountUsername": "rel8edapp",
    "AccountPassword": "reference",
    "AccountDetailsRequired": "true"
}

from enum import Enum
class DatabaseType(Enum):
    consumer = 1
    business = 2
    cellphone = 3
    newbusiness = 4
#print(DatabaseType(2).name)


class DataIrisSession:
    def __init__(self):
        self.token_id = None
        self.token_expiration = None

    def authenticate(self):
        """Solicita un nuevo token y almacena hora de expiración estimada"""
        url = f"{BASE_URL}/auth/subscriber/?AccessToken={ACCESS_TOKEN}"
        response = httpx.get(url, headers=CREDENTIALS)
        response.raise_for_status()

        data = response.json()
        self.token_id = data["Response"]["responseDetails"]["TokenID"]
        self.token_expiration = datetime.now() + timedelta(hours=8)
        print(" Token obtenido:", self.token_id)

    def is_token_valid(self):
        """Verifica si el token actual aún es válido"""
        return self.token_id is not None and datetime.now() < self.token_expiration

    def ensure_authenticated(self):
        """Valida el token y lo renueva si es necesario"""
        if not self.is_token_valid():
            print("Token expirado o inexistente. Reautenticando...")
            self.authenticate()

    def reset_criteria(self, database_type: str):
        self.ensure_authenticated()
        url = f"{BASE_URL}/criteria/search/deleteall/{database_type}"
        response = httpx.delete(url, headers={"TokenID": self.token_id})
        response.raise_for_status()

    def add_criteria(self, database_type: str, filters: dict):
        self.ensure_authenticated()
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

    def get_metadata(self, database_type: str):
        self.ensure_authenticated()
        url = f"{BASE_URL}/search/metadata/{database_type}"
        headers = {"TokenID": self.token_id}
        response = httpx.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    
    def json_to_table_consumer(self, data: dict) -> pd.DataFrame:
        """
        Convierte el JSON de resultados de búsqueda de DataIris a una tabla.
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
        first_name: str,
        last_name: str,
        middle_name: str,
        age: Optional[int] = None,
        state: Optional[str] = None,
        city: Optional[str] = None,
        gender: Optional[str] = None,
        start: int = 1,
        end: int = 10
    ) -> List[Dict[str, str]]:
        self.ensure_authenticated()
        # 1. Reset previous criteria
        reset_criteria(database_type)

        # 2. Prepare filters
        filters = {
            "First_Name": first_name,
            "Last_Name": last_name,
            "Middle_Initial": middle_name
        }

        if state:
            filters["Physical_State"] = state
        if city:
            filters["Physical_City"] = city
        if gender:
            filters["Ind_Gender_Code"] = gender.upper()
        if age:
            filters["Ind_Age"] = f"{age-2},{age-1},{age},{age+1},{age+2}"

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
                "Address": fields.get("Physical_Address", ""),
                "City": fields.get("Physical_City", ""),
                "State": fields.get("Physical_State", ""),
                "Zip": fields.get("Physical_Zip", ""),
                "Phone": fields.get("Phone", ""),
                "CellPhone": fields.get("CellPhone", "")
            })
        return resultados

    def obtener_detalle_registro(self, database_type: str, field_name: str = "id", field_value: str = None) -> dict:
        """
        Devuelve el detalle completo de un registro único en la base de datos especificada.
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
        
    detalle = obtener_detalle_registro(
        database_type="consumer",
        field_name="Id",
        field_value="15002006660373"
    )

    for campo in detalle["recordDetailFields"]:
        print(f"{campo['fieldID']:30} => {campo['fieldValue']}")

    
    @staticmethod
    def imprimir_registros_consumer(data: dict):
        for i, registro in enumerate(data, start=1):
            print(f"\n Registro #{i}")
            for campo in registro.get("resultFields", []):
                field = campo.get("fieldID", "")
                valor = campo.get("fieldValue", "")
                print(f"{field:30} : {valor}")



session = DataIrisSession()
# 1. Autenticarse y limpiar filtros anteriores
session.reset_criteria("consumer")
filtros = {
        "First_Name": "Javier",
        "Last_Name": "Padron",
        "Middle_Initial": "S",
        "Ind_Age": "69,70,71,72,73",
        "Physical_State": "IL",
        "Physical_City": "Danville",
        "Ind_Gender_Code": "M"
    }

session.add_criteria("consumer", filtros)
resultado = session.get_results("consumer")
registros = resultado["Response"]["responseDetails"]["SearchResult"]["searchResultRecord"]

DataIrisSession.imprimir_registros_consumer(registros)