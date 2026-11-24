"""
Own implementation of Okapi BM25 (no external ranking libraries).

    score(D, Q) = sum over q in Q of  IDF(q) * tf * (k1 + 1) / (tf + k1 * (1 - b + b * |D| / avgdl))
    IDF(q)      = ln(1 + (N - df + 0.5) / (df + 0.5))        (never negative)

The scorer does NOT know how the index is stored. It only needs:
  * corpus stats (N, avgdl, per-document length)
  * a `get_postings(term)` callable returning [(doc_id, tf), ...]

Plug in your barrel loader as `get_postings`, so only the barrels a query needs
are read from disk.
"""
from __future__ import annotations

import heapq
import json
import math
from array import array
from typing import Callable, Iterable, Sequence

Postings = Sequence[tuple[int, int]]  # [(doc_id, term_frequency), ...]


def idf(num_docs: int, doc_freq: int) -> float:
    return math.log(1.0 + (num_docs - doc_freq + 0.5) / (doc_freq + 0.5))


class BM25:
    def __init__(
        self,
        num_docs: int,
        avg_doc_len: float,
        doc_lengths: Sequence[int],
        get_postings: Callable[[str], Postings],
        k1: float = 1.2,
        b: float = 0.75,
    ):
        self.N = num_docs
        self.avgdl = avg_doc_len or 1.0
        self.doc_len = doc_lengths  # indexable by doc_id
        self.get_postings = get_postings
        self.k1 = k1
        self.b = b

    # ---- scoring -------------------------------------------------------
    def term_score(self, tf: int, doc_id: int, term_idf: float) -> float:
        norm = self.k1 * (1.0 - self.b + self.b * self.doc_len[doc_id] / self.avgdl)
        return term_idf * tf * (self.k1 + 1.0) / (tf + norm)

    def search(
        self,
        terms: Iterable[str],
        top_k: int | None = 10,
        require_all: bool = True,
        candidate_filter: Callable[[int], bool] | None = None,
    ) -> list[tuple[int, float]]:
        """
        Returns [(doc_id, score)] sorted by score desc.
        require_all=True  -> AND semantics (every query word must appear, any position).
        candidate_filter  -> optional predicate on doc_id (genre/price/year filters).
        """
        terms = list(dict.fromkeys(terms))  # dedupe, keep order
        if not terms:
            return []

        postings = {t: self.get_postings(t) for t in terms}
        if require_all and any(len(p) == 0 for p in postings.values()):
            return []

        allowed: set[int] | None = None
        if require_all:
            # intersect starting from the rarest term (cheapest)
            ordered = sorted(postings.values(), key=len)
            allowed = {d for d, _ in ordered[0]}
            for plist in ordered[1:]:
                allowed &= {d for d, _ in plist}
                if not allowed:
                    return []

        scores: dict[int, float] = {}
        for term, plist in postings.items():
            if not plist:
                continue
            w = idf(self.N, len(plist))
            for doc_id, tf in plist:
                if allowed is not None and doc_id not in allowed:
                    continue
                if candidate_filter is not None and not candidate_filter(doc_id):
                    continue
                scores[doc_id] = scores.get(doc_id, 0.0) + self.term_score(tf, doc_id, w)

        if top_k is None:
            return sorted(scores.items(), key=lambda x: (-x[1], x[0]))
        return heapq.nlargest(top_k, scores.items(), key=lambda x: (x[1], -x[0]))

    def search_weighted(
        self,
        required_terms: Iterable[str],
        optional_terms: dict[str, float] | None = None,
        top_k: int | None = 10,
        candidate_filter: Callable[[int], bool] | None = None,
    ) -> list[tuple[int, float]]:
        """
        Required terms use AND semantics. Optional terms (e.g. GloVe expansions,
        weight 0-1) only add a down-weighted bonus to documents that already
        match every required term; they never add new candidates.
        """
        required = list(dict.fromkeys(required_terms))
        scores = dict(self.search(required, top_k=None, require_all=True,
                                  candidate_filter=candidate_filter))
        if not scores:
            return []

        for term, weight in (optional_terms or {}).items():
            if term in required:
                continue
            plist = self.get_postings(term)
            if not plist:
                continue
            w = idf(self.N, len(plist)) * weight
            for doc_id, tf in plist:
                if doc_id in scores:
                    scores[doc_id] += self.term_score(tf, doc_id, w)

        if top_k is None:
            return sorted(scores.items(), key=lambda x: (-x[1], x[0]))
        return heapq.nlargest(top_k, scores.items(), key=lambda x: (x[1], -x[0]))

# ---- corpus stats persistence (file-based, no database) ------------------
def save_stats(path_prefix: str, doc_lengths: Sequence[int]) -> None:
    """Writes <prefix>.json (N, avgdl) and <prefix>.lens (uint32 array indexed by doc_id)."""
    n = len(doc_lengths)
    avgdl = sum(doc_lengths) / n if n else 0.0
    with open(path_prefix + ".json", "w") as f:
        json.dump({"num_docs": n, "avg_doc_len": avgdl}, f)
    with open(path_prefix + ".lens", "wb") as f:
        array("I", doc_lengths).tofile(f)


def load_stats(path_prefix: str) -> tuple[int, float, array]:
    with open(path_prefix + ".json") as f:
        meta = json.load(f)
    lens = array("I")
    with open(path_prefix + ".lens", "rb") as f:
        lens.fromfile(f, meta["num_docs"])
    return meta["num_docs"], meta["avg_doc_len"], lens