
from src.connectors.texas_scrapper import run_scraper               #Texas
from src.parsers.texas_parser import read_and_save_recent_csv       #Texas
from src.utils.logger_config import setup_logger
from datetime import datetime, timedelta
import sys
import os

# Add src/ folder to sys.path to import scraper and parser modules
sys.path.append(os.path.dirname(__file__))

outputdata_dir = "/Users/cristianb/Documents/Python/rel8ed/SynapseIQ_staging/storage"
home_dir = "/Users/cristianb/Documents/Python/rel8ed/SynapseIQ_staging"
#outputdata_dir = "/home/data"
#home_dir="home/data/SynapseIQ"

logger= setup_logger("Scheduled_execution", home_dir)
# now
now = datetime.now()

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


Texas()

