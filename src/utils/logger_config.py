# logger_config.py
import logging
import os
from datetime import datetime

def setup_logger(name: str, path_home: str):
    log_dir = os.path.join(path_home, "logs")
    os.makedirs(log_dir, exist_ok=True)

    log_filename = os.path.join(
        log_dir,
        f"{name}_{datetime.now().strftime('%Y-%m-%d')}.log"
    )

    # Evita agregar múltiples handlers si ya están configurados
    if not logging.getLogger(name).handlers:
        logger = logging.getLogger(name)
        logger.setLevel(logging.INFO)

        # Archivo
        file_handler = logging.FileHandler(log_filename)
        file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        logger.addHandler(file_handler)

        # Consola
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        logger.addHandler(console_handler)

    return logging.getLogger(name)


#from logger_config import setup_logger

#path_home = "/Users/cristianb/Documents/Python/rel8ed/SynapseIQ_staging"
#logger = setup_logger("MSP_execution", path_home)

#logger.info("start script")
#logger.warning("this is a warning")
#logger.error("Something went wrong")