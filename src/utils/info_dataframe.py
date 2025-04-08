import pandas as pd
import sys
from src.utils.logger_config import setup_logger

main_script_path = sys.path[0]
logger = setup_logger("Kansas_execution", main_script_path)

def print_dataframe_info(df: pd.DataFrame):
    """
    Safely prints general information about a DataFrame, 
    including shape, number of records, number of columns, and column names.
    Handles empty DataFrames gracefully.
    """
    logger.info("=== DataFrame General Info ===")

    if df is None:
        logger.warning("The DataFrame is None.")
        return

    if df.empty:
        logger.warning("The DataFrame is empty (no records).")
    else:
        logger.info(f"Shape (rows, columns): {df.shape}")
        logger.info(f"Number of records (rows): {df.shape[0]}")
        logger.info(f"Number of columns: {df.shape[1]}")
        logger.info("=== --- ===")

    if df.columns.size == 0:
        logger.info("The DataFrame has no columns.")
    else:
        logger.info(f"Column names: {list(df.columns)}")
