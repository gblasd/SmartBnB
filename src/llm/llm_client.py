# Embeddings model and Chat
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
# Prompt template
from langchain_core.prompts import ChatPromptTemplate
# Runnable chains
from langchain_core.runnables import chain
# Query construction
from langchain_classic.chains.query_constructor.base import AttributeInfo
from langchain_classic.retrievers.self_query.base import SelfQueryRetriever
# Vector database
# from langchain_chroma import Chroma

import sys
#sys.path.append("/Users/gblasd/Documents/SmartBnB")
#from src.vectordb.chroma_manager import ChromaManager
from vectordb.chroma_manager import ChromaManager

from chromadb.utils.embedding_functions import (
    SentenceTransformerEmbeddingFunction
)

import os
from dotenv import load_dotenv
# Load variables from .env file
load_dotenv()


# the building blocks
prompt = ChatPromptTemplate.from_template("""Answer the question based on the context below.
Give the user the listing in the documents context as recommendations. The user is looking 
for listings and make the reservation of the listing. You must return the id document

Context: {context}
                                            
Question: {question}

Answer:
""")

# Initialize the OpenAI embedding model
# embeddings = OpenAIEmbeddings(model="text-embedding-3-large", api_key=os.getenv("OPENAI_API_KEY"))
embeddings = SentenceTransformerEmbeddingFunction(
                model_name="paraphrase-multilingual-MiniLM-L12-v2",
                device="cpu"            )

# Create a ChromDB vector database
vector_store = ChromaManager()
vector_store.create_vector_database()
# create retriver
vector_store.as_retriever()

print(vector_store.persist_directory)

# Initialize the model
llm_model = ChatOpenAI(model="gpt-3.5-turbo", temperature=0, api_key=os.getenv("OPENAI_API_KEY"))

# create retriver
retriever = vector_store

# metadata description
description = "Brief summary of listing"

# metadata schema
fields = [
    AttributeInfo(
        name="price",
        description="price per night of the listing. For ranges, use a combination of 'gte' and 'lte' wrapped in an 'and' operator. Do NOT use a 'between' function.",
        type="integer"
    ),
    AttributeInfo(
        name="property_type",
        description="Type of property",
        type="string"
    ),
    AttributeInfo(
        name="room_type",
        description="Type of room",
        type="string"
    ), 
    AttributeInfo(
        name="neighbourhood_cleansed",
        description="The neighbourhood where the listing is located",
        type="string"
    ), 
    AttributeInfo(
        name="review_scores_accuracy",
        description="A 1-5 rating for the listing",
        type="float"
    ),
]

retriever = SelfQueryRetriever.from_llm(
    llm=llm_model,
    vectorstore=vector_store,
    metadata_field_info=fields,
    document_contents=description
)

# Query transform
rewrite_prompt = ChatPromptTemplate.from_template("""Provide a better search
query for web search engine to answer the given question, end the queries
with `**`. You must return or show the document ids from the vectordatabase Question: {x} Answer:""")
def parse_rewriter_output(message):
    return message.content.strip('"').strip("**")
# Rewrite-Retrieve-Read
# LCEL Declarative conposition, optimized execution plan, 
# we dont need to use invoke/stream/batch, it's automatic 
rewriter = rewrite_prompt | llm_model | parse_rewriter_output 


# combine them in a function 
# @chain decorator adds the same Runnable interface for any function you write
# Imperative composition, code into functions and classes
@chain
def chatbot(input):
    # rewrite the query, only for the retriever nd get the relevant documents
    new_query = rewriter.invoke(input)

    # fetch relevant documents
    docs = retriever.get_relevant_documents(input)

    print(docs)

    # format prompt
    formatted = prompt.invoke({"context":docs, "question":input})

    # generate answer
    answer = llm_model.invoke(formatted)

    print(answer)

    return {"answer": answer, "docs": docs}
    # return answer
   

