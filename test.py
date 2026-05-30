import os
from init_db import extract_load_data

def test_db():

    # Extract data and load into database if not exists
    assert os.path.exists('db/airbnb.db') is True

    # Transform text listings and create embeddings, save to file npy if not exists
    assert os.path.exists('db/text_embeddings.npy') is True

    # Train KNN model for text embeddings if not exists
    assert os.path.exists('models/knn_model_text_embeddings.pkl') is True
