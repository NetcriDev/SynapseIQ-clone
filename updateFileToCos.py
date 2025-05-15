import os
from src.services.ibm_cos import IBMCOSManager 
from config.config_ibm import COS_API_KEY_ID, COS_INSTANCE_CRN, COS_ENDPOINT,bucket


# === Configuración general
local_folder_base = "/home/data"  # carpeta donde están los subdirectorios por estado
bucket_name = "bucket-synapse-iq"
year = "2025"

# === Lista de estados que quieres subir
states = ["ohio", "kansas", "winstonsalem", "minnesota"]  # puedes recorrer todos los subdirectorios si prefieres

# === Inicializar cliente COS
cos = IBMCOSManager(COS_API_KEY_ID, COS_INSTANCE_CRN, COS_ENDPOINT)

for state in states:
    local_dir = os.path.join(local_folder_base, state)
    remote_folder = state  # será usado como carpeta lógica en COS

    if not os.path.isdir(local_dir):
        print(f" Carpeta no encontrada: {local_dir}")
        continue

    for file_name in os.listdir(local_dir):
        if not file_name.lower().endswith(".pdf"):
            continue

        local_path = os.path.join(local_dir, file_name)

        print(f" Subiendo {local_path} -> COS: /{remote_folder}/{year}/{file_name}")
        cos.upload_file(
            file_path=local_path,
            bucket=bucket_name,
            filename=file_name,
            year=year,
            folder=remote_folder,
            overwrite=True  # cambia a False si no quieres reemplazar existentes
        )