# logger_config.py
import logging
import os
from datetime import datetime

def setup_logger(name: str, log_folder: str) -> logging.Logger:
    """
    Configura un logger para registrar mensajes en un archivo y en la consola.
    Args:
        name (str): Nombre del logger.
        log_folder (str): Ruta base donde se creara la carpeta 'log' y su logs: '/home/data'
    Returns:
        logging.Logger: Instancia del logger configurado.
    """
    # Crear el directorio de logs si no existe
    log_dir = os.path.join(log_folder, "logs")
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