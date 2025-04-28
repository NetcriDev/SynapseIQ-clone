from src.services.api_contact import DataIrisSession
from src.utils.utils_api_contact import DatabaseType
from config.config import get_connection
from src.services.api_geocode_distance import HopeCenterDistancer
#sesion = DataIrisSession(token_file_path="/Users/cristianb/Documents/Python/rel8ed/SynapseIQ_staging/config/token.json")
sesion = DataIrisSession(token_file_path="/home/SynapseIQ/config/token.json")

################ Test to Api Contact ################

#### Test 1

filtros = {
        "First_Name": "Catherine",
        "Last_Name": "Hawkins",
        "Middle_Initial": "C",
        "Ind_Age": "76",
        "Physical_State": "NC",
        "Physical_City": "CLEMMONS",
        "Ind_Gender_Code": "F"
    }


a=DataIrisSession.extract_phone_if_valid(
    sesion.safe_get_contact_resolution(
        database_type=DatabaseType(1).name,
        first_name=filtros.get("First_Name"), 
        last_name=filtros.get("Last_Name"),
        middle_name="C",
        age="75",
        state=filtros.get("Physical_State")))
print(a)

## Test 2
#Creed, Curk Bradley
filters={'First_Name': 'Martin', 'Last_Name': 'Wells', 'Middle_Initial': 'S', 'Physical_State': 'KS', 'Ind_Age': '60,61,62,63'}
a= sesion.safe_get_contact_resolution(
        database_type=DatabaseType(1).name,
        first_name="Curk", 
        last_name="Creed",
        middle_name="Bradley",
        age="64",
        state="KS")
print(a)




########## test api distance ##########
# api_distance = HopeCenterDistancer()
# a = api_distance.find_nearest_center(country="USA", state="Ohio", city="Dayton", street="575 Andrea Ct")
# print(a)