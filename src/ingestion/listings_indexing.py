import os
import numpy as np
import datetime, uuid
from datetime import datetime
from decimal import Decimal

# PostgreSQL Database
from database.DatabaseConnection import DatabaseConnection

# Embeddings model and Chat
from langchain_openai import OpenAIEmbeddings
# Prompt template
from langchain_core.documents import Document
# Vector database
from langchain_chroma import Chroma
import chromadb

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

# Get Data
def get_documents_from_pg() -> list:

    # return list of Documents
    documents = []
    
    # Define query
    query = """select l.id, l.listing_url, l.name, l.description, l.neighborhood_overview, l.neighbourhood_cleansed,
        l.property_type, l.room_type, l.accommodates, l.bathrooms, l.bathrooms_text, l.bedrooms, 
        l.beds, l.amenities, l.price, l.latitude, l.longitude, l.minimum_nights, l.maximum_nights, 
        l.has_availability, l.review_scores_accuracy, l.review_scores_communication,
        l.review_scores_cleanliness, l.review_scores_location, l.review_scores_value, 
        l.review_scores_rating, l.reviews_per_month, l.instant_bookable,
        l.calculated_host_listings_count, l.calculated_host_listings_count_entire_homes,
        l.calculated_host_listings_count_private_rooms, l.calculated_host_listings_count_shared_rooms
    from public.listings l
   where l.has_availability is true 
     and l.description is not null
   order by length(l.description) desc
   limit 200"""

    metadata_keys = ["neighbourhood_cleansed","property_type",
                        "room_type", "bathrooms", "bathrooms_text", "bedrooms", "beds",
                        "price", "latitude", "longitude", "minimum_nights", 
                        "maximum_nights", "has_availability", 
                        "review_scores_accuracy", "amenities"]
    
    with DatabaseConnection() as conn:
        # query data
        with conn.cursor() as cur:
            cur.execute(query)
            records = cur.fetchall()

            if not records:
                print("No documents!!!")
                return

            for record in records:
                # Add the record to the vector database collection
                row = {}
                row["metadata"] = [{
                    col.name: _sanitize_metadata_value(record[i]) 
                    for i, col in enumerate(cur.description) 
                    if col.name  in metadata_keys
                }]

                # Convert amenities from string to list
                if "amenities" in row["metadata"][0]:
                    amenities_str = row["metadata"][0]["amenities"]
                    amenities_list = [amenity.strip() for amenity in amenities_str.split(",")]
                    row["metadata"][0]["amenities"] = amenities_list

                # create Document object            
                doc = Document(
                    page_content=str(record[3]),
                    metadata=row["metadata"][0],
                    id=record[0]
                )

                documents.append(doc)

    return documents


def indexing_vectors():

    documents = get_documents_from_pg()

    # Initialize the OpenAI embedding model
    embeddings_model = OpenAIEmbeddings( 
        model="text-embedding-3-small", 
        dimensions=256)
    
    vector_store = Chroma.from_documents(
        documents=documents,
        embedding=embeddings_model,
        persist_directory=CHROMA_PATH,
        collection_name='smartbnb_vector_store'
    )

    client = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = client.get_collection('smartbnb_vector_store')
    all_data = collection.get()

    print("Total rows: ", len(vector_store.get(include=["documents"])["documents"]))
    # print(f"Successfully embedded and stored {len(documents)} documents in ChromaDB at {CHROMA_PATH}.")


if __name__ == '__main__':
    print("Loading data into Chroma from PostgreSQL...")
    indexing_vectors()
    print("Finshed...")