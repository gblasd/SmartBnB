"""Pydantic schemas used across the system."""

from pydantic import BaseModel, Field

class SearchRequest(BaseModel):
    query: str
    top_k: int = 5
    property_type: str | None = None
    price: int | None = None
    beds: int | None = None

class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    property_type: str | None = None
    price: int | None = None
    beds: int | None = None

class ChatResponse(BaseModel):
    reply: str
    properties: list[dict] | None = None
    session_id: str

class PropertySearchInput(BaseModel):
    query: str
    property_type: str | None = None
    max_price: int | None = None
    min_bedrooms: int | None = None
    k: int = 5

class ReviewInsights(BaseModel):
    sentiment: str
    avg_rating_estimate: float
    top_positives: list[str]
    top_negatives: list[str]
    key_themes: list[str]
    recommendation: str

class AvailabilityPattern(BaseModel):
    listing_id: int
    total_days: int
    available_days: int
    blocked_days: int
    availability_rate: float
    avg_price: float
    min_price: float
    max_price: float
    streaks_summary: dict
    cluster: int | None

class HealthResponse(BaseModel):
    status: str
    vector_store: str
