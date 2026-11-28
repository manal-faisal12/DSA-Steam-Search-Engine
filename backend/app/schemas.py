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


class Suggestion(BaseModel):
    text: str
    kind: str


class SuggestResponse(BaseModel):
    prefix: str
    suggestions: list[Suggestion]
    took_ms: float = Field(ge=0)


class NewGame(BaseModel):
    """A game submitted through the add-content form or a JSON/text upload."""

    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=20000)
    short_description: str = Field(default="", max_length=1000)
    release_year: int | None = Field(default=None, ge=1970, le=2100)
    price: float = Field(default=0.0, ge=0)
    genres: list[str] = Field(default_factory=list, max_length=20)
    tags: list[str] = Field(default_factory=list, max_length=40)
    id: str | None = Field(default=None, max_length=60)

    @field_validator("title", "description")
    @classmethod
    def not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value


class AddGamesRequest(BaseModel):
    games: list[NewGame] = Field(min_length=1, max_length=200)


class JobStatus(BaseModel):
    job_id: str
    status: str
    total: int
    added: int
    error: str | None = None
    ids: list[str] = Field(default_factory=list)
