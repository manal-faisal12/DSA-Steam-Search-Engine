"""Temporary catalogue search used until the BM25 engine is integrated.

This module is deliberately small and replaceable.  It lets Talal's API and
UI work against real full-scale data without claiming to be Manal's ranking
implementation.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from backend.indexer.parser import SearchDocument, iter_documents
from backend.tokenizer import tokenize


@dataclass(frozen=True)
class SearchMatch:
    document: SearchDocument
    score: tuple[int, int]


class CatalogueSearchService:
    def __init__(self, catalogue_path: Path) -> None:
        self.catalogue_path = catalogue_path
        self._documents: list[SearchDocument] | None = None

    @property
    def loaded(self) -> bool:
        return self._documents is not None

    def _load(self) -> list[SearchDocument]:
        if self._documents is None:
            self._documents = list(iter_documents(self.catalogue_path)) if self.catalogue_path.exists() else []
        return self._documents

    def search(self, query: str, limit: int = 10) -> list[SearchDocument]:
        terms = tokenize(query, remove_stopwords=True) 
        if not terms:
            return []
        matches: list[SearchMatch] = []
        for document in self._load():
            title = document.title.lower()
            text = f"{title} {document.short_description.lower()}"
            title_hits = sum(term in title for term in terms)
            text_hits = sum(term in text for term in terms)
            if text_hits:
                matches.append(SearchMatch(document, (title_hits, text_hits)))
        matches.sort(key=lambda match: (match.score, match.document.popularity), reverse=True)
        return [match.document for match in matches[:limit]]
