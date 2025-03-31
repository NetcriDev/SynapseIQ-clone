
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

# Pydantic models
class Passenger(BaseModel):
    id: int
    vehicle_id: int
    role: Optional[str]
    name: Optional[str]
    age: Optional[int]
    gender: Optional[str]
    license_number: Optional[str]
    injury_severity: Optional[str]
    phone1: Optional[str]
    phone2: Optional[str]
    notes: Optional[str]

class PassengerUpdatePhones(BaseModel):
    phone1: Optional[str]
    phone2: Optional[str]

class Vehicle(BaseModel):
    id: int
    incident_report_id: int
    unit_number: Optional[int]
    make: Optional[str]
    model: Optional[str]
    year: Optional[int]
    color: Optional[str]
    license_plate_number: Optional[str]
    license_plate_state: Optional[str]
    license_plate_year: Optional[int]
    vin: Optional[str]
    damage_severity: Optional[str]
    estimated_cost: Optional[float]
    insurance_company: Optional[str]
    policy_number: Optional[str]
    driver_name: Optional[str]
    driver_license: Optional[str]
    driver_state: Optional[str]
    owner_name: Optional[str]
    owner_address: Optional[str]
    owner_phone: Optional[str]
    notes: Optional[str]
    passengers: Optional[List[Passenger]] = []
    incident: Optional[dict] = None

class IncidentReport(BaseModel):
    id: int
    report_number: str
    version_json: Optional[str]
    source_url: Optional[str]
    original_format: Optional[str]
    document_hash: Optional[str]
    responsible: Optional[str]
    generation_date: Optional[datetime]
    original_document_location: Optional[str]
    accident_datetime: Optional[datetime]
    city: Optional[str]
    street: Optional[str]
    state: Optional[str]
    zip: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    weather_condition: Optional[str]
    road_condition: Optional[str]
    crash_severity: Optional[str]
    number_of_units: Optional[int]
    narrative: Optional[str]
    notes: Optional[str]
    vehicles: Optional[List[Vehicle]] = []