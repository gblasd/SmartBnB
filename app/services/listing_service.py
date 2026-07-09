"""Listing service for SmartBnB."""

import pandas as pd
import numpy as np
import joblib
from sentence_transformers import SentenceTransformer
from app.config import settings
from app.database.connection import get_sqlite_connection

def find_similar_listings(query_text: str, n_neighbors: int = 10) -> np.ndarray:
    model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
    query_text_embedding = model.encode(query_text).reshape(1, -1)
    knn = joblib.load(settings.KNN_MODEL_PATH)
    distances, indices = knn.kneighbors(query_text_embedding, n_neighbors=n_neighbors)
    return indices.flatten()

def get_listing_by_id(listing_id: list[int]) -> pd.DataFrame:
    conn = get_sqlite_connection()
    id_tuple = tuple(int(i) for i in listing_id)
    if len(id_tuple) == 1:
        id_tuple = (id_tuple[0], id_tuple[0])

    query = f"""
    SELECT l.*
    FROM listings l
    JOIN listing_ids li ON l.id = li.id
    WHERE li.index_df IN {id_tuple}
    """ 
    listings_df = pd.read_sql_query(query, conn)
    conn.close()

    encoder_property_type = joblib.load('models/label_encoder_property_type.pkl')
    listings_df['property_type'] = listings_df['property_type'].map(lambda x: encoder_property_type.inverse_transform([x])[0])

    encoder_neighbourhood_cleansed = joblib.load('models/label_encoder_neighbourhood_cleansed.pkl')
    listings_df['neighbourhood_cleansed'] = listings_df['neighbourhood_cleansed'].map(lambda x: encoder_neighbourhood_cleansed.inverse_transform([x])[0])

    encoder_room_type = joblib.load('models/label_encoder_room_type.pkl')
    listings_df['room_type'] = listings_df['room_type'].map(lambda x: encoder_room_type.inverse_transform([x])[0])

    return listings_df

def query_similar_listings(query_text: str, n_neighbors: int = 10) -> list[dict]:
    similar_listing_indices = find_similar_listings(query_text=query_text, n_neighbors=n_neighbors)
    result = get_listing_by_id(similar_listing_indices)[['name', 'price', 'description', 'listing_url', 'property_type', 'room_type', 'neighbourhood_cleansed']]
    return result.to_dict(orient='records')
