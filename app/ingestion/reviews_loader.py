import pandas as pd
from database.DatabaseConnection import DatabaseConnection
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
    # Time series analysis with calendar data
    if 'date' in df.columns.to_list():
        df['date'] = pd.to_datetime(df['date'])
    return df

def load_df_to_database(df:pd.DataFrame) -> None:
    # Prepare available columns in dataframe and build SQL sentence
    columns = df.columns.to_list()
    columns_names = ", ".join(columns)
    update_clause = ", ".join(
        [   
            f"{col} = COALESCE(EXCLUDED.{col}, reviews.{col})"
            for col in columns
            if col not in ["id"]
        ]
    )

    query = f"""
    INSERT INTO reviews ({columns_names})
    VALUES %s
    ON CONFLICT (id)
    DO UPDATE SET {update_clause}"""

    from psycopg2.extras import execute_values

    records = [
        tuple(None if pd.isna(v) else v for v in row)
        for row in df.itertuples(index=False, name=None)
    ]

    # Execute query on database
    with DatabaseConnection() as conn:
        with conn.cursor() as cur:
            execute_values(
                cur,
                query,
                records,
                page_size=1000
            )
        conn.commit()

if __name__ == "__main__":

    print("Initializing database from sql files...")
    with DatabaseConnection() as conn:
        schema = SchemaManager(conn)
        schema.initialize_database()

    print('Downloading data from https...')
    # reviews = read_url('https://data.insideairbnb.com/mexico/df/mexico-city/2025-06-25/data/reviews.csv.gz')
    reviews = read_url('https://data.insideairbnb.com/mexico/df/mexico-city/2026-03-30/data/reviews.csv.gz')
    print(reviews.shape)
    print('Cleaning data...')
    reviews = clean_dataframe(reviews)
    print(reviews.shape)
    print('Uploading data to database...')
    load_df_to_database(reviews)
    print('Finished...')