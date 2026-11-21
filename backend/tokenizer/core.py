"""Deterministic tokenization shared by indexing and query-time code."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable

from .stopwords import STOPWORDS

_TOKEN_RE = re.compile(r"[a-z0-9]+(?:'[a-z0-9]+)?")


def normalize_text(value: object) -> str:
    """Return a Unicode-normalized, lowercase representation of *value*."""
    if value is None:
        return ""
    text = unicodedata.normalize("NFKC", str(value)).lower()
    return " ".join(text.split())


def tokenize(value: object, *, remove_stopwords: bool = True) -> list[str]:
    """Split text into normalized word tokens without stemming.

    Stemming is deliberately not applied: game names, franchises and tags are
    proper nouns where aggressive stemming would harm autocomplete and matching.
    """
    tokens = _TOKEN_RE.findall(normalize_text(value))
    if remove_stopwords:
        return [token for token in tokens if token not in STOPWORDS]
    return tokens


def unique_tokens(values: Iterable[object]) -> list[str]:
    """Tokenize several values and retain first-seen tokens once each."""
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        for token in tokenize(value):
            if token not in seen:
                seen.add(token)
                result.append(token)
    return result
