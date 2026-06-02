import os
import pandas as pd
import numpy as np
import requests
import sqlite3
import logging
import joblib
import json
from pathlib import Path

from sentence_transformers import SentenceTransformer
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.neighbors import NearestNeighbors


def encode_text_listings(listings: pd.DataFrame) -> pd.DataFrame:
    """
    Encode text data from listings
    - Parameters: 
        - DataFrame: listings dataframe
    - Returns:
        - DataFrame: listings with text columns encoded
    """

    from sentence_transformers import SentenceTransformer
    # from sklearn.preprocessing import StandardScaler # for tabular data, next steps
    import joblib

    text_columns = ['name', 'description', 'amenities_parsed']

    # Fill NaN values with empty strings for the selected text columns
    for col in text_columns:
        listings[col] = listings[col].fillna('')

    # Concatenate the cleaned text columns into 'combined_text'
    listings['combined_text'] = listings.apply(lambda row: ' '.join([str(row[col]) for col in text_columns]), axis=1)

    model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
    text_embeddings = model.encode(listings['combined_text'].tolist(), show_progress_bar=False)

    text_embeddings_df = pd.DataFrame(text_embeddings, index=listings.index)
    listings = pd.concat([listings, text_embeddings_df], axis=1)

    return listings




def read_url(link):
    """ Creates a pandas DataFrame from data online
    - Parameters:
        - link: link to the zipped data
    - Returns:
    """
    import io
    import requests
    import pandas as pd

    # Define URL and extract information
    response = requests.get(link)
    content = response.content
    # Convert into a Pandas DataFrame
    df = pd.read_csv(io.BytesIO(content), sep=',', compression='gzip')

    return df



def get_data_from_db(db_path: str, table_name: str) -> pd.DataFrame:
    """Fetch data from the specified SQLite database table."""
    conn = sqlite3.connect(db_path)
    query = f"SELECT * FROM {table_name}"
    df = pd.read_sql_query(query, conn)
    conn.close()
    logging.info(f"Data fetched from {table_name} table in {db_path} database.")
    return df


def id_mapping_database(listings: pd.DataFrame):
    """Create a mapping between listing IDs and their DataFrame indices in the SQLite database."""
    # Save id mapping in sqlite, index and id
    conn = sqlite3.connect('db/airbnb.db')
    listings.reset_index(drop=False, inplace=True)
    listings['index_df'] = listings.index
    listings[['index_df','id']].to_sql('listing_ids', conn, if_exists='replace')
    conn.close()
    
    logging.info("ID mapping for listings saved successfully.")

def transform_text_listings():
    # Get data from database and encode text listings
    listings = get_data_from_db("db/airbnb.db", "listings")
    listings_encoded = encode_text_listings(listings)
    logging.info("Listings text data encoded successfully.")
    
    # Save the encoded listings to a file npy
    np.save('db/text_embeddings.npy', listings_encoded)
    logging.info("Text embeddings for listings saved successfully. text_embeddings npy created at db/text_embeddings.npy")

    # Create id mapping in database
    id_mapping_database(listings)


# Train ML model for text embeddings encoding
def knn_text_model():
    # if model knn not exists, train it
    if not os.path.exists('models/knn_model_text_embeddings.pkl'):
        logging.info("KNN model not found. Training KNN model...")
        # load data from file npy
        text_embeddings = np.load('db/text_embeddings.npy', allow_pickle=True)
        knn = NearestNeighbors(n_neighbors=5, algorithm='auto')
        knn.fit(text_embeddings)
        # save model to file pkl
        joblib.dump(knn, 'models/knn_model_text_embeddings.pkl')
        logging.info("KNN model trained and saved successfully. Model file created at models/knn_model_text_embeddings.pkl")
    else:
        logging.info("KNN model found. Skipping training.")


# Find listings similar to a given listing based on text embeddings
def find_similar_listings(query_text: str, n_neighbors: int = 5):
    """
    Finds N most similar listings based on a combination of text query and property attributes.

    Args:
        query_text (str): A natural language description of desired listing features.
        query_attributes (dict): A dictionary of desired numerical and categorical attributes
                                 (e.g., {'price': 100, 'room_type': 'Private room', 'accommodates': 2}).
        n_neighbors (int): The number of similar listings to return.

    Returns:
        np.ndarray: An array of indices of the most similar listings in the original DataFrame.
    """
    
    model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

    # Generate text embedding for query_text
    query_text_embedding = model.encode(query_text).reshape(1, -1)

    # Load the saved KNN model pkl
    knn = joblib.load('models/knn_model_text_embeddings.pkl')

    # Use the KNN model to find similar listings
    distances, indices = knn.kneighbors(query_text_embedding, n_neighbors=n_neighbors)

    return indices.flatten()

# function to query listing by id from database sqlite
def get_listing_by_id(listing_id: list[int]) -> pd.DataFrame:
    """
    Retrieves listing details from the SQLite database based on a list of listing IDs.

    Args:
        listing_id (list[int]): A list of listing IDs to retrieve.
    Returns:
        pd.DataFrame: A DataFrame containing the listing details.
    """

    # Create a connection to SQLite database
    conn = sqlite3.connect('db/airbnb.db')

    # Convert list of IDs to a comma-separated string
    id_tuple = tuple(listing_id)

    # Convert np.int64 to native int
    id_tuple = tuple(int(i) for i in id_tuple)

    if len(id_tuple) == 1:
        id_tuple = (id_tuple[0], id_tuple[0])  # Ensure it's a tuple of length 2 for single ID

    # Query to get listings by IDs from listing_ids table and then from listings table
    query = f"""
    SELECT l.*
    FROM listings l
    JOIN listing_ids li ON l.id = li.id
    WHERE li.index_df IN {id_tuple}
    """ 
    
    listings_df = pd.read_sql_query(query, conn)

    # decode data for ['property_type', 'room_type', 'neighbourhood_cleansed'] columns
    # encoder path
    encoder_property_type = joblib.load('models/label_encoder_property_type.pkl')
    listings_df['property_type'] = listings_df['property_type'].map(lambda x: encoder_property_type.inverse_transform([x])[0])

    encoder_neighbourhood_cleansed = joblib.load('models/label_encoder_neighbourhood_cleansed.pkl')
    listings_df['neighbourhood_cleansed'] = listings_df['neighbourhood_cleansed'].map(lambda x: encoder_property_type.inverse_transform([x])[0])

    encoder_room_type = joblib.load('models/label_encoder_room_type.pkl')
    listings_df['room_type'] = listings_df['room_type'].map(lambda x: encoder_property_type.inverse_transform([x])[0])

    conn.close()
    return listings_df



# Function to query similar listings and show example usage
def query_similar_listings_example(query_text: str, n_neighbors: int = 5):
    """Demonstrates how to find similar listings based on a text query.
    Returns json with indices and details of similar listings."""

    # Find similar listings
    similar_listing_indices = find_similar_listings(
        query_text=query_text,
        #query_attributes=sample_query_attributes,
        n_neighbors=n_neighbors
    )

    # print(f"Indices of {n_neighbors} similar listings:", similar_listing_indices)
    # print("\nDetails of similar listings:")

    result = get_listing_by_id(similar_listing_indices)\
        [['id', 'name', 'price', 'description', 'listing_url', 'property_type', 'room_type', 'neighbourhood_cleansed']]
    
    print("[DEBUG] Result columns:")
    print(result.columns)

    return result.to_json(orient='records', force_ascii=False)

def test_query():
    # Example usage of querying similar listings
    example_query = "Apartamento bonito con vista y adecuado para familias"
    json_result = query_similar_listings_example(example_query, n_neighbors=5)
    print("Similar listings to the query:")
    print(json_result)

if __name__ == '__main__':

    #extract_load_data()
    #transform_text_listings()
    #knn_text_model()

    # Extract data and load into database if not exists
    if not os.path.exists('db/airbnb.db'):
        logging.info("Database not found. Extracting and loading data...")
        #extract_load_data()

    # Transform text listings and create embeddings, save to file npy if not exists
    if not os.path.exists('db/text_eßmbeddings.npy'):
        logging.info("Text embeddings not found. Transforming text listings to embeddings...")
        #transform_text_listings() # Run the encoding process

    # Train KNN model for text embeddings if not exists
    if not os.path.exists('db/knn_text_model.pkl'):
        logging.info("KNN model not found. Training KNN model for text embeddings...")
        #knn_text_model() # Train KNN model if not exists

    #aniomes_json_str = get_text_reviews_by_id(listing_id=44616)
    #print(aniomes_json_str)
    