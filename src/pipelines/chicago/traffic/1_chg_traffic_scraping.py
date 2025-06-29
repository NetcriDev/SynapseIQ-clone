# Este llama a la funcion del scraping, genera el scraping

import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))  # Ajusta según nivel
os.chdir(PROJECT_ROOT)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.connectors.chicago.chicago_scraping_traffic import pipeline_chicago_traffic
from src.utils.logger_config import setup_logger


#outputdata_dir = "/Users/cristianb/Documents/Python/rel8ed/Data"
#home_dir = "/Users/cristianb/Documents/Python/rel8ed/SynapseIQ_staging"
outputdata_dir = "/home/data/chicago/traffic"
home_dir="home/SynapseIQ"

logger= setup_logger("Scheduled_execution", home_dir)
# now

def chicago_traffic():
    logger.info(">>> Start script: chicago-traffic")
    #Reemplazar por mi scraping 
    pipeline_chicago_traffic(path=os.path.join(outputdata_dir))
    #run_msp_crash_scraper(outputdata_dir, home_path=home_dir)
    logger.info("Finish script: chicago-traffic -----|")

chicago_traffic()