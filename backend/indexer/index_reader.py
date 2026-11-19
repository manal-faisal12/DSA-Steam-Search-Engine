
"""
Reads the Steam Game Search indexes and provides BM25 search.
Supports refreshing after dynamic content additions.
"""

import json
from pathlib import Path

from backend.tokenizer.tokenizer import tokenize
from backend.search.bm25 import BM25


ROOT = Path(__file__).resolve().parents[2]
INDEX_DIR = ROOT / "data" / "index"


class BarrelStore:
    """Loads inverted-index barrels on demand."""

    def __init__(self, index_dir=INDEX_DIR):
        self.index_dir = Path(index_dir)
        self.cache = {}
        self.refresh()

    def refresh(self):
        """Reload lexicon and statistics and clear cached barrels."""

        with open(
            self.index_dir / "lexicon.json",
            encoding="utf-8",
        ) as file:
            self.lexicon = json.load(file)

        with open(
            self.index_dir / "stats.json",
            encoding="utf-8",
        ) as file:
            self.stats = json.load(file)

        self.cache.clear()

    def get_postings(self, word):
        """Return [(doc_id, term_frequency), ...]."""

        term_id = self.lexicon.get(word)

        if term_id is None:
            return []

        barrel_number = (
            (int(term_id) - 1) // self.stats["terms_per_barrel"]
        )

        if barrel_number not in self.cache:
            barrel_path = (
                self.index_dir
                / "barrels"
                / f"barrel_{barrel_number}.json"
            )

            if not barrel_path.exists():
                return []

            with open(barrel_path, encoding="utf-8") as file:
                self.cache[barrel_number] = json.load(file)

        return self.cache[barrel_number].get(str(term_id), [])


class GameSearchIndex:
    """Connects the file-based index to BM25."""

    def __init__(self, index_dir=INDEX_DIR):
        self.index_dir = Path(index_dir)
        self.barrels = BarrelStore(self.index_dir)
        self.refresh()

    def refresh(self):
        """Reload updated index data after new documents are added."""

        with open(
            self.index_dir / "stats.json",
            encoding="utf-8",
        ) as file:
            self.stats = json.load(file)

        with open(
            self.index_dir / "doc_lengths.json",
            encoding="utf-8",
        ) as file:
            self.doc_lengths = json.load(file)

        self.documents = []

        with open(
            self.index_dir / "documents.jsonl",
            encoding="utf-8",
        ) as file:
            for line in file:
                if line.strip():
                    self.documents.append(json.loads(line))

        self.barrels.refresh()

        self.ranker = BM25(
            num_docs=self.stats["num_docs"],
            avg_doc_len=self.stats["avg_doc_len"],
            doc_lengths=self.doc_lengths,
            get_postings=self.barrels.get_postings,
        )

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
            if 0 <= doc_id < len(self.documents):
                game = self.documents[doc_id]["game"]

                genres = game.get("genres", [])
                if not isinstance(genres, list):
                    genres = [str(genres)] if genres else []

                results.append({
                    "id": game.get("id"),
                    "title": game.get("title"),
                    "description": game.get("short_description", ""),
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
