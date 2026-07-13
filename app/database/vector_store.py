"""LangChain + Chroma vector store operations."""

import json
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document
from app.config import settings

def _embeddings():
    return OpenAIEmbeddings(
        model="text-embedding-3-small",
        openai_api_key=settings.OPENAI_API_KEY,
        dimensions=256
    )

def get_vector_store() -> Chroma:
    return Chroma(
        collection_name=settings.CHROMA_COLLECTION,
        embedding_function=_embeddings(),
        persist_directory=settings.CHROMA_DB_DIR,
    )

def _build_documents(properties: list[dict]) -> list[Document]:
    docs = []
    for p in properties:
        features_str = ", ".join(p["features"])
        content = (
            f"{p['property_type'].capitalize()} in {p['neighbourhood']}, {p['city']}. "
            f"{p['bedrooms']} bedrooms, {p['bathrooms']} bathrooms, {p['area']} m². "
            f"Price: ${p['price']:,} USD. Features: {features_str}. "
            f"{p['description']}"
        )
        metadata = {
            "id": p["id"],
            "property_type": p["property_type"],
            "price": p["price"],
            "bedrooms": p["bedrooms"],
            "bathrooms": p["bathrooms"],
            "area": p["area"],
            "address": p["address"],
            "neighbourhood": p["neighbourhood"],
            "city": p["city"],
            "lat": p["lat"],
            "lon": p["lon"],
            "features": json.dumps(p["features"]),
            "description": p["description"],
        }
        docs.append(Document(page_content=content, metadata=metadata))
    return docs

def seed_vector_store(store: Chroma, properties: list[dict]) -> int:
    existing = store.get()
    if existing and existing.get("ids"):
        return 0
    docs = _build_documents(properties)
    ids = [str(p["id"]) for p in properties]
    store.add_documents(docs, ids=ids)
    return len(docs)

def similarity_search(store: Chroma, query: str, k: int = 6, filters: dict | None = None) -> list[dict]:
    query_results = store.similarity_search(query=query, k=k, filter=filters)
    return [document.to_json()['kwargs'] for document in query_results]

def get_all(store: Chroma) -> list[dict]:
    return store.get()
