"""Search service that connects the API to the file-based BM25 index.

The service owns no ranking logic.  It tokenizes the query exactly like the
indexer does, asks the BM25 ranker for matches, applies optional metadata
filters and slices out one page of results.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from backend.indexer.index_reader import GameSearchIndex
from backend.tokenizer.tokenizer import tokenize


class IndexUnavailableError(RuntimeError):
    """Raised when the search index has not been built yet."""


@dataclass(frozen=True)
class SearchFilters:
    genre: str | None = None
    min_price: float | None = None
    max_price: float | None = None
    year_from: int | None = None
    year_to: int | None = None

    @property
    def active(self) -> bool:
        return any(value is not None for value in (
            self.genre, self.min_price, self.max_price, self.year_from, self.year_to,
        ))

    def matches(self, game: dict[str, Any]) -> bool:
        if self.genre is not None:
            wanted = self.genre.casefold()
            labels = [str(label).casefold() for label in _as_list(game.get("genres"))]
            if wanted not in labels:
                return False
        price = _to_float(game.get("price"))
        if self.min_price is not None and price < self.min_price:
            return False
        if self.max_price is not None and price > self.max_price:
            return False
        if self.year_from is not None or self.year_to is not None:
            year = game.get("release_year")
            if not isinstance(year, int):
                return False
            if self.year_from is not None and year < self.year_from:
                return False
            if self.year_to is not None and year > self.year_to:
                return False
        return True


@dataclass
class SearchPage:
    total: int
    results: list[dict[str, Any]]
    took_ms: float = 0.0
    terms: list[str] = field(default_factory=list)


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    return [value] if value else []


def _to_float(value: Any) -> float:
    try:
        return max(float(value), 0.0)
    except (TypeError, ValueError):
        return 0.0


class IndexSearchService:
    """Lazy wrapper around :class:`GameSearchIndex`."""

    def __init__(self, index_dir: Path) -> None:
        self.index_dir = Path(index_dir)
        self._index: GameSearchIndex | None = None
        self._lock = threading.Lock()

    @property
    def loaded(self) -> bool:
        return self._index is not None

    @property
    def index(self) -> GameSearchIndex:
        if self._index is None:
            with self._lock:
                if self._index is None:
                    if not (self.index_dir / "stats.json").exists():
                        raise IndexUnavailableError(
                            f"No search index found in {self.index_dir}. "
                            "Run: python -m backend.indexer.index_builder"
                        )
                    self._index = GameSearchIndex(self.index_dir)
        return self._index

    def reload(self) -> None:
        """Re-read the index files, e.g. after new games were added."""
        with self._lock:
            if self._index is None:
                return
            self._index.refresh()

    def search(
        self,
        query: str,
        limit: int = 10,
        offset: int = 0,
        filters: SearchFilters | None = None,
    ) -> SearchPage:
        started = time.perf_counter()
        index = self.index
        terms = tokenize(query, remove_stopwords=True)
        if not terms:
            return SearchPage(total=0, results=[], terms=[])

        documents = index.documents
        candidate_filter = None
        if filters is not None and filters.active:
            def candidate_filter(doc_id: int) -> bool:
                return 0 <= doc_id < len(documents) and filters.matches(documents[doc_id]["game"])

        ranked = index.ranker.search(
            terms, top_k=None, require_all=True, candidate_filter=candidate_filter,
        )
        page = ranked[offset:offset + limit]
        results = [
            _to_result(documents[doc_id]["game"], score)
            for doc_id, score in page
            if 0 <= doc_id < len(documents)
        ]
        took = (time.perf_counter() - started) * 1000
        return SearchPage(total=len(ranked), results=results, took_ms=took, terms=terms)


def _to_result(game: dict[str, Any], score: float) -> dict[str, Any]:
    year = game.get("release_year")
    return {
        "id": str(game.get("id")),
        "title": str(game.get("title", "")),
        "short_description": str(game.get("short_description") or game.get("description") or ""),
        "release_year": year if isinstance(year, int) else None,
        "price": _to_float(game.get("price")),
        "genres": [str(label) for label in _as_list(game.get("genres"))],
        "score": round(float(score), 4),
    }
