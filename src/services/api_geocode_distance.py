import psycopg2
import requests
from typing import List, Tuple, Optional
from geopy.distance import geodesic

API_KEY_1 = "5b3ce3597851110001cf6248d00b6552c19b4cf0b097ade3c0908959" 
API_KEY_2 = "5b3ce3597851110001cf6248dfb20be472f14bae85fb58b843205878" #(jhon)

class HopeCenterDistancer:
    def __init__(self, conn: Optional[psycopg2.extensions.connection] = None):
        self.api_key1 = API_KEY_1
        self.api_key2 = API_KEY_2 
        self.conn = conn
        if not conn:
            self.conn = psycopg2.connect(
                dbname="crash_records_001",
                user="synapseiq",
                password="SynapseIQ$2025",
                host="localhost",
                port="5432"
            )

    def try_geocode_address(self, address: str, api_key: str = None) -> Optional[List[float]]:
        if api_key:
            self.api_key1 = api_key
        try:
            response = requests.get(
                "https://api.openrouteservice.org/geocode/search",
                params={"api_key": self.api_key1, "text": address},
                timeout=5
            )
            response.raise_for_status()
            data = response.json()
            if data.get("features"):
                return data["features"][0]["geometry"]["coordinates"]
            else:
                print(f"No coordinates found for the address: {address}")
                return None
        except requests.exceptions.HTTPError as http_err:
            print(f"HTTP error with API key {self.api_key1[:8]}...: {http_err}")
        except requests.exceptions.RequestException as req_err:
            print(f"Request error with API key {self.api_key1[:8]}...: {req_err}")
        except Exception as e:
            print(f"Unexpected error with API key {self.api_key1[:8]}...: {e}")
        return None

    def geocode_address(self, address: str, api_key1: str = None, api_key2: str = None) -> Optional[List[float]]:
        if api_key1:
            self.api_key1 = api_key1
        if api_key2:
            self.api_key2 = api_key2
        
        coords = self.try_geocode_address(address, self.api_key1)
        if coords:
            return coords

        if self.api_key2:
            print("Retrying with secondary API key...")
            coords = self.try_geocode_address(address, self.api_key2)

        return coords

    def get_distance_by_road(self, origin_coords: List[float], destination_coords: List[float]) -> Optional[Tuple[float, float]]:
        url = "https://api.openrouteservice.org/v2/matrix/driving-car"
        headers = {
            "Authorization": self.api_key1,
            "Content-Type": "application/json"
        }
        body = {
            "locations": [origin_coords, destination_coords],
            "metrics": ["distance", "duration"]
        }

        try:
            response = requests.post(url, json=body, headers=headers)
            response.raise_for_status()
            data = response.json()

            distance_km = data["distances"][0][1] / 1000  # meters to kilometers
            duration_min = data["durations"][0][1] / 60   # seconds to minutes
            return distance_km, duration_min
        except Exception as e:
            print(f"Distance calculation error: {e}")
            return None

    def robust_geocode(self, 
                       country: str = "USA", 
                       state: Optional[str] = None, 
                       city: Optional[str] = None, 
                       street: Optional[str] = None, 
                       adress: Optional[str] = None, 
                       api_key1: str = None, 
                       api_key2: str = None ) -> Optional[Tuple[float, float]]:
        if api_key1:
            self.api_key1 = api_key1
        if api_key2:
            self.api_key2 = api_key2
        
        if adress:
            result = self.geocode_address(f"{adress}")
            if result:
                return result

        if street and city and state:
            full_address = f"{street}, {city}, {state}, {country}"
            result = self.geocode_address(full_address)
            if result:
                return result

        if city and state:
            result = self.geocode_address(f"{city}, {state}, {country}")
            if result:
                return result

        if city:
            result = self.geocode_address(f"{city}, {country}")
            if result:
                return result

        if adress and city:
            result = self.geocode_address(f"{adress}, {city}")
            if result:
                return result

        return None

    def linear_distance(self, coord1: Tuple[float, float], coord2: Tuple[float, float]) -> float:
        return geodesic(coord1, coord2).miles

    def find_nearest_center_by_linear_distance(self, origin: Tuple[float, float]) -> Tuple[str, float, Tuple[float, float]]:
        min_distance = float("inf")
        nearest_name = ""
        nearest_coords = ()

        with self.conn.cursor() as cur:
            cur.execute("SELECT name, latitude, longitude FROM hope_center")
            for name, lat, lon in cur.fetchall():
                center_coords = (lat, lon)
                dist = self.linear_distance(origin, center_coords)
                if dist < min_distance:
                    min_distance = dist
                    nearest_name = name
                    nearest_coords = center_coords

        return nearest_name, min_distance, nearest_coords

    def find_nearest_center(
                            self,
                            country: str = "USA",
                            state: Optional[str] = None,
                            city: Optional[str] = None,
                            street: Optional[str] = None,
                            adress: Optional[str] = None,
                            api_key1: str = None,
                            api_key2: str = None
                        ) -> Optional[Tuple[str, float]]:
        
        if api_key1:
            self.api_key1 = api_key1
        if api_key2:
            self.api_key2 = api_key2

        # Geocode the address
        coords = self.robust_geocode(
            country=country,
            state=state,
            city=city,
            street=street,
            adress=adress
        )

        if not coords:
            return None

        center_name, distance, _ = self.find_nearest_center_by_linear_distance(coords)

        return center_name, distance


## Test basic
# api_distance = HopeCenterDistancer()
# a = api_distance.find_nearest_center(country="USA", state="Ohio", city="Dayton", street="575 Andrea Ct")
# print(a)
## >> Fish Test