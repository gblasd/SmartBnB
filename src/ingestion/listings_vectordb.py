import datetime, uuid
from datetime import datetime
import numpy as np
from decimal import Decimal

from database.DatabaseConnection import DatabaseConnection
from database.DatabaseExecutor import DatabaseExecutor
from vectordb.chroma_manager import ChromaManager

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

def load_from_postgres():

    # create vector database conection
    vector_db = ChromaManager()

    # create vector database collection
    vector_db.create_vector_database()

    # connect to postgres database, query the data and load to vector database
    with DatabaseConnection() as conn:
        # Query the database to get all records from the listings table
        with conn.cursor() as cur:
            cur.execute("""select l.id, l.listing_url, l.name, l.description, l.neighborhood_overview, l.neighbourhood_cleansed,
                            l.property_type, l.room_type, l.accommodates, l.bathrooms, l.bathrooms_text, l.bedrooms, 
                            l.beds, l.amenities, l.price, l.latitude, l.longitude, l.minimum_nights, l.maximum_nights, 
                            l.has_availability, l.review_scores_accuracy, l.review_scores_communication,
                            l.review_scores_cleanliness, l.review_scores_location, l.review_scores_value, 
                            l.review_scores_rating, l.reviews_per_month, l.instant_bookable,
                            l.calculated_host_listings_count, l.calculated_host_listings_count_entire_homes,
                            l.calculated_host_listings_count_private_rooms, l.calculated_host_listings_count_shared_rooms
                        from public.listings l
                        where l.has_availability is true limit 1""")
            
            records = cur.fetchall()
            for record in records:
                # Add the record to the vector database collection
                row = {}
                row["metadata"] = [
                    {
                        col.name: _sanitize_metadata_value(record[i]) 
                        for i, col in enumerate(cur.description) 
                        if col.name  in ["neighbourhood_cleansed","property_type","room_type", "bathrooms", "bathrooms_text", "bedrooms", "beds",
                                    "price", "latitude", "longitude", "minimum_nights", "maximum_nights", "has_availability", 
                                    "review_scores_accuracy", "amenities"]
                    }
                ]

                # Convert amenities from string to list
                if "amenities" in row["metadata"][0]:
                    amenities_str = row["metadata"][0]["amenities"]
                    amenities_list = [amenity.strip() for amenity in amenities_str.split(",")]
                    row["metadata"][0]["amenities"] = amenities_list

                # insert document to vector database
                vector_db.insert_document(
                    document_id=str(record[0]),
                    document=str(record[3]),
                    metadatas=row["metadata"][0]
                )


def reset_vector_store():
    # create vector database conection
    vector_db = ChromaManager()
    vector_db.get_collection()
    print(f"Deleting {vector_db.collection_name[0]} ...") 
    vector_db.delete_collection()

if __name__ == '__main__':
    print("Loading data into Chrom from PostgreSQL...")
    load_from_postgres()
    print("Finshed...")
    # reset_vector_store()