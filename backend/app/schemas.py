"""Public request and response contracts for the search API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class GameResult(BaseModel):
    id: str
    title: str
    short_description: str
    release_year: int | None
    price: float
    genres: list[str]
    score: float = 0.0


class SearchResponse(BaseModel):
    query: str
    results: list[GameResult]
    total: int = Field(ge=0)
    offset: int = Field(ge=0)
    limit: int = Field(ge=1)
    took_ms: float = Field(ge=0)
    engine: str


class HealthResponse(BaseModel):
    status: str
    index_loaded: bool
