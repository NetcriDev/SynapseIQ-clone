from apscheduler.schedulers.blocking import BlockingScheduler
from src.connectors.Kansas_requests import run_kansas_crash_scraper
from src.connectors.WSP_requests import run_wsp_crash_scraper
from src.connectors.MSP_requests import run_msp_crash_scraper
from src.connectors.texas_scrapper import run_scraper               #Texas
from src.parsers.texas_parser import read_and_save_recent_csv       #Texas
from src.utils.logger_config import setup_logger
from datetime import datetime, timedelta
import sys
import os


# Add src/ folder to sys.path to import scraper and parser modules
sys.path.append(os.path.dirname(__file__))

#outputdata_dir = "/Users/cristianb/Documents/Python/rel8ed/SynapseIQ_staging/storage"
#home_dir = "/Users/cristianb/Documents/Python/rel8ed/SynapseIQ_staging"
outputdata_dir = "/home/data"
home_dir="home/data/SynapseIQ"

logger= setup_logger("Scheduled_execution", home_dir)
# now
now = datetime.now()

sched = BlockingScheduler()

@sched.scheduled_job('interval', minutes=30, next_run_time=now)
def kansas():
    logger.info(">>> Start script: Kansas")
    run_kansas_crash_scraper(path_dir=outputdata_dir)
    logger.info("Finish script: kansas ---|")

@sched.scheduled_job('interval', minutes=30, next_run_time=now + timedelta(minutes=5))
def WinstonSalem():
    logger.info(">>> Start script: WinstonSalem")
    run_wsp_crash_scraper(output_dir=outputdata_dir)
    logger.info("Finish script: WinstonSalem ---|")

@sched.scheduled_job('interval', minutes=30, next_run_time=now + timedelta(minutes=10))
def Minnesota():
    logger.info(">>> Start script: Minnesota")
    run_msp_crash_scraper(outputdata_dir, home_dir)
    logger.info("Finish script: Minnesota ---|")

@sched.scheduled_job('interval', minutes=30, next_run_time=now + timedelta(minutes=15))
def Texas():
    logger.info(">>> Start script: Texas")
    try:
        print(" scraping execute...")
        df_scraped = run_scraper(os.path.join(outputdata_dir,"texas"), os.path.join(home_dir,"texas"))

        print("processed CSV ")
        df_processed = read_and_save_recent_csv(os.path.join(outputdata_dir,"texas"), 
                                                os.path.join(outputdata_dir,"texas", "processed"),
                                                margin_seconds=60)
        logger.info("Finish script: Texas ---|")
    except Exception as e:
        logger.error("Error script: Texas ---|")

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