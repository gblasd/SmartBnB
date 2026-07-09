"""Database initialization and KNN model management."""

import sqlite3
import numpy as np
import json
from pathlib import Path
from sentence_transformers import SentenceTransformer
from sklearn.neighbors import NearestNeighbors
import joblib
from app.config import settings

def get_connection():
    return sqlite3.connect(settings.DB_PATH)

def init():
    if not Path(settings.DB_PATH).exists():
        print(f"Database not found at {settings.DB_PATH}")
    if not Path(settings.EMBEDDINGS_PATH).exists():
        print("Embeddings not found.")
    if not Path(settings.KNN_MODEL_PATH).exists():
        print("KNN model not found.")
