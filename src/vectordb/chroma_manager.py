from pathlib import Path
import shutil

import chromadb
from chromadb import PersistentClient
from chromadb.config import Settings
from chromadb.utils.embedding_functions import (
    SentenceTransformerEmbeddingFunction
)

class ChromaManager(Chroma):
    def __init__(
        self,
        collection_name: str = "smartbnb_vector_store",
        persist_directory: str = '/Users/gblasd/Documents/SmartBnB/db/chroma_db/',
        embedding_model: str = "paraphrase-multilingual-MiniLM-L12-v2"
    ):
        
        self.collection_name = collection_name,
        self.persist_directory = persist_directory,
        
        self.embedding_function = (
            SentenceTransformerEmbeddingFunction(
                model_name=embedding_model,
                device="cpu",
                normalize_embeddings=True
            )
        )

        self.client = None
        self.collection = None

    def create_vector_database(self):
        self.client = chromadb.PersistentClient(
            path=str(self.persist_directory[0])
        )

        self.collection = (
            self.client.get_or_create_collection(
                name=str(self.collection_name[0]),
                embedding_function=self.embedding_function
            )
        )

        return self.collection

    def get_collection(self):
        if self.collection is None:
            self.create_vector_database()
        return self.collection

    def insert_document(
        self,
        document_id: str,
        document: str,
        metadatas: dict | None = None
    ):
        collection = self.get_collection()
        collection.add(
            ids=[str(document_id)],
            documents=[document],
            metadatas=metadatas or {}
        )

    
    def delete_collection(self):

        if self.client is None:
            self.create_vector_database()
        
        self.client.delete_collection(
            str(self.collection_name[0])
        )

    def delete_vector_database(self):

        self.delete_collection()
        chroma_path = Path(self.persist_directory)

        if chroma_path.exists():
            shutil.rmtree(chroma_path)

    # def search(
    #     self,
    #     query: str,
    #     n_results: int = 5
    # ):

    #     collection = self.get_collection()

    #     return collection.query(
    #         query_texts=[query],
    #         n_results=n_results
    #     )