import asyncio
from typing import Dict
from ibm_watsonx_ai import APIClient, Credentials
from ibm_watsonx_ai.foundation_models import ModelInference


class WatsonXModelHandler:
    def __init__(self, api_key: str, 
                 project_id: str, 
                 url: str, 
                 default_model_id: str = "meta-llama/llama-3-2-11b-vision-instruct", 
                 temperature: float = 0.2):
        """
        Initializes the IBM WatsonX AI client.

        Args:
            api_key (str): IBM Cloud API Key.
            project_id (str): WatsonX project ID.
            url (str): Regional endpoint.
            default_model_id (str): Default model if not specified.
            temperature (float): Model creativity.
        """
        self.api_key = api_key
        self.project_id = project_id
        self.url = url
        self.default_model_id = default_model_id
        self.temperature = temperature

    def _build_model(self, model_id: str) -> ModelInference:
        """
        Crea una instancia aislada del modelo para cada petición.
        """
        credentials = Credentials(api_key=self.api_key, url=self.url)
        client = APIClient(credentials)
        return ModelInference(
            model_id=model_id,
            api_client=client,
            project_id=self.project_id,
            persistent_connection=False,
            params={"max_new_tokens": 1000, "temperature": self.temperature}
        )

    def _build_messages(self, question: str, text_content: str) -> list:
        """
        Create the message to send to the model.
        """
        return [
            {
                "role": "system",
                "content": "You are an expert assistant that analyzes documents and answers questions based on their content."
            },
            {
                "role": "user",
                "content": f"""
                                Given the following accident report text:

                                >>> This is the report:
                                {text_content}
                                <<<

                                Answer the following question:
                                {question}
                            """
            }
        ]

    async def query(self, question: str, text_content: str, model_id: str = None) -> Dict[str, str]:
        """
        Query the WatsonX model concurrently without blocking.

        Args:
            question (str): User question.
            text_content (str): Full text of the document.
            model_id (str): (Opcional) Model to use.

        Returns:
            Dict[str, str]: Model response.
        """
        model_id = model_id or self.default_model_id
        if not model_id:
            raise ValueError("You must specify a 'model_id' if one is not set by default.")

        messages = self._build_messages(question, text_content)
        model = self._build_model(model_id)

        # Ejecutar llamada en hilo separado para no bloquear
        response = await asyncio.to_thread(model.chat, messages=messages)
        answer = response["choices"][0]["message"]["content"]
        return {
            "model_id": model_id,
            "question": question,
            "response": answer.strip()
        }