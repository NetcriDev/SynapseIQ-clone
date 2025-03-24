from .base import BaseParser

class ImageParser(BaseParser):
    def parser(self, file_bytes: bytes, filename: str) -> dict:
        # Code that executes the parser
        return {
            "report_id": "ACC12345",
            "datetime": "2025-02-26",
            "location": {
                "street": "Lakeview Dr",
                "city": "Angeles",
                "state": "CA",
                "zip": "90001",
                "coordinates": {"latitude": 34.0522, "longitude": -118.2437}
                },
                "vehicles_involved": [
                    {"plate_number": "XYZ123", "make": "Toyota", "model": "Corolla", "year": 2018}
                    ],
                    "injuries_reported": True,
                    "injury_severity": "Major",
                    "official_documentation": {
                        "police_report_id": "PR-98765",
                        "insurance_claim_status": "Pending"
                        },
                        "officer_in_charge": {"name": "Smith Adam", "badge_number": "3435345"}
                        }