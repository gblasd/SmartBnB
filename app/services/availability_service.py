"""Availability service for SmartBnB."""

import numpy as np
import joblib
import pandas as pd
from app.config import settings
from app.database.connection import get_sqlite_connection

def get_calendar_data(listing_id: int) -> list[tuple]:
    conn = get_sqlite_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT date, available, price, minimum_nights, maximum_nights FROM calendar WHERE listing_id = ? ORDER BY date",
        (listing_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return rows
