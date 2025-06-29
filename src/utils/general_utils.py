
import os
import pandas as pd


# Función que convierte el DataFrame a CSV
def convert_df_to_csv(df: pd.DataFrame, download_folder: str, csv_name: str):
    csv_path = os.path.join(download_folder, f"{csv_name}.csv")
    df.to_csv(csv_path, index=False)
    print(f"Archivo CSV guardado en: {csv_path}")
    return csv_path
