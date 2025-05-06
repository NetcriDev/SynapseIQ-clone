from io import BytesIO
from src.services.ibm_cos import IBMCOSManager
from config.config_ibm import COS_API_KEY_ID, COS_INSTANCE_CRN, COS_ENDPOINT, bucket


cos = IBMCOSManager(
    api_key=COS_API_KEY_ID, 
    service_crn=COS_INSTANCE_CRN,
    endpoint=COS_ENDPOINT
)

print(cos.list_objects(bucket,"temp"))

# Subida desde disco
file_path_data = "/Users/cristianb/Documents/Python/rel8ed/SynapseIQ_staging/storage/kansas/004321.pdf"
cos.upload_file(
    file_path=file_path_data,
    bucket=bucket,
    filename="004321.pdf",
    year="2025",
    folder="kansas",
    overwrite=True
)

# O, alternativa: Subida desde memoria
with open("/Users/cristianb/Documents/Python/rel8ed/SynapseIQ_staging/storage/kansas/004370.pdf", "rb") as f:
    stream = BytesIO(f.read())

cos.upload_file_stream(
    stream=stream,
    bucket=bucket,
    filename="prueba005.pdf",
    year="2025",
    folder="temp",
    overwrite=True
)
#print(cos.list_objects(bucket,"kansas/2025"))
print(cos.list_objects(bucket,"winstonsalem"))