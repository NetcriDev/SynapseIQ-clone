#Clase CrashReportValidator
import json
import os
import jsonschema
from typing import Dict, Any, List, Optional, Tuple
from jsonschema import Draft202012Validator
import logging
from datetime import datetime, timedelta

class CrashReportValidator:
    """
    Specialized class for validating crash reports against the defined schema.
    It implements detailed validation and provides information about specific errors.
    """
    
    def __init__(self, schema_path: Optional[str] = None, schema_dict: Optional[Dict[str, Any]] = None):
        """
        Initializes the validator with a JSON schema, either from a file or directly as a dictionary.
        
        Args:
            schema_path: Path to the JSON schema file (optional)
            schema_dict: Dictionary containing the JSON schema (optional)
        
        Raises:
            ValueError: If no schema source is provided or if there is an error in the schema.
        """
        self.logger = logging.getLogger(__name__)
        
        if schema_path and os.path.exists(schema_path):
            try:
                with open(schema_path, 'r') as schema_file:
                    self.schema = json.load(schema_file)
                self.logger.info(f"Scheme loaded from file: {schema_path}")
            except json.JSONDecodeError as e:
                self.logger.error(f"Error decoding schema file: {e}")
                raise ValueError(f"Error decoding schema file: {e}")
        elif schema_dict:
            self.schema = schema_dict
            self.logger.info("Schema loaded from dictionary")
        else:
            self.logger.error("No valid schema was provided")
            raise ValueError("You must provide a path to a valid schema file or schema dictionary")
        
        # Validar que el esquema mismo sea válido
        try:
            Draft202012Validator.check_schema(self.schema)
            self.validator = Draft202012Validator(self.schema)
            self.logger.info("Schema validated correctly")
        except jsonschema.exceptions.SchemaError as e:
            self.logger.error(f"The provided schema is not valid: {e}")
            raise ValueError(f"The provided schema is not valid: {e}")
    
    def validate(self, json_data: Dict[str, Any]) -> bool:
        """
        Validates the accident report against the loaded schematic.
        
        Args:
            json_data: JSON data to validate
            
        Returns:
            bool: True if the JSON is valid, False if it is not
        """
        try:
            self.validator.validate(json_data)
            self.logger.info("JSON validation successful")
            return True
        except jsonschema.exceptions.ValidationError as e:
            self.logger.warning(f"Validation error: {e}")
            return False
    
    def validate_with_details(self, json_data: Dict[str, Any]) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        Validates the crash report, in Json, and returns detailed information about the errors.
        
        Args:
            json_data: JSON data to validate
            
        Returns:
            Tuple[bool, List[Dict[str, Any]]]: (is_valid, error_list)
        """
        errors = []
        is_valid = True
        
        for error in self.validator.iter_errors(json_data):
            is_valid = False
            error_info = {
                "path": ".".join(str(p) for p in error.path) if error.path else "root_document",
                "message": error.message,
                "schema_path": ".".join(str(p) for p in error.schema_path)
            }
            errors.append(error_info)
            self.logger.warning(f"Schema violation: {error_info['path']} - {error_info['message']}")
        
        if is_valid:
            self.logger.info("Successful validation")
        else:
            self.logger.warning(f"Validation failed with {len(errors)} errors")
        
        return is_valid, errors
    
    def validate_required_fields(self, json_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Specifically check the presence of all required fields in the report.
        
        Args:
            json_data: JSON data to validate
            
        Returns:
            Tuple[bool, List[str]]: (all_fields_present, fields_missing)
        """
        missing_fields = []
        
        # Validate required fields at the root level
        for field in self.schema.get("required", []):
            if field not in json_data:
                missing_fields.append(field)
        
        # Validate required fields in traceability
        if "traceability" in json_data and isinstance(json_data["traceability"], dict):
            for field in self.schema.get("properties", {}).get("traceability", {}).get("required", []):
                if field not in json_data["traceability"]:
                    missing_fields.append(f"traceability.{field}")
        
        # Validate required fields in Accident Details
        if "accidentDetails" in json_data and isinstance(json_data["accidentDetails"], dict):
            for field in self.schema.get("properties", {}).get("accidentDetails", {}).get("required", []):
                if field not in json_data["accidentDetails"]:
                    missing_fields.append(f"accidentDetails.{field}")
            
            # Validar campos requeridos en location
            if "location" in json_data["accidentDetails"] and isinstance(json_data["accidentDetails"]["location"], dict):
                for field in self.schema.get("properties", {}).get("accidentDetails", {}).get("properties", {}).get("location", {}).get("required", []):
                    if field not in json_data["accidentDetails"]["location"]:
                        missing_fields.append(f"accidentDetails.location.{field}")
        
        # Validate vehicles
        if "vehicles" in json_data and isinstance(json_data["vehicles"], list):
            vehicle_requirements = self.schema.get("properties", {}).get("vehicles", {}).get("items", {}).get("required", [])
            license_requirements = self.schema.get("properties", {}).get("vehicles", {}).get("items", {}).get("properties", {}).get("licensePlate", {}).get("required", [])
            insurance_requirements = self.schema.get("properties", {}).get("vehicles", {}).get("items", {}).get("properties", {}).get("insurance", {}).get("required", [])
            driver_requirements = self.schema.get("properties", {}).get("vehicles", {}).get("items", {}).get("properties", {}).get("driver", {}).get("required", [])
            owner_requirements = self.schema.get("properties", {}).get("vehicles", {}).get("items", {}).get("properties", {}).get("owner", {}).get("required", [])
            
            for i, vehicle in enumerate(json_data["vehicles"]):
                for field in vehicle_requirements:
                    if field not in vehicle:
                        missing_fields.append(f"vehicles[{i}].{field}")
                
                if "licensePlate" in vehicle and isinstance(vehicle["licensePlate"], dict):
                    for field in license_requirements:
                        if field not in vehicle["licensePlate"]:
                            missing_fields.append(f"vehicles[{i}].licensePlate.{field}")
                
                if "insurance" in vehicle and isinstance(vehicle["insurance"], dict):
                    for field in insurance_requirements:
                        if field not in vehicle["insurance"]:
                            missing_fields.append(f"vehicles[{i}].insurance.{field}")
                
                if "driver" in vehicle and isinstance(vehicle["driver"], dict):
                    for field in driver_requirements:
                        if field not in vehicle["driver"]:
                            missing_fields.append(f"vehicles[{i}].driver.{field}")
                
                if "owner" in vehicle and isinstance(vehicle["owner"], dict):
                    for field in owner_requirements:
                        if field not in vehicle["owner"]:
                            missing_fields.append(f"vehicles[{i}].owner.{field}")
        
        return len(missing_fields) == 0, missing_fields
    
    def validate_crash_report_completeness(self, json_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform a comprehensive validation of the accident report and generate a quality report.   

        Args:
            json_data: JSON data to validate
            
        Returns:
            Dict[str, Any]: Detailed validation report
        """
        result = {
            "is_valid": False,
            "schema_validation": {
                "passed": False,
                "errors": []
            },
            "completeness": {
                "all_required_fields_present": False,
                "missing_fields": []
            },
            "data_quality": {
                "warnings": []
            }
        }
        
        # Schema validation
        schema_valid, errors = self.validate_with_details(json_data)
        result["schema_validation"]["passed"] = schema_valid
        result["schema_validation"]["errors"] = errors
        
        # Validation of required fields
        fields_complete, missing = self.validate_required_fields(json_data)
        result["completeness"]["all_required_fields_present"] = fields_complete
        result["completeness"]["missing_fields"] = missing
        
        # Data quality validation
        self._validate_data_quality(json_data, result["data_quality"]["warnings"])
        
        # Bottom line
        result["is_valid"] = schema_valid and fields_complete and len(result["data_quality"]["warnings"]) == 0
        
        return result
    
    def _validate_data_quality(self, json_data: Dict[str, Any], warnings: List[str]) -> None:
        """
        Verifies data quality beyond schema validation.
        
        Args:
            json_data: JSON data to validate
            warnings: List where warnings will be added
        """
        # Verify that the date of the accident is prior to the generation date
        if ("accidentDetails" in json_data and "datetime" in json_data["accidentDetails"] and
            "traceability" in json_data and "generationDate" in json_data["traceability"]):
            
            accident_date = json_data["accidentDetails"]["datetime"]
            accident_date=datetime.strptime(accident_date[:-1], "%Y-%m-%dT%H:%M:%S")
            generation_date = json_data["traceability"]["generationDate"]
            generation_date=datetime.strptime(generation_date[:-1], "%Y-%m-%dT%H:%M:%S")+timedelta(days=2)

            if accident_date > generation_date:
                warnings.append("The date of the accident is after the date the report was generated.")
        
        # Verify geographic data
        if ("accidentDetails" in json_data and "location" in json_data["accidentDetails"]):
            location = json_data["accidentDetails"]["location"]
            
            # Verify that the latitude is within the valid range
            if "latitude" in location and (location["latitude"] < -90 or location["latitude"] > 90):
                warnings.append(f"Latitude out of valid range: {location['latitude']}")
            
            # Verify that the length is in the valid range
            if "longitude" in location and (location["longitude"] < -180 or location["longitude"] > 180):
                warnings.append(f"Length out of valid range: {location['longitude']}")
        
        # Check vehicle year
        if "vehicles" in json_data and isinstance(json_data["vehicles"], list):
            current_year = 2025+1  # TODO: retrieve the system date and time
            
            for i, vehicle in enumerate(json_data["vehicles"]):
                if "year" in vehicle and isinstance(vehicle["year"], int):
                    if vehicle["year"] < 1920 or vehicle["year"] > current_year:
                        warnings.append(f"Año del vehículo {i+1} ({vehicle['year']}) fuera de rango razonable")
