from apscheduler.schedulers.blocking import BlockingScheduler
from src.connectors.Kansas_requests import run_kansas_crash_scraper
from src.connectors.WSP_requests import run_wsp_crash_scraper
from src.connectors.MSP_requests import run_msp_crash_scraper
from src.connectors.texas_scrapper import run_scraper               #Texas
from src.parsers.texas_parser import read_and_save_recent_csv       #Texas
from src.utils.logger_config import setup_logger
from datetime import datetime, timedelta
from src.utils.record_update import process_names_in_db
import sys
import os
from src.models.texas_db import create_tables_texas

# Add src/ folder to sys.path to import scraper and parser modules
base_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, base_dir)

outputdata_dir = "/Users/cristianb/Documents/Python/rel8ed/SynapseIQ_staging/storage"
home_dir = "/Users/cristianb/Documents/Python/rel8ed/SynapseIQ_staging"
#outputdata_dir = "/home/data"
#home_dir="home/data/SynapseIQ"

logger= setup_logger("Scheduled_execution", home_dir)
# now


# def kansas():
#     logger.info(">>> Start script: Kansas")
#     run_kansas_crash_scraper(path_dir=outputdata_dir)
#     logger.info("Finish script: kansas -----|")

# kansas()


# def WinstonSalem():
#     logger.info(">>> Start script: WinstonSalem")
#     run_wsp_crash_scraper(output_dir=outputdata_dir)
#     logger.info("Finish script: WinstonSalem -----|")

# WinstonSalem()


# def Minnesota():
#     logger.info(">>> Start script: Minnesota")
#     run_msp_crash_scraper(outputdata_dir)
#     logger.info("Finish script: Minnesota -----|")

# Minnesota()


# def Texas():
#     logger.info(">>> Start script: Texas")
#     try:
#         logger.info(" scraping execute...")
#         df_scraped = run_scraper(os.path.join(outputdata_dir,"texas"), os.path.join(home_dir,"texas"))

#         logger.info("processed CSV ")
#         df_processed = read_and_save_recent_csv(os.path.join(outputdata_dir,"texas"), 
#                                                 os.path.join(outputdata_dir,"texas", "processed"),
#                                                 margin_seconds=60)
#         logger.info("Finish script: Texas -----|")
#     except Exception as e:
#         logger.error("Error script: Texas -----|")
# Texas()

#process_names_in_db()
#create_tables_texas()
