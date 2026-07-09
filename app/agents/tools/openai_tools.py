"""OpenAI tool definitions for the SmartBnB dashboard."""

tools = [
    {
        "type": "function",
        "function": {
            "name": "query_similar_listings",
            "description": "Busca listados similares por ID o filtra por vecindario, tipo de propiedad o tipo de habitación.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query_text": {"type": "string", "description": "Texto de búsqueda natural"},
                    "n_neighbors": {"type": "integer", "description": "Número de resultados (default 5)"},
                },
                "required": ["query_text"],
                "additionalProperties": False,
            },
            "strict": True,
        }
    },
    {
        "type": "function",
        "function": {
            "name": "extract_insights",
            "description": "Analiza las reseñas de un listado y extrae insights como sentimiento, temas clave, positivos y negativos.",
            "parameters": {
                "type": "object",
                "properties": {
                    "listing_id": {"type": "integer", "description": "ID del listado a analizar"},
                },
                "required": ["listing_id"],
                "additionalProperties": False,
            },
            "strict": True,
        }
    },
    {
        "type": "function",
        "function": {
            "name": "extract_pattern_availability",
            "description": "Analiza patrones de disponibilidad del calendario de un listado.",
            "parameters": {
                "type": "object",
                "properties": {
                    "listing_id": {"type": "integer", "description": "ID del listado a analizar"},
                },
                "required": ["listing_id"],
                "additionalProperties": False,
            },
            "strict": True,
        }
    },
]
