import pandas as pd

from database.DatabaseConnection import DatabaseConnection
from database.DatabaseExecutor import DatabaseExecutor
from database.SchemaManager import SchemaManager

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
    with DatabaseConnection() as conn:
        schema = SchemaManager(conn)
        schema.initialize_database()

    print('Downloading data from https...')
    #listings = read_url('https://data.insideairbnb.com/mexico/df/mexico-city/2025-06-25/data/listings.csv.gz')
    listings = read_url('https://data.insideairbnb.com/mexico/df/mexico-city/2026-03-30/data/listings.csv.gz')
    print('Cleaning data...')
    listings = clean_dataframe(listings)
    print('Uploading data to database...')
    load_df_to_database(listings)
    print('Finished...')