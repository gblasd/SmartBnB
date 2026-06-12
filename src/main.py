
"""
The backend leverages FastAPI to create an API endpoint that handles the LLM orchestrating logic.
"""

import os
from fastapi import FastAPI
from pydantic import BaseModel

from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# App
app = FastAPI(title="LangChain RAG API")

# Initialize components
CHROMA_PATH = os.path.abspath(os.path.join("..", "db", "chroma_db"))
def get_vector_store() -> Chroma:
    # Initialize the OpenAI embedding model
    embeddings_model = OpenAIEmbeddings(
        model="text-embedding-3-small",
        dimensions=256 
    )
    return Chroma(
        persist_directory=CHROMA_PATH,
        embedding_function=embeddings_model,
        collection_name='smartbnb_vector_store'
        )


class QueryRequest(BaseModel):
    question: str


@app.get("/")
def read_root():
    return {"Hello":"World"}

@app.get("/listings/{item_str}/{k_int}")
#def read_item(item_id : int, q : str | None = None):
def read_item(item_str : str, k : int):
    # load vector store
    vector_store = get_vector_store()
    # query data 
    results = vector_store.similarity_search(
        query = item_str, k = k, )
    # return formatted data
    return [document.to_json()['kwargs'] for document in results]

@app.post("/query")
def query_db(request: QueryRequest):
    """Retrieve context from Chroma"""
    # load vector store
    vector_store = get_vector_store()
    # query data
    results = vector_store.similarity_search_with_score(
        query = request.question, k = 3, )
    # formatted data
    return [document.to_json() for document, _ in results]
