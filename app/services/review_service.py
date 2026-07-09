"""Review service for SmartBnB."""

import pandas as pd
from app.database.connection import get_sqlite_connection

def parse_reviews_to_dict(text: str) -> dict:
    result = {}
    if pd.isna(text) or text.strip() == "":
        return result
    for pair in text.split("||"):
        if ":" not in pair:
            continue
        user, comment = pair.split(":", 1)
        result[user.strip()] = comment.strip()
    return result

def get_reviews(listing_id: int, limit: int = 50) -> dict:
    conn = get_sqlite_connection()
    query = f"""SELECT * FROM reviews WHERE listing_id = {listing_id} AND año_trimestre >= 20200"""
    reviews_df = pd.read_sql_query(query, con=conn)
    conn.close()

    if reviews_df.shape == (0, 3):
        return {"error": "No reviews yet"}
    
    reviews_df["all_comments"] = reviews_df["all_comments"].map(lambda x: str(x).replace('<br/>', ''))
    aniomes_json = {}

    for _, row in reviews_df.iterrows():
        aniomes = str(row["año_trimestre"])
        review_dict = parse_reviews_to_dict(row["all_comments"])
        if aniomes not in aniomes_json:
            aniomes_json[aniomes] = {}
        aniomes_json[aniomes].update(review_dict)

    return aniomes_json
