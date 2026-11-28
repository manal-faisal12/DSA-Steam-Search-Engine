"""Public request and response contracts for the search API."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class GameResult(BaseModel):
    id: str
    title: str
    short_description: str
    release_year: int | None
    price: float
    genres: list[str]

    @field_validator("price", mode="before")
    @classmethod
    def default_missing_price(cls, value):
        return 0.0 if value is None else value


class SearchResponse(BaseModel):
    query: str
    results: list[GameResult]
    total: int = Field(ge=0)
    engine: str


class HealthResponse(BaseModel):
    status: str
    catalogue_loaded: bool
