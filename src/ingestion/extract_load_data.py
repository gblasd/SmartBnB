import os
import numpy as np
import pandas as pd
import sqlite3

from sklearn.preprocessing import LabelEncoder, StandardScaler
import joblib

from pathlib import Path
import psycopg2


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

    listings['price'] = listings['price'].replace(r'[\$,]', '', regex=True).astype(float)

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
    calendar['price'] = calendar['price'].replace(r'[\$,]', '', regex=True).astype(float)

    listings = read_url('https://data.insideairbnb.com/mexico/df/mexico-city/2025-03-19/data/listings.csv.gz')
    # Convert price to numeric (remove $ and ,)
    listings['price'] = listings['price'].replace(r'[\$,]', '', regex=True).astype(float)

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

    
# Download, extract and load data into database
def extract_load_data():
    load_data_listings()
    load_data_reviews()
    load_data_calendar()

def initialize_database(conn):
    sql_dir = Path("sql")
    with conn.cursor() as cur:
        for sql_file in sorted(sql_dir.glob("*.sql")):
            print(f"Running {sql_file.name}")
            with open(sql_file, "r", encoding="utf-8") as f:
                cur.execute(f.read())
    conn.commit()


# Create connection to the database and initialize it
def create_db_connection() -> psycopg2.extensions.connection:
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5433"),
        dbname=os.getenv("DB_NAME", "smartbnb"),
        user=os.getenv("DB_USER", "admin"),
        password=os.getenv("DB_PASSWORD", "admin")
    )
    return conn

def drop_connection(conn):
    conn.close()


def load_data() -> None:
    listings = extract_transform_listings()
    # insert into database
    conn = create_db_connection()
    with conn.cursor() as cur:
        for idx, row in listings.iterrows():
            cur.execute(
                """
                INSERT INTO listings (id, name, description, neighborhood_overview, listing_url, price, accommodates, bathrooms, bedrooms, beds, property_type, amenities_n, room_type, calculated_host_listings_count, calculated_host_listings_count_entire_homes, calculated_host_listings_count_private_rooms, calculated_host_listings_count_shared_rooms, host_is_superhost, host_has_profile_pic, host_identity_verified, host_since_delta, host_response_rate, host_acceptance_rate, host_total_listings_count, host_listings_count, review_scores_rating)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s , %s)
                """,
                (
                    row['id'], row['name'], row['description'], row['neighborhood_overview'], row['listing_url'], 0 if str(row['price']) == 'nan' else int(row['price']) , 
                    int(row['accommodates']), int(row['bathrooms']), int(row['bedrooms']), int(row['beds']), int(row['property_type']), int(row['amenities_n']), 
                    int(row['room_type']), int(row['calculated_host_listings_count']), int(row['calculated_host_listings_count_entire_homes']), 
                    int(row['calculated_host_listings_count_private_rooms']), int(row['calculated_host_listings_count_shared_rooms']), 
                    int(row['host_is_superhost']), int(row['host_has_profile_pic']), int(row['host_identity_verified']), 
                    int(row['host_since_delta']), int(row['host_response_rate']), int(row['host_acceptance_rate']), 
                    int(row['host_total_listings_count']), int(row['host_listings_count']), str(row['review_scores_rating']) # placeholder for review_scores_rating
                )
            )


          
    conn.commit()
    drop_connection(conn)

if __name__ == '__main__':

    # print("Initializing database connection...")
    # conn = create_db_connection()
    # print("Initializing database from sql files...")
    # initialize_database(conn=conn)
    # print("Dropping database connection...")
    # drop_connection(conn)

    #Extract data and load into database if not exists
    # if not os.path.exists('db/airbnb.db'):
    #     extract_load_data()

    load_data()