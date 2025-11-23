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


def extract_transform_listings() -> pd.DataFrame:
    listings = read_url('https://data.insideairbnb.com/mexico/df/mexico-city/2025-06-25/data/listings.csv.gz')

    listings['price'] = listings['price'].replace('[\$,]', '', regex=True).astype(float)

    # listings.filter(like='host_').columns
    host_factors = [
        'host_is_superhost',
        'host_has_profile_pic',
        'host_identity_verified',
        #'host_since_delta',
        'host_since', # new feature: days since host joined
        'host_response_rate',
        'host_acceptance_rate',
        'host_total_listings_count',
        'host_listings_count'
    ]

    listings["host_is_superhost"] = listings["host_is_superhost"].map({'t': 1, 'f': 0})
    listings["host_is_superhost"] = listings["host_is_superhost"].fillna(2) # 2 means unknown
    listings["host_has_profile_pic"] = listings["host_has_profile_pic"].map({'t': 1, 'f': 0})
    listings["host_has_profile_pic"] = listings["host_has_profile_pic"].fillna(2) # 2 means unknown
    listings["host_identity_verified"] = listings["host_identity_verified"].map({'t': 1, 'f': 0})
    listings["host_identity_verified"] = listings["host_identity_verified"].fillna(2) # 2 means unknown
    listings["host_since"]  = pd.to_datetime(listings["host_since"], errors='coerce') # create delta days from today
    listings["host_since_delta"] = (pd.Timestamp('2025-06-25') - listings["host_since"]).dt.days
    listings["host_since_delta"] = listings["host_since_delta"].fillna(listings["host_since_delta"].median())
    listings["host_response_rate"] = listings["host_response_rate"].str.replace('%', '').astype(float)
    listings["host_response_rate"] = listings["host_response_rate"].fillna(listings["host_response_rate"].median())
    listings["host_acceptance_rate"] = listings["host_acceptance_rate"].str.replace('%', '').astype(float)
    listings["host_acceptance_rate"] = listings["host_acceptance_rate"].fillna(listings["host_acceptance_rate"].median())
    listings["host_total_listings_count"] = listings["host_total_listings_count"].fillna(1) # assume 1 because they have a listing
    listings["host_listings_count"] = listings["host_listings_count"].fillna(1) # assume 1 because they have a listing

    host_factors = [  x if x != "host_since" else "host_since_delta" for x in host_factors ]
    # host_factors

    function_factors = [
        'price',
        'accommodates', # number of guests
        'bathrooms',
        'bedrooms',
        'beds',
        'property_type',
        'amenities',
        'room_type',
        'calculated_host_listings_count',
        'calculated_host_listings_count_entire_homes',
        'calculated_host_listings_count_private_rooms',
        'calculated_host_listings_count_shared_rooms'
    ]

    def extract_amenities(amenities_str):
        amenities_str = str(amenities_str)
        amenities_list = []
        if pd.isna(amenities_str):
            return None
        amenities_str = amenities_str.replace('"', '').replace('[', '').replace(']', '')
        amenities_list = [amenity.strip() for amenity in amenities_str.split(',')]
        return len(amenities_list)
    
    listings["bathrooms"] = listings["bathrooms"].fillna(0) # shared
    listings["bedrooms"] = listings["bedrooms"].fillna(0) # shared bedroom
    listings["beds"] = listings["beds"].fillna(1) # at least one bed

    listings["amenities_n"] = listings["amenities"].map(lambda x: extract_amenities(x))
    listings["bathrooms"] = listings["bathrooms"].astype(int)
    listings["bedrooms"] = listings["bedrooms"].astype(int)
    listings["beds"] = listings["beds"].astype(int)

    listings['amenities_parsed'] = listings['amenities'].apply(lambda x: str(x).strip('{}').replace('"', '').replace('[', '').replace(']', '').split(', '))
    # convert list to str before save the database
    listings['amenities_parsed'] = listings['amenities_parsed'].apply(lambda x: ', '.join(x) if isinstance(x, list) else '')


    # Cambio a variables nuevas
    function_factors = [x if x != "amenities" else "amenities_n" for x in function_factors]
    function_factors.append('amenities_parsed')

    reputation_factors = [
        'number_of_reviews',
        'reviews_per_month',
        'review_scores_rating', # this is general
        'review_scores_accuracy',
        'review_scores_cleanliness',
        'review_scores_checkin',
        'review_scores_communication',
        'review_scores_location',
        'review_scores_value',
        'number_of_reviews_ltm',
        'number_of_reviews_l30d',
        'first_review', # delta
        'last_review', # delta
    ]

    listings['reviews_per_month'] = listings['reviews_per_month'].fillna(listings['reviews_per_month'].median())
    listings['review_scores_rating'] = listings['review_scores_rating'].fillna(listings['review_scores_rating'].median())
    listings['review_scores_accuracy'] = listings['review_scores_accuracy'].fillna(listings['review_scores_accuracy'].median())
    listings['review_scores_cleanliness'] = listings['review_scores_cleanliness'].fillna(listings['review_scores_cleanliness'].median())
    listings['review_scores_checkin'] = listings['review_scores_checkin'].fillna(listings['review_scores_checkin'].median())
    listings['review_scores_communication'] = listings['review_scores_communication'].fillna(listings['review_scores_communication'].median())
    listings['review_scores_location'] = listings['review_scores_location'].fillna(listings['review_scores_location'].median())
    listings['review_scores_value'] = listings['review_scores_value'].fillna(listings['review_scores_value'].median())
    listings['reviews_per_month'] = listings['reviews_per_month'].fillna(listings['reviews_per_month'].median())

    listings["first_review"]  = pd.to_datetime(listings["first_review"], errors='coerce') # create delta days from today
    listings["first_review"] = (pd.Timestamp('2025-06-25') - listings["first_review"]).dt.days
    listings["first_review"] = listings["first_review"].fillna(listings["first_review"].median())

    listings["last_review"]  = pd.to_datetime(listings["last_review"], errors='coerce') # create delta days from today
    listings["last_review"] = (pd.Timestamp('2025-06-25') - listings["last_review"]).dt.days
    listings["last_review"] = listings["last_review"].fillna(listings["last_review"].median())

    listings["number_of_reviews"] = listings["number_of_reviews"].astype(int)
    listings["reviews_per_month"] = listings["reviews_per_month"].astype(int)
    listings["number_of_reviews_ltm"] = listings["number_of_reviews_ltm"].astype(int)
    listings["number_of_reviews_l30d"] = listings["number_of_reviews_l30d"].astype(int)
    listings["first_review"] = listings["first_review"].astype(int)
    listings["last_review"] = listings["last_review"].astype(int)
    listings["reviews_per_month"] = listings["reviews_per_month"].astype(int)

    listings["review_scores_rating"] = listings["review_scores_rating"].astype(float)
    listings["review_scores_accuracy"] = listings["review_scores_accuracy"].astype(float)
    listings["review_scores_cleanliness"] = listings["review_scores_cleanliness"].astype(float)
    listings["review_scores_checkin"] = listings["review_scores_checkin"].astype(float)
    listings["review_scores_communication"] = listings["review_scores_communication"].astype(float)
    listings["review_scores_location"] = listings["review_scores_location"].astype(float)
    listings["review_scores_value"] = listings["review_scores_value"].astype(float)
    listings["review_scores_cleanliness"] = listings["review_scores_cleanliness"].astype(float)

    location_factors = [
        'neighbourhood_cleansed',
        'latitude',
        'longitude'
    ]

    misellaneous_factors = [
        'minimum_nights',
        'maximum_nights',
        'minimum_minimum_nights',
        'maximum_minimum_nights',
        'minimum_maximum_nights',
        'maximum_maximum_nights',
        'minimum_nights_avg_ntm',
        'maximum_nights_avg_ntm',
        'has_availability',
        'availability_30',
        'availability_60',
        'availability_90',
        'availability_365',
        'instant_bookable'
    ]

    listings["has_availability"] = listings["has_availability"].fillna('f')
    listings["has_availability"] = listings["has_availability"].map({'t': 1, 'f': 0})
    listings["instant_bookable"] = listings["instant_bookable"].map({'t': 1, 'f': 0})
    listings["minimum_minimum_nights"] = listings["minimum_minimum_nights"].fillna(listings["minimum_minimum_nights"].median())
    listings["maximum_minimum_nights"] = listings["maximum_minimum_nights"].fillna(listings["maximum_minimum_nights"].median())
    listings["minimum_maximum_nights"] = listings["minimum_maximum_nights"].fillna(listings["minimum_maximum_nights"].median())
    listings["maximum_maximum_nights"] = listings["maximum_maximum_nights"].fillna(listings["maximum_maximum_nights"].median())

    # Items encoder for categorical variables
    structural_columns = host_factors + function_factors + reputation_factors + location_factors + misellaneous_factors

    # all columns except amenities_parsed
    categorical_columns = listings[structural_columns].select_dtypes(exclude=['int64', 'float64']).columns.tolist()
    categorical_columns.remove('amenities_parsed')

    for col in categorical_columns:
        lb = LabelEncoder()

        # Convert to string
        col_data = listings[col].astype(str)

        # Fit + transform
        lb.fit(col_data)
        listings[col] = lb.transform(col_data)

        # Save encoder
        joblib.dump(lb, f'models/label_encoder_{col}.pkl')

        print(f'Added encoded column for: {col}')
        #print("Current shape:", listings.shape)
        #print("-----------------------------------")
        #print("Final:", listings.shape)

    # get colums encoded
    columns_encoded = listings[categorical_columns].select_dtypes(exclude=['int64', 'float64']).columns

    # Drop amenities (text) column from structural columns
    structural_columns.remove('amenities_parsed')

    # Fit scaler and save it
    scaler = StandardScaler()
    struct_matrix = scaler.fit_transform(listings[structural_columns].select_dtypes(include=['int64', 'float64']))
    joblib.dump(scaler, 'models/structural_scaler.pkl')

    info_cols = [
        'id',
        'name',
        'description',
        'neighborhood_overview',
        'listing_url'
    ]

    # add info columns
    structural_columns += info_cols
    # add amenities_parsed
    structural_columns.append('amenities_parsed')

    return listings[structural_columns]

def extract_transform_reviews() -> pd.DataFrame:

    reviews = read_url('https://data.insideairbnb.com/mexico/df/mexico-city/2025-06-25/data/reviews.csv.gz')

    # añadimos numero de año_trimestre en que se realizo el comentario en una columna nueva
    reviews['date'] = pd.to_datetime(reviews['date'])
    # Finalmente, lo convertimos a entero para tener un valor numérico.
    reviews['año_trimestre'] = (reviews['date'].dt.year.astype(str) + 
                        reviews['date'].dt.quarter.astype(str)).astype(int)
    
    # Agrupa por listing_id y año_trimestre y concatena los comentarios como "usuario:comentario"
    def _combine_comments(df):
        tmp = df.loc[df['comments'].notna(), ['reviewer_name', 'reviewer_id', 'comments']].copy()
        if tmp.empty:
            return ''
        tmp['reviewer_name'] = tmp['reviewer_name'].fillna(tmp['reviewer_id'].astype(str))
        tmp['comments'] = tmp['comments'].astype(str).str.replace(r'\s+', ' ', regex=True).str.strip()
        return ' || '.join(tmp['reviewer_name'].astype(str) + ':' + tmp['comments'])

    grouped_comments = reviews.groupby(['listing_id', 'año_trimestre']).apply(_combine_comments).reset_index(name='all_comments')
    return grouped_comments


def extract_transform_calendar() -> pd.DataFrame:
    calendar = read_url('https://data.insideairbnb.com/mexico/df/mexico-city/2025-06-25/data/calendar.csv.gz')
    # Time series analysis with calendar data
    calendar['date'] = pd.to_datetime(calendar['date'])
    # Convert price to numeric (remove $ and ,)
    calendar['price'] = calendar['price'].replace('[\$,]', '', regex=True).astype(float)

    listings = read_url('https://data.insideairbnb.com/mexico/df/mexico-city/2025-03-19/data/listings.csv.gz')
    # Convert price to numeric (remove $ and ,)
    listings['price'] = listings['price'].replace('[\$,]', '', regex=True).astype(float)

    # availability rate
    # We calculate the corresponding Nights Intended to be available.
    listings['availability_rate'] = listings['availability_365'].map(lambda x: x/365)

    # get random listing on listings DataFrame
    #list_sample = listings.sample()
    # Find the data in calendar DataFrame
    #listing_selected = calendar[calendar['listing_id'] == int(list_sample['id'])]
    #listing_selected['available'] = listing_selected['available'].map(lambda x: x == 't')

    # Time series plot: availability by date for listing_selected
    #listing_selected['date'] = pd.to_datetime(listing_selected['date'])

    # Find streaks of availability and unavailability in listing_selectec
    def find_streaks(df, min_streak=2):
        """
        Finds streaks of available and unavailable periods with at least min_streak consecutive days.
        Returns a list of tuples: (start_date, end_date, available, streak_length)
        """
        streaks = []
        current = None
        streak_start = None
        streak_len = 0

        for idx, row in df.iterrows():
            avail = row['available']
            date = row['date']
            if current is None:
                current = avail
                streak_start = date
                streak_len = 1
            elif avail == current:
                streak_len += 1
            else:
                if streak_len >= min_streak:
                    streaks.append((streak_start, date - pd.Timedelta(days=1), current, streak_len))
                current = avail
                streak_start = date
                streak_len = 1
        # Add last streak
        if streak_len >= min_streak:
            streaks.append((streak_start, date, current, streak_len))
        return streaks


    def get_streaks(calendar_listing: pd.DataFrame) -> int:
        """
        Compute and return number streaks
        """

        # Ensure sorted by date
        listing_selected = calendar_listing.sort_values('date').reset_index(drop=True)

        # Find all streaks
        all_streaks = find_streaks(listing_selected, min_streak=2)

        # Count and return streaks
        streaks_by_listing = pd.DataFrame(all_streaks, columns=['available_start', 'available_end', 'available', 'available_length'])

        return streaks_by_listing[streaks_by_listing['available'] == 't'].shape[0]


    # add new column with value of streaks
    listings['streaks'] = listings['id'].map(
        lambda id : get_streaks(calendar[calendar['listing_id'] == int(id)])
    )

    # Seasonality
    def quarters_with_availability(calendar_listing: pd.DataFrame) -> int:
        """
        Returns the number of quarters (3-month periods) with at least one night available.
        """
        if calendar_listing.empty:
            return 0
        df = calendar_listing.copy()
        df['date'] = pd.to_datetime(df['date'])
        # Map 'available' to boolean if not already
        if df['available'].dtype != bool:
            df['available'] = df['available'].map(lambda x: x == 't')
        df['quarter'] = df['date'].dt.to_period('Q')
        quarters = df[df['available']].groupby('quarter').size()
        return len(quarters)

    # Example: add as a feature to listings DataFrame
    listings['quarters_with_availability'] = listings['id'].map(
        lambda id: quarters_with_availability(calendar[calendar['listing_id'] == int(id)])
    )

    def max_consecutive_months_available(calendar_listing: pd.DataFrame) -> int:
        """
        Returns the maximum number of consecutive months with at least one night available.
        """
        if calendar_listing.empty:
            return 0
        df = calendar_listing.copy()
        df['date'] = pd.to_datetime(df['date'])
        # Map 'available' to boolean if not already
        if df['available'].dtype != bool:
            df['available'] = df['available'].map(lambda x: x == 't')
        # Get months with at least one available night
        months = df[df['available']].copy()
        if months.empty:
            return 0
        months['month'] = months['date'].dt.to_period('M')
        unique_months = sorted(months['month'].unique())
        # Find max consecutive months
        max_streak = streak = 1 if unique_months else 0
        for i in range(1, len(unique_months)):
            if unique_months[i-1] + 1 == unique_months[i]:
                streak += 1
                max_streak = max(max_streak, streak)
            else:
                streak = 1
        return max_streak

    # Add as a feature to listings DataFrame
    listings['max_consecutive_months_available'] = listings['id'].map(
        lambda id: max_consecutive_months_available(calendar[calendar['listing_id'] == int(id)])
    )

    # Truncate values upper the percentile 99 
    p99_values = {
        'price': listings['price'].quantile(.99)
    }

    for col, upper_limit in p99_values.items():
        #pass
        listings[col] = listings[col].clip(upper=upper_limit)

    features = [
        'availability_rate', 
        'streaks', 
        'quarters_with_availability', 
        'max_consecutive_months_available', 
        'latitude', 'longitude', 
        'price',
        'room_type', 
        'neighbourhood_cleansed',
        'id'  # include 'id' for reference
    ]

    return listings[features]

def load_data_listings():
    conn = sqlite3.connect('db/airbnb.db')
    df = extract_transform_listings()
    df.to_sql('listings', conn, if_exists='replace', index=False)
    df = None
    conn.close()
    print("Data listings loaded successfully!")

def load_data_reviews():
    conn = sqlite3.connect('db/airbnb.db')
    df = extract_transform_reviews()
    df.to_sql('reviews', conn, if_exists='replace', index=False)
    df = None
    conn.close()
    print("Data reviews loaded successfully!")

def load_data_calendar():
    conn = sqlite3.connect('db/airbnb.db')
    df = extract_transform_calendar()
    df.to_sql('calendar', conn, if_exists='replace', index=False)
    df = None
    conn.close()
    print("Data calendar loaded successfully!")


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

    
# Download, extract and load data into database
def extract_load_data():
    load_data_listings()
    load_data_reviews()
    load_data_calendar()

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

    aniomes_json_str = get_text_reviews_by_id(listing_id=44616)
    print(aniomes_json_str)
    