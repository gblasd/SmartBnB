import os
import sys
import numpy as np
import datetime, uuid
from datetime import datetime
from decimal import Decimal

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# PostgreSQL Database
from database.connection import DatabaseExecutor
# Embeddings model and Chat
from services.embeddings import EmbeddingsModel
# Prompt template
from langchain_core.documents import Document
# Vector database
from langchain_chroma import Chroma
import chromadb

from config import settings

CHROMA_PATH = os.path.abspath(os.path.join("..", "db", "chroma_db"))
# Load environment variables
from dotenv import load_dotenv
load_dotenv()

def _sanitize_metadata_value(v):

    # to contain only str, int, float, or bool
    if isinstance(v, (str, int, float, bool)):
        return v
    elif v is None:
        return None
    elif isinstance(v, (Decimal,)):
        return float(v)
    elif isinstance(v, (list, tuple)):
        return [_sanitize_metadata_value(i) for i in v]
    elif isinstance(v, dict):
        return {k: _sanitize_metadata_value(v) for k, v in v.items()}
    elif isinstance(v, (set, frozenset)):
        return [_sanitize_metadata_value(i) for i in v]
    elif isinstance(v, (np.ndarray,)):
        return v.tolist()
    elif isinstance(v, (datetime.datetime, datetime.date)):
        return v.isoformat()
    elif isinstance(v, uuid.UUID):
        return str(v)
    return v

def load_query_from_file(file_path: str) -> str:
    """Load SQL query from a file."""
    with open(file_path, 'r') as file:
        return file.read()

# Get Data
def get_documents_from_pg() -> list:

    # return list of Documents
    documents = []
    
    # Define query
    query = load_query_from_file(settings.SQL_GET_LISTINGS)

    metadata_keys = ["neighbourhood_cleansed","property_type",
                        "room_type", "bathrooms", "bathrooms_text", "bedrooms", "beds",
                        "price", "latitude", "longitude", "minimum_nights", 
                        "maximum_nights", "has_availability", 
                        "review_scores_accuracy", "amenities"]
    
    records = DatabaseExecutor().execute(query)
    if not records:
        print("No documents!!!")
        return
        
    for i, col in enumerate(records[0]):

        # Insert record into database collection
        row = {}
        row["metadata"] = {
            col.name: _sanitize_metadata_value(i) 
            for i, col in enumerate(records[0])
            if col in metadata_keys
        }   

        # Convert amenities from string to list
        if "amenities" in row["metadata"]:
            amenities_str = row["metadata"]["amenities"]
            amenities_list = [amenity.strip() for amenity in amenities_str.split(",")]
            row["metadata"]["amenities"] = amenities_list

        # Create Document object
        doc = Document(
            page_content=str(col.value),
            metadata=row["metadata"],
            id=col.id
        )   

        documents.append(doc)

    return documents


def indexing_vectors():

    documents = get_documents_from_pg()

    # Initialize the OpenAI embedding model
    embeddings_model = EmbeddingsModel()
    
    vector_store = Chroma.from_documents(
        documents=documents,
        embedding=embeddings_model,
        persist_directory=CHROMA_PATH,
        collection_name=settings.CHROMA_COLLECTION
    )

    client = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = client.get_collection(settings.CHROMA_COLLECTION)
    all_data = collection.get()

    print("Total rows: ", len(vector_store.get(include=["documents"])["documents"]))
    # print(f"Successfully embedded and stored {len(documents)} documents in ChromaDB at {CHROMA_PATH}.")


if __name__ == '__main__':

    documents = get_documents_from_pg()

    # print("Loading data into Chroma from PostgreSQL...")
    # indexing_vectors()
    # print("Finshed...")