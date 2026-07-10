# Class to return an model embeddings
import os
import sys

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from langchain_openai import OpenAIEmbeddings
from config import settings

class EmbeddingsModel(OpenAIEmbeddings):
    def __init__(self, 
                 model_name: str = settings.OPENAI_EMBEDDINGS_MODEL, 
                 openai_api_key: str = settings.OPENAI_API_KEY):
        
        super().__init__(model=model_name, openai_api_key=openai_api_key)