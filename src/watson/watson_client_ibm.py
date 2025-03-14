from ibm_watsonx_ai import APIClient
from ibm_watsonx_ai import Credentials
from ibm_watsonx_ai.foundation_models import ModelInference
import sys, os

credentials = Credentials(
    url = "https://us-south.ml.cloud.ibm.com",
    api_key = os.getenv("WATSON_API_KEY")
)

client = APIClient(credentials)

params = {
    "time_limit": 10000,
    "max_new_token": 100
}

model_id = "meta-llama/llama-3-2-11b-vision-instruct"
project_id = "2696de87-406d-40ce-8fcc-07693ac2740b"
space_id = None # optional
verify = False

model = ModelInference(
  model_id=model_id,
  api_client=client,
  params=params,
  project_id=project_id,
  space_id=space_id,
  verify=verify,
)

messages = [
  {
    "role": "system",
    "content": "You are a helpful assistant."
  },
  {
    "role": "user",
    "content": [
      {
        "type": "text",
        "text": "How far is Paris from Bangalore?"
      }
    ]
  },
  {
    "role": "assistant",
    "content": "The distance between Paris, France, and Bangalore, India, is approximately 7,800 kilometers (4,850 miles)"
  }
]

q = " ".join(sys.argv[1:])
print(q)
data = {
    "role": "user",
    "content": [
      {
        "type": "text",
        "text": str(q)
      }
    ]
  }

messages.append(data)
print(model.chat(messages=messages))