
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

# Pydantic models
class Passenger(BaseModel):
    id: int
    report_number: Optional[str]
    vehicle_id: int
    role: Optional[str]
    name: Optional[str]
    first_name: Optional[str]
    middle_name: Optional[str]
    last_name: Optional[str]
    state: Optional[str]
    city: Optional[str]
    age: Optional[int]
    gender: Optional[str]
    license_number: Optional[str]
    injury_severity: Optional[str]
    phone1: Optional[str]
    phone2: Optional[str]
    contact_resolution: Optional[str]
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
    driver_first_name: Optional[str]
    driver_middle_name: Optional[str]
    driver_last_name: Optional[str]
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
    internal_report_number: Optional[str]
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
    nearest_center_d: Optional[float]
    nearest_hope_d: Optional[float]
    name_nearest_hope: Optional[str]
    notes: Optional[str]
    technical_notes: Optional[str]
    vehicles: Optional[List[Vehicle]] = []

#texas
class PassengerReport(BaseModel):
    id: int
    crash_report_id: Optional[int]
    crash_id: Optional[str]
    report_number: Optional[str]
    amount_damage: Optional[str]
    contributing_factors: Optional[str]
    fatal_crash_flag: Optional[str]
    street_number: Optional[str]
    nearest_trauma_center: Optional[str]
    nearest_trauma_center_distance: Optional[float]
    contributing_factor_1: Optional[str]
    contributing_factor_2: Optional[str]
    contributing_factor_3: Optional[str]
    driver_zip_code: Optional[int]
    lessee_owner_zip_code: Optional[int]
    vehicle_hit_and_run_flag: Optional[str]
    vin: Optional[str]
    person_age: Optional[int]
    person_gender: Optional[str]
    person_injury_severity: Optional[str]
    person_non_suspected_serious_injury_count: Optional[int]
    person_count_number: Optional[int]
    physical_location_of_an_occupant: Optional[str]
    state: Optional[str]
    city: Optional[str]
    street: Optional[str]

#Texas
class CrashReportWithPassengers(BaseModel):
    id: int
    crash_id: str
    internal_crash_id: str
    report_number: Optional[str]
    agency: Optional[str]
    case_id: Optional[str]
    state: Optional[str]
    city: Optional[str]
    county: Optional[str]
    street_number: Optional[str]
    street: Optional[str]
    region: Optional[str]
    crash_date: Optional[datetime]
    crash_severity: Optional[str]
    passengers: List[PassengerReport] = []
