import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))  # Ajusta según nivel
os.chdir(PROJECT_ROOT)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.connectors.kansas_w_functions import pipeline_kansas
from src.utils.logger_config import setup_logger


#outputdata_dir = "/Users/cristianb/Documents/Python/rel8ed/Data"
#home_dir = "/Users/cristianb/Documents/Python/rel8ed/SynapseIQ_staging"
outputdata_dir = "/home/data"
home_dir="home/SynapseIQ"

logger= setup_logger("Scheduled_execution", home_dir)
# now

def kansas():
    logger.info(">>> Start script: kansas")
    pipeline_kansas(outdata_folder=os.path.join(outputdata_dir, "kansas"))
    #run_msp_crash_scraper(outputdata_dir, home_path=home_dir)
    logger.info("Finish script: kansas -----|")

kansas()