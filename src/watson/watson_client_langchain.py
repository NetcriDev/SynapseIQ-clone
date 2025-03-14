from langchain_ibm import WatsonxLLM

import os

watsonx_api_key = os.getenv("WATSON_API_KEY")

parameters = {
    "decoding_method": "sample",
    "max_new_tokens": 100,
    "min_new_tokens": 1,
    "temperature": 0.5,
    "top_k": 50,
    "top_p": 1,
}

watsonx_llm = WatsonxLLM(
    model_id="ibm/granite-13b-instruct-v2",
    url="https://us-south.ml.cloud.ibm.com",
    project_id="2696de87-406d-40ce-8fcc-07693ac2740b",
    params=parameters,
)

from langchain_core.prompts import PromptTemplate

prompt_1 = PromptTemplate(
    input_variables=["topic"],
    template="Generate a random question about {topic}: Question: "
)
prompt_2 = PromptTemplate(
    input_variables=["question"],
    template="Answer the following question: {question}",
)

from langchain.chains import LLMChain

prompt_to_flan_ul2 = LLMChain(llm=flan_ul2_llm, prompt=prompt_1, output_key='question')


flan_to_t5 = LLMChain(llm=flan_t5_llm, prompt=prompt_2, output_key='answer')

from langchain.chains import SequentialChain

qa = SequentialChain(chains=[prompt_to_flan_ul2, flan_to_t5], input_variables=["topic"], output_variables=['question', 'answer'], verbose=True)
