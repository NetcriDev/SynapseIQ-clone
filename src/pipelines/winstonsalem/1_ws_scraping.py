import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))  # Ajusta según nivel
os.chdir(PROJECT_ROOT)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.connectors.WSP_w_functions import pipeline_winstonsalem
from src.utils.logger_config import setup_logger


#outputdata_dir = "/Users/cristianb/Documents/Python/rel8ed/Data"
#home_dir = "/Users/cristianb/Documents/Python/rel8ed/SynapseIQ_staging"
outputdata_dir = "/home/data"
home_dir="home/SynapseIQ"

logger= setup_logger("Scheduled_execution", home_dir)
# now

def winston():
    logger.info(">>> Start script: Winston Salem")
    pipeline_winstonsalem(outdata_folder=os.path.join(outputdata_dir, "winstonsalem"))
    #run_msp_crash_scraper(outputdata_dir, home_path=home_dir)
    logger.info("Finish script: Winston Salem -----|")

winston()