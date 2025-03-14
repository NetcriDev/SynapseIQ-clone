# See https://dataplatform.cloud.ibm.com/docs/content/wsj/analyze-data/fm-text-extraction-notebook.html?context=wx

from ibm_watsonx_ai.helpers import DataConnection, S3Location
from ibm_watsonx_ai import Credentials
from ibm_watsonx_ai.foundation_models import ModelInference
from ibm_watsonx_ai import APIClient
from ibm_watsonx_ai.foundation_models.extractions import TextExtractions
from ibm_watsonx_ai.foundation_models.extractions import TextExtractions
from ibm_watsonx_ai.metanames import TextExtractionsMetaNames
import json

local_source_file_name = "granite_code_models_paper.pdf"
source_file_name = "./files/granite_code_models_paper.pdf"
results_file_name = "./files/text_extraction_granite_code_models_paper.json"


connection_asset_id="crn:v1:bluemix:public:cloud-object-storage:global:a/a3ddc697dfc74d418f1d2974f79fe20e:21f71496-8920-408b-867e-b8f4f80a240e:bucket:ingestion-temp-bucket"
bucketname="ingestion-temp-bucket"

source_file_name="ALDI_sustainability_6.pdf"
results_file_name="output"

document_reference = DataConnection(connection_asset_id=connection_asset_id,
                                    location=S3Location(bucket=bucketname,
                                                        path=source_file_name))

results_reference = DataConnection(connection_asset_id=connection_asset_id,
                                   location=S3Location(bucket=bucketname,
                                                       path=results_file_name))

credentials = Credentials(
    url = "https://us-south.ml.cloud.ibm.com",
    #api_key = "ZGSeCv9jm4AW0jhCbIWQUl7WeBU4ZYIYL0iCwSVoDISS"
    api_key = "ySoS-QcyX7G8XZTQqVd2Bw0SRNZWCOjgo5RI8s87YTP3"
)
project_id = os.getenv("PROJECT_ID")

client = APIClient(credentials)


extraction = TextExtractions(api_client=client,
                            project_id=project_id)


steps = {TextExtractionsMetaNames.OCR: {'language_list': ['en']},
        TextExtractionsMetaNames.TABLE_PROCESSING: {'enabled': True}}


details = extraction.run_job(document_reference=document_reference,
                            results_reference=results_reference,
                            steps=steps)
extraction_job_id = extraction.get_id(extraction_details=details)

results_reference = extraction.get_results_reference(extraction_id=extraction_job_id)
filename = "text_extraction_results_granite_code_models_paper.json"
results_reference.download(filename=filename)

metadata = json.load(open(filename, 'r'))
metadata.get('all_structures').get('tokens')[:10]
