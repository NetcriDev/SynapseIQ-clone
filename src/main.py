from connectors.email_connector import EmailConnector
from connectors.ftp_connector import FTPConnector
from services.ingestion_pipeline import IngestionPipeline

def main():
    # Aquí podrías usar argumentos o un archivo de configuración para elegir el conector
    connector = EmailConnector()  # cambiar por FTPConnector(), etc.
    
    pipeline = IngestionPipeline(connector)
    pipeline.run()

if __name__ == "__main__":
    main()

