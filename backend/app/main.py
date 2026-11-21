"""FastAPI application for the Steam search interface."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from .schemas import GameResult, HealthResponse, SearchResponse
from .search_service import CatalogueSearchService

DEFAULT_CATALOGUE = Path("index/catalogue/games.jsonl")


def create_app(catalogue_path: Path = DEFAULT_CATALOGUE) -> FastAPI:
    app = FastAPI(title="Steam Games Search API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_credentials=False,
        allow_methods=["GET"],
        allow_headers=["*"],
    )
    service = CatalogueSearchService(catalogue_path)

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(status="ok", catalogue_loaded=service.loaded)

    @app.get("/search", response_model=SearchResponse)
    def search(query: str = Query(min_length=1, max_length=200), limit: int = Query(default=10, ge=1, le=50)) -> SearchResponse:
        documents = service.search(query, limit)
        results = [
            GameResult(
                id=document.id,
                title=document.title,
                short_description=document.short_description,
                release_year=document.release_year,
                price=document.price,
                genres=document.genres,
            )
            for document in documents
        ]
        return SearchResponse(query=query, results=results, total=len(results), engine="temporary_catalogue_match")

    return app


app = create_app()
