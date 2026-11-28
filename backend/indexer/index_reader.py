"""
Reads Steam Game Search indexes and provides BM25 search.

Uses byte-offset tables to retrieve individual term postings and individual
documents without loading entire files into memory.
"""

import json
from collections import OrderedDict
from pathlib import Path

from backend.tokenizer.tokenizer import tokenize
from backend.search.bm25 import BM25


ROOT = Path(__file__).resolve().parents[2]
INDEX_DIR = ROOT / "data" / "index"

MAX_CACHED_TERMS = 5000


class BarrelStore:
    """Retrieves individual term postings using byte offsets."""

    def __init__(self, index_dir=INDEX_DIR):
        self.index_dir = Path(index_dir)
        self.cache = OrderedDict()
        self.offset_cache = {}
        self.refresh()

    def refresh(self):
        """Reload lexicon and statistics and clear caches."""

        with open(self.index_dir / "lexicon.json", encoding="utf-8") as file:
            self.lexicon = json.load(file)

        with open(self.index_dir / "stats.json", encoding="utf-8") as file:
            self.stats = json.load(file)

        self.cache.clear()
        self.offset_cache.clear()

    def get_postings(self, word):
        """Return [(doc_id, term_frequency), ...] for a word."""

        term_id = self.lexicon.get(word)

        if term_id is None:
            return []

        term_id = int(term_id)

        barrel_number = (
            (term_id - 1) // self.stats["terms_per_barrel"]
        )

        cache_key = (barrel_number, term_id)

        # Fast path: postings already cached (mark as recently used).
        if cache_key in self.cache:
            self.cache.move_to_end(cache_key)
            return self.cache[cache_key]

        # Cache offset tables separately from postings.
        if barrel_number not in self.offset_cache:
            offset_path = (
                self.index_dir
                / "barrels"
                / f"offsets_{barrel_number}.json"
            )

            if not offset_path.exists():
                return []

            with open(offset_path, encoding="utf-8") as file:
                self.offset_cache[barrel_number] = json.load(file)

        offsets = self.offset_cache[barrel_number]
        offset = offsets.get(str(term_id))

        if offset is None:
            return []

        barrel_path = (
            self.index_dir
            / "barrels"
            / f"barrel_{barrel_number}.jsonl"
        )

        if not barrel_path.exists():
            return []

        # Open in binary mode because offsets represent byte positions.
        with open(barrel_path, "rb") as file:
            file.seek(offset)
            line = file.readline()

        if not line:
            return []

        record = json.loads(line.decode("utf-8"))

        if int(record["term_id"]) != term_id:
            raise ValueError(
                f"Offset mismatch for term ID {term_id}"
            )

        self.cache[cache_key] = record["postings"]

        # Evict the least recently used entry when the cache is full.
        if len(self.cache) > MAX_CACHED_TERMS:
            self.cache.popitem(last=False)

        return record["postings"]


class GameSearchIndex:
    """Connects the file-based index to BM25."""

    def __init__(self, index_dir=INDEX_DIR):
        self.index_dir = Path(index_dir)
        self.barrels = None
        self.refresh()

    def refresh(self):
        """Reload index data after dynamic content additions."""

        with open(self.index_dir / "stats.json", encoding="utf-8") as file:
            self.stats = json.load(file)

        with open(self.index_dir / "doc_lengths.json", encoding="utf-8") as file:
            self.doc_lengths = json.load(file)

        # Only byte offsets are kept in RAM; documents are read on demand.
        with open(self.index_dir / "doc_offsets.json", encoding="utf-8") as file:
            self.doc_offsets = json.load(file)

        if self.barrels is None:
            self.barrels = BarrelStore(self.index_dir)
        else:
            self.barrels.refresh()

        self.ranker = BM25(
            num_docs=self.stats["num_docs"],
            avg_doc_len=self.stats["avg_doc_len"],
            doc_lengths=self.doc_lengths,
            get_postings=self.barrels.get_postings,
        )

    def get_document(self, doc_id):
        """Read one document record from documents.jsonl using its byte offset."""
        with open(self.index_dir / "documents.jsonl", "rb") as file:
            file.seek(self.doc_offsets[doc_id])
            return json.loads(file.readline().decode("utf-8"))

    def search(self, query, top_k=10):
        """Search games using AND semantics and BM25 ranking."""

        terms = tokenize(query, remove_stopwords=True)

        if not terms:
            return []

        ranked_results = self.ranker.search(
            terms,
            top_k=top_k,
            require_all=True,
        )

        results = []

        for doc_id, score in ranked_results:
            if 0 <= doc_id < len(self.doc_offsets):
                game = self.get_document(doc_id)["game"]

                genres = game.get("genres", [])
                if not isinstance(genres, list):
                    genres = [str(genres)] if genres else []

                results.append({
                    "id": game.get("id"),
                    "title": game.get("title"),
                    "description": game.get("short_description", ""),
                    "short_description": game.get("short_description", ""),
                    "release_year": game.get("release_year"),
                    "score": score,
                    "price": game.get("price"),
                    "genres": genres,
                })

        return results


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("query", help="Game search query")
    parser.add_argument("--top", type=int, default=10)

    args = parser.parse_args()

    search_engine = GameSearchIndex()
    results = search_engine.search(args.query, args.top)

    if not results:
        print("No matching games found.")
        return

    for number, game in enumerate(results, start=1):
        print(f"\n{number}. {game['title']}")
        print(f"   Score: {game['score']:.4f}")
        print(f"   Game ID: {game['id']}")
        print(f"   Genres: {', '.join(game['genres'])}")


if __name__ == "__main__":
    main()