from services.json_accident_report_validator import CrashReportValidator
import logging
import json
# Ejemplo de uso: def create_crash_report_validator(schema_path: Optional[str] = None) -> CrashReportValidator:
def create_crash_report_validator(schema_path: Optional[str] = None) -> CrashReportValidator:
    """
    Crea un validador para informes de accidentes con el esquema integrado si no se proporciona uno.
    
    Args:
        schema_path: Ruta opcional al archivo de esquema
        
    Returns:
        CrashReportValidator: Instancia del validador configurada
    """
    if schema_path:
        return CrashReportValidator(schema_path=schema_path)
    
    # Si no se proporciona un esquema, usar el esquema integrado
    schema = {
      "$schema": "https://json-schema.org/draft/2020-12/schema",
      "title": "Crash Report",
      "description": "Schema for standardizing traffic accident reports from multiple jurisdictions",
      "type": "object",
      "properties": {
        "version": {
          "type": "string",
          "description": "Version control for schema updates",
          "example": "1.0.0"
        },
        "reportNumber": {
          "type": "string",
          "description": "Unique identifier for the crash report",
          "example": "RP2025C0000102"
        },
        "traceability": {
          "type": "object",
          "description": "Metadata about the source of the JSON data",
          "properties": {
            "sourceURL": { "type": "string", "format": "uri", "example": "https://police-reports.gov/accident-RP2025C0000102.pdf" },
            "originalFormat": { "type": "string", "example": "PDF/XML/HTML" },
            "documentHash": { "type": "string", "description": "SHA-256 hash of the original document", "example": "abc1234def5678..." },
            "responsible": { "type": "string", "description": "Person/System in charge of JSON creation", "example": "Adam Smith/IBM/CHAT API" },
            "generationDate": {
              "type": "string",
              "format": "date-time",
              "description": "Timestamp of JSON file generation in UTC",
              "example": "2025-01-26T14:45:00Z"
            },
            "originalDocumentLocation": { "type": "string", "description": "File storage location", "example": "/reports/2025C0000102.pdf" }
          },
          "required": ["sourceURL", "originalFormat", "generationDate"]
        },
        "accidentDetails": {
          "type": "object",
          "properties": {
            "datetime": {
              "type": "string",
              "format": "date-time",
              "description": "Timestamp of the accident occurrence in UTC",
              "example": "2025-01-26T15:12:00Z"},
            "location": {
              "type": "object",
              "properties": {
                "city": { "type": "string", "example": "Blue Ash" },
                "street": { "type": "string", "example": "Kenwood Rd" },
                "state": { "type": "string", "example": "OH" },
                "zip": { "type": "string", "example": "45238" },
                "latitude": { "type": "number", "example": 39.250039 },
                "longitude": { "type": "number", "example": -84.375575 }
              },
              "required": ["city", "street", "state","zip"]
            },
            "weatherCondition": { "type": "string", "example": "Cloudy" },
            "roadCondition": { "type": "string", "example": "Wet" },
            "crashSeverity": {
              "type": "string",
              "enum": ["Fatal", "Serious Injury", "Minor Injury", "Property Damage Only"],
              "example": "Minor Injury"
            },
            "numberOfUnits": { "type": "integer", "example": 2 },
            "narrative": {
              "type": "string",
              "example": "Unit 1 struck Unit 2 while making a left turn."
            }
          },
          "required": ["datetime", "location", "crashSeverity","narrative"]
        },
        "vehicles": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "unitNumber": { "type": "integer", "example": 1 },
              "make": { "type": "string", "example": "KIA" },
              "model": { "type": "string", "example": "Optima/Rio" },
              "year": { "type": "integer", "example": 2013 },
              "color": { "type": "string", "example": "Black" },
              "licensePlate": {
                "type": "object",
                "properties": {
                  "number": { "type": "string", "example": "KXX63XX" },
                  "state": { "type": "string", "example": "OH" },
                  "year": { "type": "integer", "example": 2025 }
                },
                "required": ["number", "state","year"]
              },
              "VIN": { "type": "string", "example": "4300GR4XXXXXXXX970" },
              "damage": {
                "type": "object",
                "properties": {
                  "severity": { "type": "string", "example": "Minor Damage" },
                  "estimatedCost": { "type": "number", "example": 1500.00 }
                }
              },
              "insurance": {
                "type": "object",
                "properties": {
                  "company": { "type": "string", "example": "NORTH Insurance CO" },
                  "policyNumber": { "type": "string", "example": "10-002-0945345" }
                },
                "required": ["company", "policyNumber"]
              },
              "driver": {
                "type": "object",
                "properties": {
                  "name": { "type": "string", "example": "ELTON JAMES" },
                  "license": { "type": "string", "example": "XXXXXXX" },
                  "state": { "type": "string", "example": "OH" }
                },
                "required": ["name", "license", "state"]
              },
              "owner": {
                "type": "object",
                "properties": {
                  "name": { "type": "string", "example": "Adam Smith" },
                  "address": { "type": "string", "example": "123456 XYZ St, Cincinnati, OH, 45202" },
                  "phone": { "type": "string", "example": "XXX-XXX-XXXX" }
                },
                "required": ["name", "address"]
              }
            },
            "required": ["unitNumber", "make", "model", "year", "insurance", "driver", "owner"]
          }
        }
      },
      "required": ["version", "reportNumber", "traceability", "accidentDetails", "vehicles"]
    }
    
    return CrashReportValidator(schema_dict=schema)

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
# Crear validador con esquema incorporado
validator = create_crash_report_validator()

import json
import os

# Path file
#ruta_archivo = r"C:\Users\TuUsuario\Documents\datos.json"  # Windows
ruta_archivo = "/Users/cristianb/Documents/Python/SynapseIQ/Data/incident_sample.json"  # Linux

# Leer el archivo JSON y convertirlo en un diccionario
with open(ruta_archivo, "r", encoding="utf-8") as archivo:
    datos = json.load(archivo)

# Imprimir el diccionario resultante
print(datos)



# Ejemplo de datos de informe (incompleto para demostración)
sample_report = {
    "version": "1.0.0",
    "reportNumber": "RP2025C0000102",
    "traceability": {
        "sourceURL": "https://police-reports.gov/accident-RP2025C0000102.pdf",
        "originalFormat": "PDF",
        "generationDate": "2025-01-27T14:45:00Z"
    },
    "accidentDetails": {
        "datetime": "2025-01-26T15:12:00Z",
        "location": {
            "city": "Blue Ash",
            "street": "Kenwood Rd",
            "state": "OH",
            "zip": "45238",
            "latitude": 39.250039,
            "longitude": -84.375575
        },
        "crashSeverity": "Minor Injury",
        "narrative": "Unit 1 struck Unit 2 while making a left turn."
    },
    "vehicles": [
        {
            "unitNumber": 1,
            "make": "KIA",
            "model": "Optima",
            "year": 2013,
            "insurance": {
                "company": "NORTH Insurance CO",
                "policyNumber": "10-002-0945345"
            },
            "driver": {
                "name": "JamesS Bond",
                "license": "XXXXXXX",
                "state": "OH"
            },
            "owner": {
                "name": "Adam Smith",
                "address": "123456 XYZ St, Cincinnati, OH, 45202"
            }
        }
    ]
}

# Realizar validación completa
validation_result = validator.validate_crash_report_completeness(datos)
    
# Imprimir resultado
print(json.dumps(validation_result, indent=2))