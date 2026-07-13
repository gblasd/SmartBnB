"""Application configuration settings."""

import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv
load_dotenv()

class Settings(BaseSettings):
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_EMBEDDINGS_MODEL: str = "text-embedding-3-small"
    OPENAI_MODEL: str = "gpt-4o-mini"
    
    DB_PATH: str = "db/airbnb.db"
    EMBEDDINGS_PATH: str = "db/text_embeddings.npy"
    KNN_MODEL_PATH: str = "models/knn_model_text_embeddings.pkl"
    KMEANS_MODEL_PATH: str = "models/kmeans_calendar_streaks.pkl"
    SCALER_PATH: str = "models/scaler_calendar_streaks.pkl"
    CHROMA_DB_DIR: str = "db/chroma_db"
    CHROMA_COLLECTION: str = "smartbnb_vector_store"
    
    PG_HOST: str = "localhost"
    PG_PORT: str = "5433"
    PG_DBNAME: str = "smartbnb"
    PG_USER: str = "admin"
    PG_PASSWORD: str = "admin"
    
    S3_BUCKET: str = "smartbnb-s3"
    AWS_REGION: str = "us-east-2"
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_SESSION_TOKEN: str = ""
    
    BACKEND_URL: str = "http://localhost:8000"

    SQL_GET_LISTINGS: str = os.path.join(os.path.dirname(__file__), "..", "sql", "get_listings.sql")

    class Config:
        env_file = ".env"

settings = Settings()
