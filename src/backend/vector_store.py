"""
LangChain + Chroma vector store for property search.
Uses OpenAI embeddings. Seeds the DB from data/properties.py on first run.
"""

import os
import json
from typing import Optional

from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document

# Persist Chroma on disk so it survives restarts
# CHROMA_DIR = os.path.join(os.path.dirname(__file__), "..", "chroma_db")
# CHROMA_DIR = os.path.abspath(os.path.join("..", "db", "chroma_db"))
CHROMA_DIR = os.path.abspath(os.path.join("db", "chroma_db"))
COLLECTION_NAME = "smartbnb_vector_store"


def _build_documents(properties: list[dict]) -> list[Document]:
    """
    Convert property dicts into LangChain Documents.
    - page_content  → rich text passage that will be embedded
    - metadata      → structured fields used for post-search filtering
    """
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
            "features": json.dumps(p["features"]),  # Chroma requires string values
            "description": p["description"],
        }
        docs.append(Document(page_content=content, metadata=metadata))
    return docs


def get_vector_store(openai_api_key: str) -> Chroma:
    """Return (and lazily seed) the Chroma vector store."""
    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small",
        openai_api_key=openai_api_key,
        dimensions=256
    )
    store = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=CHROMA_DIR,
    )
    return store


def seed_vector_store(store: Chroma, properties: list[dict]) -> int:
    """
    Insert properties into the vector store only if the collection is empty.
    Returns the number of documents inserted (0 if already seeded).
    """
    existing = store.get()
    if existing and existing.get("ids"):
        return 0  # already seeded

    docs = _build_documents(properties)
    ids = [p["id"] for p in properties]
    store.add_documents(docs, ids=ids)
    return len(docs)


def similarity_search(
    store: Chroma,
    query: str,
    k: int = 6,
    filters: Optional[dict] = None,
) -> list[dict]:
    """
    Run a semantic similarity search against the Chroma collection.

    Optional `filters` dict supports:
      - property_type:      "apartment" | "house"
      - max_price: int
      - min_beds:  int

    Returns a list of property dicts with an added `relevance` score (0-1).
    """

    query_results = store.similarity_search(query=query,k=k,filter=filters)

    # return query_results[0].to_json()

    return [document.to_json()['kwargs'] for document in query_results]

    # # Build Chroma where-clause
    # where_clauses = []
    # if filters:
    #     if filters.get("property_type") and filters["property_type"].lower() != "all":
    #         where_clauses.append({"property_type": {"$eq": filters["property_type"].lower()}})
    #     if filters.get("price"):
    #         where_clauses.append({"price": {"$lte": int(filters["price"])}})
    #     if filters.get("beds"):
    #         where_clauses.append({"beds": {"$gte": int(filters["beds"])}})

    # where = None
    # if len(where_clauses) == 1:
    #     where = where_clauses[0]
    # elif len(where_clauses) > 1:
    #     where = {"$and": where_clauses}


    # results = store.similarity_search_with_relevance_scores(
    #     query, k=k, filter=where
    # )

    # properties = []
    # for doc, score in results:
    #     m = doc.metadata
    #     prop = {
    #         "id": m["id"],
    #         "property_type": m["property_type"],
    #         "price": m["price"],
    #         "beds": m["beds"],
    #         "bathrooms": m["bathrooms"],
    #         "area": m["area"],
    #         "address": m["address"],
    #         "neighbourhood": m["neighbourhood"],
    #         "city": m["city"],
    #         "lat": m["lat"],
    #         "lon": m["lon"],
    #         "features": json.loads(m["features"]),
    #         "description": m["description"],
    #         "relevance": round(max(0.0, min(score, 1.0)), 3),
    #     }
    #     properties.append(prop)

    # print(properties)

    # # Sort by relevance descending
    # properties.sort(key=lambda x: x["relevance"], reverse=True)
    # return properties



def get_all(
    store: Chroma
) -> list[dict]:

    return  store.get() 