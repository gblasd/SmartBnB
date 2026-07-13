"""Agent for extracting insights from listing reviews."""

import json
from openai import OpenAI
from app.config import settings
from app.prompts.registry import prompt_registry
from app.services.review_service import get_reviews

def extract_insights(listing_id: int) -> dict:
    reviews = get_reviews(listing_id, limit=50)
    if "error" in reviews:
        return reviews
    
    # Simple extraction for demo: just stringify the dict
    combined = json.dumps(reviews)[:2000] 
    
    system_prompt = prompt_registry.get("review_analysis").render()
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    
    response = client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Analiza estas reseñas:\n\n{combined}"},
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "review_insights",
                "schema": {
                    "type": "object",
                    "properties": {
                        "sentiment": {"type": "string", "enum": ["positive", "mixed", "negative"]},
                        "avg_rating_estimate": {"type": "number"},
                        "top_positives": {"type": "array", "items": {"type": "string"}},
                        "top_negatives": {"type": "array", "items": {"type": "string"}},
                        "key_themes": {"type": "array", "items": {"type": "string"}},
                        "recommendation": {"type": "string"},
                    },
                    "required": ["sentiment", "avg_rating_estimate", "top_positives", "top_negatives", "key_themes", "recommendation"],
                    "additionalProperties": False,
                },
                "strict": True,
            }
        },
    )
    return json.loads(response.choices[0].message.content)
