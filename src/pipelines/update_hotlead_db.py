import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))  # Ajusta según nivel
os.chdir(PROJECT_ROOT)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pandas as pd
from src.utils.logger_config import setup_logger
from src.database.kansas_into_db import insert_full_crash_data
from src.utils.hotlead import update_hotlead_flags


#outputdata_dir = "/Users/cristianb/Documents/Python/rel8ed/Data"
#home_dir = "/Users/cristianb/Documents/Python/rel8ed/SynapseIQ_staging"
outputdata_dir = "/home/data"
home_dir="home/SynapseIQ"

logger= setup_logger("Scheduled_execution", outputdata_dir)
# now

update_hotlead_flags()