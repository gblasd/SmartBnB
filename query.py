import pandas as pd
import numpy as np
import sqlite3
import joblib
import json
from typing import Optional, List, Dict
from pydantic import BaseModel, Field
from sentence_transformers import SentenceTransformer
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.neighbors import NearestNeighbors

# Find listings similar to a given listing based on text embeddings
def find_similar_listings(query_text: str, n_neighbors: int = 10):
    """
    Finds N most similar listings based on a combination of text query and property attributes.

    Args:
        query_text (str): A natural language description of desired listing features.
        query_attributes (dict): A dictionary of desired numerical and categorical attributes
                                 (e.g., {'price': 100, 'room_type': 'Private room', 'accommodates': 2}).
        n_neighbors (int): The number of similar listings to return.

    Returns:
        np.ndarray: An array of indices of the most similar listings in the original DataFrame.
    """
    
    model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

    # Generate text embedding for query_text
    query_text_embedding = model.encode(query_text).reshape(1, -1)

    # Load the saved KNN model pkl
    knn = joblib.load('models/knn_model_text_embeddings.pkl')

    # Use the KNN model to find similar listings
    distances, indices = knn.kneighbors(query_text_embedding, n_neighbors=n_neighbors)

    return indices.flatten()


# Function to query similar listings and show example usage
def query_similar_listings_example(query_text: str, n_neighbors: int = 10):
    """Demonstrates how to find similar listings based on a text query.
    Returns json with indices and details of similar listings."""

    # Find similar listings
    similar_listing_indices = find_similar_listings(
        query_text=query_text,
        #query_attributes=sample_query_attributes,
        n_neighbors=n_neighbors
    )

    # print(f"Indices of {n_neighbors} similar listings:", similar_listing_indices)
    # print("\nDetails of similar listings:")

    result = get_listing_by_id(similar_listing_indices)\
        [['name', 'price', 'description', 'listing_url', 'property_type', 'room_type', 'neighbourhood_cleansed']]
    
    print("[DEBUG] Result columns:")
    print(result.columns)

    # return result.to_json(orient='records', force_ascii=False)
    return result.to_dict(orient='records')


# function to query listing by id from database sqlite
def get_listing_by_id(listing_id: list[int]) -> pd.DataFrame:
    """
    Retrieves listing details from the SQLite database based on a list of listing IDs.

    Args:
        listing_id (list[int]): A list of listing IDs to retrieve.
    Returns:
        pd.DataFrame: A DataFrame containing the listing details.
    """

    # Create a connection to SQLite database
    conn = sqlite3.connect('db/airbnb.db')

    # Convert list of IDs to a comma-separated string
    id_tuple = tuple(listing_id)

    # Convert np.int64 to native int
    id_tuple = tuple(int(i) for i in id_tuple)

    if len(id_tuple) == 1:
        id_tuple = (id_tuple[0], id_tuple[0])  # Ensure it's a tuple of length 2 for single ID

    # Query to get listings by IDs from listing_ids table and then from listings table
    query = f"""
    SELECT l.*
    FROM listings l
    JOIN listing_ids li ON l.id = li.id
    WHERE li.index_df IN {id_tuple}
    """ 
    
    listings_df = pd.read_sql_query(query, conn)

    # decode data for ['property_type', 'room_type', 'neighbourhood_cleansed'] columns
    # encoder path
    encoder_property_type = joblib.load('models/label_encoder_property_type.pkl')
    listings_df['property_type'] = listings_df['property_type'].map(lambda x: encoder_property_type.inverse_transform([x])[0])

    encoder_neighbourhood_cleansed = joblib.load('models/label_encoder_neighbourhood_cleansed.pkl')
    listings_df['neighbourhood_cleansed'] = listings_df['neighbourhood_cleansed'].map(lambda x: encoder_neighbourhood_cleansed.inverse_transform([x])[0])

    encoder_room_type = joblib.load('models/label_encoder_room_type.pkl')
    listings_df['room_type'] = listings_df['room_type'].map(lambda x: encoder_room_type.inverse_transform([x])[0])

    conn.close()
    return listings_df

def parse_reviews_to_dict(text):
    """Convierte 'user:review||user2:review2' en {user: review, ...}"""
    result = {}
    if pd.isna(text) or text.strip() == "":
        return result
    
    for pair in text.split("||"):
        if ":" not in pair:
            continue
        user, comment = pair.split(":", 1)
        result[user.strip()] = comment.strip()
    return result


# load reviews from database
def _get_text_reviews_by_id(listing_id):

    # connect with the database and query the reviews from the listing_id
    conn = sqlite3.connect("db/airbnb.db")
    query = f"""SELECT * FROM reviews WHERE listing_id = {listing_id} AND año_trimestre >= 20200"""
    reviews_df = pd.read_sql_query(query, con=conn)
    conn.close()

    # if there are no comment, return text "No reviews yet"
    if reviews_df.shape == (0, 3):
        return "No reviews yet"
    
    # Replace wrong characters
    reviews_df["all_comments"] = reviews_df["all_comments"].map(lambda x: str(x).replace('<br/>', ''))
    
    # count number reviews
    reviews_df["no_reviews"] = reviews_df["all_comments"].map(lambda x: len(str(x).split('||')))

    # Creamos el diccionario final
    aniomes_json = {}

    for _, row in reviews_df.iterrows():
        aniomes = str(row["año_trimestre"])
        review_dict = parse_reviews_to_dict(row["all_comments"])

        # Si ya existen entradas para ese aniomes, las acumulamos
        if aniomes not in aniomes_json:
            aniomes_json[aniomes] = {}

        # Merge de usuarios/comentarios dentro del aniomes
        aniomes_json[aniomes].update(review_dict)

    # Convertir a JSON (opcional)
    # aniomes_json_str = json.dumps(aniomes_json, ensure_ascii=False, indent=2)
    
    return aniomes_json


class ReviewsCallInsights(BaseModel):
    """
    Output estructurado con insights clave en español  extraidos de reviews de usuarios.
    """
    listing_id: Optional[int] = Field(description="ID del listing de Airbnb, ej. 44616")
    sentiment : Optional[str] = Field(description="Sentimiento general de las reviews (positivo, negativo, neutral)")
    summary: str = Field(description="Resumen de las reviews destacando puntos clave")
    common_themes: List[str] = Field(description="Temas comunes mencionados en las reviews")
    pros: List[str] = Field(description="Aspectos positivos destacados en las reviews")
    cons: List[str] = Field(description="Aspectos negativos destacados en las reviews")
    suggestions: List[str] = Field(description="Sugerencias de mejora basadas en las reviews")
    
def render_transcript(d: dict) -> str:
    """Renderiza el dict de salida en un formato legible."""
    if not d:
        return "No hay reviews disponibles."
    elif isinstance(d, str):
        return d
    elif isinstance(d, list):
        return "\n".join(d)
    else:
        lines = []
        for key, value in d.items():
            if isinstance(value, list):
                lines.append(f"{key.capitalize()}:")
                for item in value:
                    lines.append(f" - {item}")
            else:
                lines.append(f"{key.capitalize()}: {value}")
    return "\n".join(lines)

def extract_insights(listing_id: int) -> ReviewsCallInsights:
    """
    Obtiene insights clave de reviews de usuarios de Airbnb en español usando OpenAI.
    Arguments:
    - client: instancia del cliente OpenAI
    - reviews_text: diccionario con reviews de usuarios
    - model_openai: nombre del modelo OpenAI a usar
    Returns:
    - un objeto ReviewsCallInsights con los insights extraidos.
    """
    import os
    from dotenv import load_dotenv 
    from openai import OpenAI
    from typing import Optional, List
    from pydantic import BaseModel, Field

    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    client = OpenAI(api_key=OPENAI_API_KEY)
    model_openai = "gpt-5.1"

    # Get reviews text by listing ID
    reviews_text = _get_text_reviews_by_id(listing_id=listing_id)
    
    # Render the transcript text from reviews
    transcript_text = render_transcript(reviews_text)

    # Call OpenAI to extract insights
    response = client.chat.completions.parse(
        model=model_openai,
        messages=[
            {"role": "system", "content": "Eres un asistente útil que extrae insights de los reviews de un listing de airbnb. Devuelve solo un JSON valido que siga exactamente el esquema de ReviewsCallInsights. Salidas en español"},
            {"role": "user", "content": transcript_text}
        ],
        response_format=ReviewsCallInsights
    )

    response_text = response.choices[0].message.parsed
    
    # Parsear la respuesta JSON a ReviewsCallInsights
    # insights = ReviewsCallInsights.model_validate_json(response_text)
    
    return response_text.model_dump()

def extract_pattern_availability(listing_id: int) -> str:
    """
    Extract the availability pattern for a given listing ID.
    """
    import sqlite3
    import pandas as pd
    import joblib

    # extract data from the database
    conn = sqlite3.connect('db/airbnb.db')
    query = f"""SELECT availability_rate, streaks, quarters_with_availability, max_consecutive_months_available
      FROM calendar_streaks WHERE id = {listing_id}"""
    listing_data = pd.read_sql_query(query, conn)
    conn.close()

    # Load the model
    kmeans = joblib.load('models/kmeans_calendar_streaks.pkl')
    scaler = joblib.load('models/scaler_calendar_streaks.pkl')

    if listing_data.empty:
        return "Listing ID not found."

    # Prepare data for prediction
    features = [
        'availability_rate', 
        'streaks', 
        'quarters_with_availability', 
        'max_consecutive_months_available'
    ]
    X_listing = listing_data[features].fillna(0)
    X_scaled = scaler.transform(X_listing)

    # Predict cluster
    cluster_label = kmeans.predict(X_scaled)[0]

    # Map cluster label to name
    # Name of clusters based on availability patterns
    cluster_names = {
        0: 'Estacion Larga',
        1: 'Estacion Corta',
        2: 'Tiempo Parcial',
        3: 'Casi Disponible',
        4: 'Siempre Disponible',
        5: 'Evento Motivado',
        6: 'Bloqueado',
        7: 'Esporadico'
    }

    cluster_names_intuition = {
        0 : "Disponibilidad concentrada en temporadas largas.",
        1 : "Disponibilidad en temporadas cortas o específicas.",
        2 : "Disponibilidad parcial a lo largo del año.",
        3 : "Disponibilidad frecuente pero con algunas ausencias.",
        4 : "Disponibilidad casi completa durante todo el año.",
        5 : "Disponibilidad influenciada por eventos específicos.",
        6 : "Propiedad bloqueada o no disponible.",
        7 : "Disponibilidad esporádica sin un patrón claro."
    }

    cluster_name = cluster_names[cluster_label]
    intuition = cluster_names_intuition[cluster_label]

    # build json response
    response = {
        "listing_id": listing_id,
        # "cluster_label": int(cluster_label),
        "cluster_name": cluster_name,
        "intuition": intuition
    }

    return response

get_similar_listings_json = {
    "name": "query_similar_listings_example",
    "description": "Usa esta herramienta (tool) para obtener los listings de airbnb que coinciden con la descripción proporcionada por el usuario. \
                    Evita busquedas ajenas a la herramienta proporcionada como url o recomendadores de internet.\
                    Contrasta siempre con las amenidades que también provee la herramienta para dar insights sin ser recomendación de compra o venta.",
    "parameters": {
        "type": "object",
        "properties": {
            "query_text": {
                "type": "string",
                "description": "La descripción en lenguaje natural para buscar listings similares."
            },
            "n_neighbors": {
                "type": "integer",
                "description": "Número de listings similares a retornar.",
                "default": 10
            }
        },
        "required": ["query_text"],
        "additionalProperties": False
    }
}


get_extract_insights_from_json = {
    "name": "extract_insights",
    "description": "Devuelve una tabla con reseñas individuales para un listing específico.",
    "parameters": {
        "type": "object",
        "properties": {
            "listing_id": {
                "type": "integer",
                "description": "ID del listing de Airbnb para obtener reseñas."
            }
        },
        "required": ["listing_id"],
        "additionalProperties": False
    }
}

get_extract_pattern_availability_json = {
    "name": "extract_pattern_availability",
    "description": "Extrae el patrón de disponibilidad de un listing específico.",
    "parameters": {
        "type": "object",
        "properties": {
            "listing_id": {
                "type": "integer",
                "description": "ID del listing de Airbnb para obtener el patrón de disponibilidad."
            }
        },
        "required": ["listing_id"],
        "additionalProperties": False
    }
}

tools = [
    {"type": "function", "function": get_similar_listings_json},
    {"type": "function", "function": get_extract_insights_from_json},
    {"type": "function", "function": get_extract_pattern_availability_json},
]

def handle_tool_calls(tool_calls):
    results = []
    for tool_call in tool_calls:
        tool_name = tool_call.function.name
        arguments = json.loads(tool_call.function.arguments)
        print(f"Tool called: {tool_name}", flush=True)
        tool = globals().get(tool_name)
        result = tool(**arguments) if tool else {}
        results.append({"role": "tool","content": json.dumps(result),"tool_call_id": tool_call.id})
    return results

system_prompt = (
    "Eres un experto en recomendaciones de SmartBnB. Responde siempre en español. "
    "Cuando el usuario pida recomendaciones de propiedades usa la herramienta query_similar_listings_example, acompletando con detalles de las amenidades, usa extract_pattern_availability para dar contexto completo si es necesario."
    "Cuando el usuario pida insights de reviews usa la herramienta extract_insights y complementa con extract_pattern_availability para dar contexto completo."
    "Proporciona respuestas claras y concisas basadas en los datos disponibles."
)