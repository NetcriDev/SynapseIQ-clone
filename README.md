# SynapseIQ

Repository layout (under construction)

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

You can connect to the current VM instance with the following command;
```
ssh -i rel8tedkey01_rsa.prv" root@52.116.202.144
```

Use the following command to execute python scripts
```
pyhton3.11
```

For API keys, SSH keys, and any other general questions, please contact

```
eperler@rel8ed.to
```