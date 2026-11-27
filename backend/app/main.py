"""FastAPI application for the Steam search interface."""

from __future__ import annotations

import os
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .schemas import GameResult, HealthResponse, SearchResponse, SuggestResponse, Suggestion
from .search_service import IndexSearchService, IndexUnavailableError, SearchFilters

DEFAULT_INDEX_DIR = Path(os.environ.get("STEAM_INDEX_DIR", "data/index"))
DEFAULT_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173"


def _allowed_origins() -> list[str]:
    raw = os.environ.get("CORS_ORIGINS", DEFAULT_ORIGINS)
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


def create_app(index_dir: Path | None = None) -> FastAPI:
    app = FastAPI(title="Steam Games Search API", version="0.2.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_allowed_origins(),
        allow_credentials=False,
        allow_methods=["GET"],
        allow_headers=["*"],
    )
    service = IndexSearchService(index_dir or DEFAULT_INDEX_DIR)
    app.state.search_service = service

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(status="ok", index_loaded=service.loaded)

    @app.get("/search", response_model=SearchResponse)
    def search(
        query: str = Query(min_length=1, max_length=200),
        limit: int = Query(default=10, ge=1, le=50),
        offset: int = Query(default=0, ge=0),
        genre: str | None = Query(default=None, max_length=60),
        min_price: float | None = Query(default=None, ge=0),
        max_price: float | None = Query(default=None, ge=0),
        year_from: int | None = Query(default=None, ge=1970, le=2100),
        year_to: int | None = Query(default=None, ge=1970, le=2100),
    ) -> SearchResponse:
        filters = SearchFilters(genre or None, min_price, max_price, year_from, year_to)
        try:
            page = service.search(query, limit=limit, offset=offset, filters=filters)
        except IndexUnavailableError as error:
            raise HTTPException(status_code=503, detail=str(error)) from error
        return SearchResponse(
            query=query,
            results=[GameResult(**row) for row in page.results],
            total=page.total,
            offset=offset,
            limit=limit,
            took_ms=round(page.took_ms, 2),
            engine="bm25_barrels",
        )

    @app.get("/suggest", response_model=SuggestResponse)
    def suggest(
        q: str = Query(min_length=1, max_length=100),
        limit: int = Query(default=5, ge=1, le=5),
    ) -> SuggestResponse:
        started = time.perf_counter()
        try:
            rows = service.suggest(q, limit)
        except IndexUnavailableError as error:
            raise HTTPException(status_code=503, detail=str(error)) from error
        return SuggestResponse(
            prefix=q,
            suggestions=[Suggestion(**row) for row in rows],
            took_ms=round((time.perf_counter() - started) * 1000, 3),
        )

    return app


app = create_app()
