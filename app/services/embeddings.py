"""Embeddings model wrapper — Layer 1 helper.

Provides a module-level singleton of OpenAIEmbeddings with settings
from the central config.  Both services and agents import from here
to keep embeddings configuration in one place.
"""

from langchain_openai import OpenAIEmbeddings
from app.config import settings


class EmbeddingsModel(OpenAIEmbeddings):
    """OpenAI embeddings preconfigured with SmartBnB settings."""

    def __init__(
        self,
        model_name: str = settings.OPENAI_EMBEDDINGS_MODEL,
        openai_api_key: str = settings.OPENAI_API_KEY,
        dimensions: int = 256,
    ):
        super().__init__(
            model=model_name,
            openai_api_key=openai_api_key,
            dimensions=dimensions,
        )


# Module-level singleton
embeddings_model = EmbeddingsModel()