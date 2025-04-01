from apscheduler.schedulers.blocking import BlockingScheduler
from src.connectors.Kansas_requests import run_kansas_crash_scraper
from src.connectors.WSP_requests import run_wsp_crash_scraper

#output_data = "/Users/cristianb/Documents/Python/rel8ed/SynapseIQ_staging/storage"
output_data = "/home/data"


sched = BlockingScheduler()

@sched.scheduled_job('interval', minutes=18)
def kansas():
    run_kansas_crash_scraper(path_dir=output_data)
    print("Task each 20 minutes")

@sched.scheduled_job('interval', minutes=24)
def WinstonSalem():
    run_wsp_crash_scraper(output_dir=output_data)
    print("Task each 20 minutes")

sched.start()



#from connectors.email_connector import EmailConnector
#from connectors.ftp_connector import FTPConnector
#from services.ingestion_pipeline import IngestionPipeline
#def main():
#    # Aquí podrías usar argumentos o un archivo de configuración para elegir el conector
#    connector = EmailConnector()  # cambiar por FTPConnector(), etc.
#    
#    pipeline = IngestionPipeline(connector)
#    pipeline.run()
#if __name__ == "__main__":
#    main()