## Table of Contents

- [Introduction](#introduction)
- [Configuration](#configuration)
- [Api execution](#api-execution)
- [File-System](#file-system)
- [Branching-Strategy/Policies](#branching-strategypolicies)
  - [Main Branches](#main-branches)
  - [Branches of Work (Secondary Branches)](#branches-of-work-secondary-branches)
- [Design Pattern and File System](#design-pattern-and-file-system)
  - [Design Pattern](#design-pattern)
  - [Design Pattern: File System](#design-pattern-file-system)

# Introduction
Repository layout (under construction)

# Configuration
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
uvicorn src.api.api_crash_report:app --reload
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
