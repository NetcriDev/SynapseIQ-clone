from src.services.api_contact import DataIrisSession
from src.utils.utils_api_contact import DatabaseType
from config.config import get_connection
from src.services.api_geocode_distance import HopeCenterDistancer


## Test basic
api_distance = HopeCenterDistancer()
a = api_distance.find_nearest_center(country="USA", 
                                     state="NC", 
                                     city="SALEM", 
                                     street="500 HAVEN RIDGE DR APT 12", 
                                     address="")
print(a)
print(a[0])
## >> Fish Test