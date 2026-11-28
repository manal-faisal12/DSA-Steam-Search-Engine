"""Shared tokenizer. Use the SAME function when building the index and when parsing queries."""
import re
import unicodedata
from collections.abc import Iterable

_TOKEN_RE = re.compile(r"[a-z0-9]+")

# Small stopword list; extend if needed. Keep it tiny so queries like "the witcher" still work.
STOPWORDS = frozenset(
    "a an and are as at be by for from in is it of on or the to with".split()
)


def _fold_accents(text: str) -> str:
    """'pokémon' -> 'pokemon' so accented words are not split into fragments."""
    if text.isascii():
        return text
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def normalize_text(value) -> str:
    """Lowercase, fold accents and collapse whitespace."""
    if value is None:
        return ""
    return " ".join(_fold_accents(str(value).lower()).split())


def tokenize(text: str, remove_stopwords: bool = False) -> list[str]:
    """
    Lowercase, fold accents, split on non-alphanumerics.
    remove_stopwords=True also drops stopwords and single-letter junk (the 's' in "don't").
    The index is built with remove_stopwords=True, so queries must use it too.
    """
    tokens = _TOKEN_RE.findall(_fold_accents((text or "").lower()))
    if remove_stopwords:
        tokens = [t for t in tokens if t not in STOPWORDS and (len(t) > 1 or t.isdigit())]
    return tokens


def unique_tokens(values: Iterable, remove_stopwords: bool = True) -> list[str]:
    """Tokenize several values and keep each token once, in first-seen order."""
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        for token in tokenize(str(value or ""), remove_stopwords=remove_stopwords):
            if token not in seen:
                seen.add(token)
                result.append(token)
    return result