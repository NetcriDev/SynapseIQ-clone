## Table of Contents

- [Introduction](#introduction)
- [Access to the virtual machine](#access-to-the-virtual-machine)
- [Api execution](#api-execution)
- [Scraping execution](#scraping-execution)
- [File-System](#file-system)
- [Branching-Strategy/Policies](#branching-strategypolicies)
  - [Main Branches](#main-branches)
  - [Branches of Work (Secondary Branches)](#branches-of-work-secondary-branches)
- [Design Pattern and File System](#design-pattern-and-file-system)
  - [Design Pattern](#design-pattern)
  - [Design Pattern: File System](#design-pattern-file-system)
- [Api Contact](#api-contact)
    - [1. Autentication](#1-autentication)
    - [2. Send Search Criteria](#2-send-search-criteria)
    - [3. Delete Search Criteria](#3-delete-search-criteria)
    - [4. Obtener Resultados de la Búsqueda](#4-obtener-resultados-de-la-búsqueda)
    - [5. Get Field Metadata](#5-get-field-metadata)
    - [6. Get Record Details](#6-get-record-details)
    - [7. Consult Available Databases](#7-consult-available-databases)
    - [API Endpoints - Use Cases](#api-endpoints---use-cases)
    - [Annexes: databaseType](#annexes-databasetype)
    - [Annexes: Search criteria in consumer](#annexes-search-criteria-in-consumer)
    - [Annexes: Field of databaseType cellphone](#annexes-field-of-databasetype-cellphone)
# Introduction
Repository layout (under construction)

# Access to the virtual machine
```
ssh -i rel8tedkey01_rsa.prv root@52.116.202.144
```

Use the following command to execute python scripts
```
pyhton3.11
```

For API keys, SSH keys, and any other general questions, please contact

```
eperler@rel8ed.to
```
# Api execution
Run the API from the directory:

```
cd /home/SynapseIQ
nohup uvicorn src.api.api_crash_report:app --reload --host 0.0.0.0 --port 8000 >> /home/SynapseIQ/logs/uvicorn.log 2>&1 &
```

# Scraping execution

```
cd /home/SynapseIQ
nohup python main.py >> /home/SynapseIQ/logs/scraping.log 2>&1 &
```
# File-System
To ensure a structured approach, the following file organization schema will be implemented. This structure separates concerns into distinct directories, making it easier to manage different components of the application. The src/ directory will contain the core application logic, including API endpoints, business logic services, JSON validation schemas, and data connectors. A dedicated ml/ folder will store machine learning models, training scripts, and inference logic. Additionally, an notebooks/ directory will be included to store notebooks for exploratory data analysis and code for proof-of-concept implementations. Deployment configurations such as Dockerfiles and CI/CD pipelines will reside in the deploy/ and ci_cd/ directories, respectively. Furthermore, logs, documentation, and test cases will be systematically organized into their respective folders, ensuring better debugging, monitoring, and maintainability.

```bash
project_root/
├── requirements.txt                    # Lists Python dependencies required for the project.
├── .github/                            # Repository workflows and CI/CD pipeline configurations.
├── src/                                # Main application directory.
│   ├── api/                            # API-related modules.
│   │   ├── example_chatbot.py          # Endpoints for chatbot interactions.
│   │   ├── example_documents.py        # Endpoints for receiving and validating JSON documents.
│   ├── services/                       # Business logic layer that handles core functionalities.
│   │   ├── example_document_service.py # Processes and stores JSON documents.
│   │   ├── example_ml_service.py       # Handles machine learning model integrations.
│   ├── schemas/                        # JSON schemas for request validation.
│   │   ├── example_document_schema.py  # JSON document validation schema.
│   │   ├── example_chatbot_schema.py   # Request/response schema for chatbot.
│   ├── utils/                          # Utility functions for various tasks.
│   ├── connectors/                     # Data ingestion modules for various file formats.
│   │   ├── example_pdf_connector.py    # Processes and extracts data from PDFs.
│   │   ├── example_csv_connector.py    # Parses and processes CSV files.
│   │   ├── example_xml_connector.py    # Parses and processes XML files.
│   │   ├── example_email_connector.py  # Handles email data ingestion.
│   ├── tests/                          # Unit and integration tests for the application.
│       ├── example_test_api.py         # Tests FastAPI endpoints and responses.
│       ├── example_test_services.py    # Tests business logic and services.
│       ├── example_test_ml.py          # Tests ML model accuracy and inference.
├── ml/                                 # Machine Learning models, training, and inference scripts.
│   ├── training/                       # Scripts for training AI models.
│   │   ├── example_train_model.py      # Trains ML models.
│   │   ├── example_preprocess_data.py  # Preprocesses training datasets.
│   ├── inference/                      # Scripts for making predictions with trained models.
│   │   ├── example_predict.py          # Runs AI model predictions.
│   ├── models/                         # Storage for trained AI models.
│       ├── example_chatbot_model.pkl           # Trained chatbot AI model.
│       ├── example_lead_qualification.pkl      # AI model for lead qualification.
├── deploy/                                     # Deployment (Docker) configuration and scripts.
│   ├── example_Dockerfile              # Defines the Docker container setup.
│   ├── example_docker-compose.yml      # Docker Compose service configurations.
├── logs/                               # Application logs for debugging and monitoring.
│   ├── example_api_logs.txt            # Logs API request and response details.
│   ├── example_chatbot_logs.txt        # Logs chatbot interactions.
│   ├── example_ml_logs.txt             # Logs ML performance and inference outputs.
├── docs/                               # Project documentation files.
│   ├── example_architecture.md         # Describes system architecture and design.
│   ├── example_api_documentation.md    # API documentation and usage details.
├── storage/                            # Temporary files, processed data (not part of source code).
├── notebooks/                          # Jupyter notebooks for exploratory analysis.
│   ├── example_scraping.ipynb          # Scraping.
│   ├── example_EDA.ipynb               # Exploratory Data Analysis (EDA).
├── config/                             # Application settings (variables, environments).
│   ├── example_settings.py             # General application settings.
│   ├── example_env.py                  # Loads variables from .env.

```

# Branching-Strategy/Policies 
For the "SympnapseIQ" project, a Branching Strategy based on “Traditional Git Flow”  will be used, which defines five main branches:

* `main`: Contains the production version.
* `release/*`:  For preparing versions before merging them into main.
* `dev`: Used for development and preparing new versions.
* `feature/*`: For developing new features.
* `hotfix/*`: For fixing production issues.
 

Traditional Git Flow is based on two permanent branches: `main` (which contains the production code) and `develop` (the main development branch). From develop, `feature/*` branches are created for new functionalities, which, once completed and reviewed via Pull Requests, are merged back into develop. When the code in develop is ready for release, a `release/*` branch is created for final testing and minor adjustments before being merged into `main`, generating a tag (v X.Y.Z) for versioning. Afterward, `release/*` is merged back into develop to keep everything in sync. For critical production issues, `hotfix/*` branches are created from main. Once the fix is implemented, they are merged into both main and develop.

## Main Branches

The following branches exist permanently in the repository and follow the following policies:
1. `main` (Production)
   - Contains the most stable version of the code and is used for production deployments.
   - Merges are only made from `release/*` or `hotfix/*` (never directly from development).
   - **Protected**: No one can push directly to this branch.

2. `dev` (Development)
   - This is the branch where new features are integrated before being released.
   - It is updated with changes from `feature/*` through reviewed Pull Requests (PRs).
   - It may be in an unstable state, but should compile correctly and pass basic tests.


## Branches of Work (Secondary Branches)

3. `feature/*` – New Features
Used for developing new features.

   - Created from `dev` and merged back into `dev` when ready.
   - Naming convention: `feature/functionality_name`

```bash
git checkout -b feature/functionality_name dev
# When the functionality is ready:
git add .
git commit -m "Implemented JSON structure validation"
# Upload the branch to the remote repository
git push origin feature/functionality_name
# <!> Then generate a Pull Request to dev and wait for the team's review.
```
4.	`hotfix/*`  (Production fixes): 
    - Created from “main” to fix urgent bugs.
    - Merged into both main and dev after fix.
    - The nomenclature follows: hotfix/hotfix_name

```bash
# The new branch will be created from the main branch
git checkout -b hotfix/bug-correction-validation main
# The error is corrected, committed and uploaded
git commit -m "Fixes duplicate JSON validation bug"
git push origin hotfix/bug-correction-validation
# <!> A pull request is created for main.
# <!> Once approved, it's merged and also merged into dev to keep both up to date.

```
5.	`release/*`  (Release preparation): Used before releasing major versions.
    - They are used to prepare versions before deployment.
    - They are created from dev and allow for: Final adjustments. Minor bug fixes. Documentation.
    - The nomenclature follows: release/vX.Y.Z
```bash
git checkout -b release/v1.0.0 dev
# <!> Testing, final adjustments are performed, and when it's ready,
# it's merged into main (deployed to production).
#It's merged into dev to keep everything synchronized.

```

# Design Pattern and File System
## Design Pattern
The following design patterns are used to organize the workflow:

`Strategy`: Helps us handle different ways of connecting to file sources (such as FTP, email, API, websites, etc.). Each connector follows the same structure, so we can switch the source without changing all the code.

```python
from abc import ABC, abstractmethod
class BaseConnector(ABC):
    @abstractmethod
    def fetch_files(self) -> list[tuple[bytes, str]]:
        "Must return a list of tuples (file_content, file_name)"
        pass
```
```python
from .base import BaseConnector

class AzureConnector(BaseConnector):
    def fetch_files(self):
        # logic for connecting and downloading from Azure Storage Blob
        return [(b"<binary>", "report.pdf")] # Example of return, Must return a list of tuples (file_content, file_name)

```

`Factory`: Allows us to decide, based on the file type (PDF, Excel, XML, image…), which class should process it. Instead of writing many “if” statements in the code, we use a factory that automatically returns the correct processor.

```python
# file: base.py
from abc import ABC, abstractmethod
from typing import Any

class BaseParser(ABC):
    @abstractmethod
    def parser(self, file_bytes: bytes, filename: str) -> dict[str, Any]:
        """Processes the file and returns a structured JSON."""
        pass
```

```python
# file: pdf_parser.py
from .base import BaseParser

class PdfParser(BaseParser):
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

```

```python
# file: factory.py
from .pdf_processor import PDFProcessor
from .excel_processor import ExcelProcessor
from .base import BaseProcessor

def get_processor(file_extension: str) -> BaseProcessor:
    match file_extension.lower():
        case ".pdf":
            return PDFProcessor()
        case ".xls" | ".xlsx":
            return ExcelProcessor()
        case _:
            raise ValueError(f"No processor found for: {file_extension}")

```

`Repository`: Takes care of saving and retrieving data (metadata, processed files, JSON results, etc.) without the rest of the system needing to worry about where or how it’s stored. It allows us to store and query data without knowing whether it goes to a database, the cloud, or a local file.

```python
from abc import ABC, abstractmethod
from typing import Any, Optional

class BaseRepository(ABC):
    @abstractmethod
    def create(self, data: dict[str, Any]) -> None:
        """Creates a new record in the database."""
        pass

    @abstractmethod
    def read(self, identifier: str) -> Optional[dict[str, Any]]:
        """Reads and returns a record given its unique identifier."""
        pass

    @abstractmethod
    def update(self, identifier: str, updates: dict[str, Any]) -> None:
        """Updates an existing record."""
        pass

    @abstractmethod
    def delete(self, identifier: str) -> None:
        """Deletes a record given its identifier."""
        pass

    @abstractmethod
    def exists(self, file_hash: str) -> bool:
        """Returns True if the file has already been hashed."""
        pass

    @abstractmethod
    def save_metadata(self, metadata: dict[str, Any]) -> None:
        """Stores metadata associated with a file."""
        pass

    @abstractmethod
    def save_json(self, structured_json: dict[str, Any]) -> None:
        """Saves the processed structured JSON from the file."""
        pass

```


## Design Pattern: File System

```
src/
│
├── connectors/                  # Strategy: for each data source (Email, FTP, API, etc.)
│   ├── base.py
│   ├── ftp_connector.py
│   ├── email_connector.py
│   ├── sharepoint_connector.py
│   └── ...
│
├── parsers/                  # Factory: for processing by file type
│   ├── base.py
│   ├── pdf_parser.py
│   ├── excel_parser.py
│   ├── xml_parser.py
│   └── factory.py
│
├── repository/                  # Repository: storage, verification, retrieval
│   ├── base.py
│   ├── cloudant_repository.py
│   ├── milvus_repository.py
│   └── athena_repository.py
│
├── metadata/                    # Extracting metadata from files such as file type, size, hash, ...
│   ├── extractor.py             # ... and file renaming strategy to create file IDs
│   ├── renamer.py
│   └── hashing.py
│
├── services/                    # Orchestration of the entire flow
│   └── ingestion_pipeline.py
│
├── models/                      # Data models
│   └── metadata_model.py
│
├── utils/                       # General utilitarian functions
│   └── logger.py
│
└── main.py                      # Entry point

```
# Api Contact
### 1. Autentication
Obtain a valid TokenID to authorize the following requests.
URL:
```
GET https://www.datairis.co/V1/auth/subscriber/?AccessToken=TU_TOKEN
```
Required headers:

* SubscriberID \
* subscriberUsername \
* SubscriberPassword \
* (optional) AccountUsername, AccountPassword (for “Application” type users)

expected response:
```
{
  "Response": {
    "responseDetails": {
      "TokenID": "a1b2cx123xyz...", 
      ...
    },
    "responseCode": "200",
    "responseMessage": "Success"
  }
}

```
**Token lifespan: 8 to 10 hours. After that, it must be regenerated.**

### 2. Send Search Criteria  
a) Add a single criterion
```
PUT /V1/criteria/search/add/{databaseType}/{criteriaName}/{criteriaValue}
```
Example:
```
PUT /V1/criteria/search/add/consumer/Physical_Zip/61834
```
b) Add multiple criteria
```
PUT /V1/criteria/search/addall/{databaseType}
```
Body JSON::
```
{
  "Physical_Zip": "61834",
  "First_Name": "Adman",
  "Last_Name": "Smith"
}
```
**Required header: TokenID**

### 3. Delete Search Criteria 
a) Delete a single criterion
```
DELETE /V1/criteria/search/delete/{databaseType}/{criteriaName}
```
b) Delete all criteria (reset search)
```
DELETE /V1/criteria/search/deleteall/{databaseType}
```
This is important because the search criteria are cumulative. If they are not deleted, any new search will include the conditions from previous ones. Therefore, using deleteall to reset the criteria between searches helps ensure accurate and isolated results.

### 4. Obtener Resultados de la Búsqueda
a) Count result
```
GET /V1/search/count/{databaseType}
```
Required header: TokenID

b) get result
```
GET /V1/search/{databaseType}?Start=1&End=10
```
Pagination: use the `Start` and `End` parameters to navigate through the results.
Response Structure:
```
{
  "Response": {
    "responseDetails": {
      "SearchResult": {
        "searchResultRecord": [
          {
            "resultFields": [
              {"fieldID": "First_Name", "fieldValue": "Adams"},
              {"fieldID": "Last_Name", "fieldValue": "Smith"},
              ...
            ]
          }
        ]
      }
    }
  }
}
```

### 5. Get Field Metadata
```
GET /V1/search/metadata/{databaseType}

```
Response:
* List of available fields (`fieldID`)
* Whether it is searchable (isSearchable)
* Whether it is visible in the output (isVisible)
* Supported operators
* Special formats (if applicable)

### 6. Get Record Details
```
GET /V1/search/recordDetail/{databaseType}/{fieldName}/{fieldValue}
```
Example:
```
GET /V1/search/recordDetail/consumer/Id/11132543091991
```
Returns: the full details of the record based on its ID.

### 7. Consult Available Databases
```
GET /V1/search/mapped/database
```
Returns: List of bases like "consumer", "business", "cellphone".

### API Endpoints - Use Cases

| Use Case           | Endpoint                                                                 | Method  | Description                                                                                       |
|--------------------|--------------------------------------------------------------------------|---------|---------------------------------------------------------------------------------------------------|
| Authentication     | `/auth/subscriber/?AccessToken={token}`                                 | GET     | Authenticates the subscriber and returns a TokenID for use in subsequent calls                   |
| Search Criteria     | `/criteria/search/add/{databaseType}/{criteriaName}/{criteriaValue}`   | PUT     | Adds a single search criterion                                                                    |
| Search Criteria     | `/criteria/search/addall/{databaseType}`                               | PUT     | Adds multiple search criteria in a single JSON payload                                            |
| Search Criteria     | `/criteria/search/deleteall/{databaseType}`                            | DELETE  | Deletes all current criteria for the specified databaseType (reset)                              |
| Search Criteria     | `/criteria/search/getall/{databaseType}`                               | GET     | Retrieves all active search criteria for the session                                              |
| Search & Data       | `/search/count/{databaseType}`                                         | GET     | Returns the number of current search matches                                                      |
| Search & Data       | `/search/{databaseType}?Start=X&End=Y`                                 | GET     | Returns paginated search results                                                                  |
| Search & Data       | `/search/recordDetail/{databaseType}/{RecordId}`                       | GET     | Returns all details of an individual record                                                       |
| Metadata            | `/search/metadata/{databaseType}`                                     | GET     | Returns the available fields for search and output                                                |
| Metadata            | `/lookup/metadata/{databaseType}?Search={field}&Start=X&End=Y&ApplyKeyword=false` | GET     | Returns decoded values for encoded fields                                                         |
| Reports             | `/reports/{ReportType}/{AccountID}/{StartDate}/{EndDate}`              | GET     | Returns reports by date, month, week, database, etc. Types: ByDay, ByMonth, etc.                 |
| Session             | `/session/getAllKeys`                                                  | GET     | Returns all session key names                                                                     |
| Session             | `/session/get/{SessionKeyName}`                                        | GET     | Returns the value of a specific session key                                                       |
| Session             | `/session/getAll`                                                      | GET     | Returns all session values                                                                        |
| Session             | `/session/delete/{SessionKeyName}`                                     | DELETE  | Deletes a specific session key                                                                    |
| Session             | `/session/deleteAll`                                                   | DELETE  | Deletes all session keys                                                                          |
| Personalization     | `/personalization/availablelayouts`                                    | GET     | Returns available layouts for the subscriber                                                      |
| Personalization     | `/personalization/theme`                                               | GET     | Returns CSS theme details configured for the user                                                 |



### Annexes: databaseType
Available Databases (`databaseType`)

| `databaseType` | Description                                                                 |
|----------------|-----------------------------------------------------------------------------|
| `consumer`     | Database of individuals (demographic data, address, credit capacity, etc.) |
| `business`     | Database of businesses (name, activity, revenue, etc.)                      |
| `cellphone`    | Mobile records database (numbers and associated data)                       |
| `newbusiness`  | Database of newly created or recently established businesses                |

These databases define the context for the following operations:

* searches (/search/...)
* criteria submission (/criteria/search/...)
* metadata (/search/metadata/...)
* record details (/search/recordDetail/...)

Each *databaseType* has a specific set of valid fields and criteria, which can be queried with:
```
GET /V1/search/metadata/{databaseType}
```

### Annexes: Search criteria in consumer
Representative list of search criteria supported by the DataIRIS API for the *consumer* database, according to the official API documentation:
Searchable Fields (`fieldID`)

| `fieldID`                                | Description                                |
|------------------------------------------|--------------------------------------------|
| `First_Name`                             | First name                                 |
| `Last_Name`                              | Last name                                  |
| `Physical_Address`                       | Physical address                           |
| `Physical_City`                          | City                                       |
| `Physical_Zip`                           | ZIP code                                   |
| `Physical_State`                         | State                                      |
| `Email`                                  | Email address                              |
| `Phone`                                  | Landline phone                             |
| `CellPhone`                              | Mobile phone                               |
| `Ind_Age`                                | Individual age                             |
| `Ind_Gender_Code`                        | Gender (e.g., M / F)                       |
| `Home_Market_Value`                      | Estimated home value                       |
| `Credit_Capacity_Code`                   | Credit capacity code                       |
| `Credit_Capacity_Description`            | Credit capacity description                |
| `Income_Estimated_Household_Ranges`      | Estimated household income range           |
| `Length_Of_Residence_Code`               | Length of residence                        |
| `Home_Dwelling_Type_Code`                | Type of dwelling                           |
| `Home_Owner_Renter_Code`                 | Owner or renter                            |
| `NetWorth_Code`                          | Net worth code                             |
| `Marital_Status_Code`                    | Marital status                             |
| `Household_Id`                           | Household ID                               |
| `Vendor_State_County`                    | Associated county                          |
| `Id`                                     | Unique record ID                           |
| `CBSA_Code`                              | Metropolitan area code                     |
| `Tally_Physical_State`                   | Tallied state                              |
| `Tally_Physical_Zip`                     | Tallied ZIP                                |
| `Tally_County_Code`                      | Tallied county code                        |

### Annexes: Field of databaseType cellphone
Possible Fields

| Field             | Description                                             |
|-------------------|---------------------------------------------------------|
| `CellPhone`       | Mobile phone number                                     |
| `First_Name`      | First name of the holder                                |
| `Last_Name`       | Last name of the holder                                 |
| `Physical_Address`| Associated physical address                             |
| `Physical_Zip`    | ZIP code linked to the number                           |
| `Phone_Carrier`   | Phone service provider                                  |
| `State / City`    | Geographic location                                     |
| `Ind_Age`, `Gender` | Demographic characteristics (if applicable)          |

