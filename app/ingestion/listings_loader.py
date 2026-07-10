import os
import sys
import pandas as pd

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from database.connection import DatabaseConnection
from database.connection import DatabaseExecutor
from database.connection import SchemaManager

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


def clean_dataframe(df:pd.DataFrame) -> pd.DataFrame:

    # Columns date information
    column_dates = ['last_scraped', 'host_since', 'price_quote_checkin_date',
                    'price_quote_checkout_date', 'calendar_updated', 'calendar_last_scraped',
                    'first_review', 'last_review']
    
    # Transform data, fill nan values with None
    for col in column_dates:
        if col in df.columns.to_list():
            df[col] = pd.to_datetime(df[col], errors='coerce')
            df[col] = df[col].dt.date
            df[col] = df[col].where(df[col].notna(), None)
        
    df = df.astype(object)
    df = df.where(pd.notnull(df), None)

    # Clean data, drop special characters of amounts and percentages
    if 'price' in df.columns.to_list():
        df['price'] = df['price'].replace(r'[\$,]', '', regex=True).astype(float)
    if 'host_acceptance_rate' in df.columns.to_list():
        df['host_acceptance_rate'] = df['host_acceptance_rate'].replace(r'[%,]', '', regex=True).astype(float)
    if 'host_response_rate' in df.columns.to_list():
        df['host_response_rate'] = df['host_response_rate'].replace(r'[%,]', '', regex=True).astype(float)
    if 'price_quote_total_price' in df.columns.to_list():
        df['price_quote_total_price'] = df['price_quote_total_price'].replace(r'[\$,]', '', regex=True).astype(float)
    if 'price_quote_price_per_night' in df.columns.to_list():
        df['price_quote_price_per_night'] = df['price_quote_price_per_night'].replace(r'[\$,]', '', regex=True).astype(float)

    def parse_bathrooms(text):
        import regex as re
        if pd.isna(text):
            return 0
        elif "Half-bath" in text:
            return 0.5
        elif "Private half-bath" in text:
            return 0.5
        elif "Shared half-bath" in text:
            return 0.5
        match = re.search(r"(\d+(?:\.\d+)?)", text)  
        if match:
            return float(match.group(1))
        return 0 
    
    df["bathrooms"] = (
    df["bathrooms"].fillna(
        df["bathrooms_text"].apply(parse_bathrooms)
    )
    )
    df['bathrooms_text'] = df['bathrooms_text'].fillna(
        df["bathrooms"].astype(str) + " baths")
    df['bedrooms'] = df['bedrooms'].fillna(1)
    df['beds'] = df['beds'].fillna(df['accommodates'] // 2)
    df['minimum_nights'] = df['minimum_nights'].fillna(1)
    df['maximum_nights'] = df['maximum_nights'].fillna(365)
    df["price"] = df["price"].fillna(
        df.groupby(
            ["neighbourhood_cleansed", "property_type", "room_type"]
        )["price"]
        .transform("mean")
    )

    df["price"] = df["price"].fillna(
        df.groupby(
            ["neighbourhood_cleansed"]
        )["price"]
        .transform("mean")
    )

    df['review_scores_accuracy'] = df['review_scores_accuracy'].fillna(-1)
    df['review_scores_communication'] = df['review_scores_communication'].fillna(-1)
    df['review_scores_cleanliness'] = df['review_scores_cleanliness'].fillna(-1)
    df['review_scores_location'] = df['review_scores_location'].fillna(-1)
    df['review_scores_value'] = df['review_scores_value'].fillna(-1)
    df['review_scores_rating'] = df['review_scores_rating'].fillna(-1)
    df['reviews_per_month'] = df['reviews_per_month'].fillna(-1)
    df['instant_bookable'] = df['instant_bookable'].fillna(False)

    df['description'] = df['description'].str.replace('<br />', '')
    df['neighborhood_overview'] = df['neighborhood_overview'].str.replace('<br />', '')

    return df


def load_df_to_database(df:pd.DataFrame) -> None:

    # Prepare available columns in dataframe and build SQL sentence
    columns = df.columns.to_list()
    columns_names = ", ".join(columns)
    placeholders = ", ".join(["%s"] * len(columns))
    update_clause = ", ".join(
        [   f"{col} = COALESCE(EXCLUDED.{col}, listings.{col})"
            for col in columns
            if col != "id"])

    query = f"""
        INSERT INTO listings ({columns_names}) 
        VALUES ({placeholders})
        ON CONFLICT (id) DO UPDATE SET {update_clause}
        """
        # ON CONFLICT (id) DO NOTHING

    # Execute query on database
    with DatabaseConnection() as conn:
        with conn.cursor() as cur:
            for _, row in df.iterrows():
                values = [
                    None if pd.isna(value) else value 
                    for value in row
                ]
                cur.execute(query, values)
        conn.commit()

if __name__ == "__main__":

    print("Initializing database from sql files...")
    # Create connection to database and initialize schema
    SchemaManager().initialize_schema()
    print('Downloading data from https...')
    # listings = read_url('https://data.insideairbnb.com/mexico/df/mexico-city/2025-06-25/data/listings.csv.gz')
    listings = read_url('https://data.insideairbnb.com/mexico/df/mexico-city/2026-03-30/data/listings.csv.gz')
    print('Cleaning data...')
    listings = clean_dataframe(listings)
    print('Uploading data to database...')
    load_df_to_database(listings)
    print('Finished...')