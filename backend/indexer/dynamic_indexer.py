"""
Dynamic Indexer for Steam Game Search Engine.

Adds new games to an existing file-based index.
Appends to the document and forward-index files, updates the byte-offset
table, and rewrites only the barrels that contain the new game's terms.
stats.json is written last and acts as the commit point.
"""

import json
import os
import tempfile
from collections import defaultdict
from pathlib import Path

from backend.indexer.index_builder import (
    get_searchable_text,
    write_barrel,
)
from backend.tokenizer.tokenizer import tokenize


ROOT = Path(__file__).resolve().parents[2]
INDEX_DIR = ROOT / "data" / "index"


def atomic_write_json(path, data):
    """Write JSON safely using a temporary file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    fd, temp_name = tempfile.mkstemp(
        dir=str(path.parent),
        suffix=".tmp",
        text=True,
    )

    try:
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)

        os.replace(temp_name, path)

    except Exception:
        if os.path.exists(temp_name):
            os.remove(temp_name)
        raise


class DynamicIndexer:
    """Adds new documents to an existing index."""

    def __init__(self, index_dir=INDEX_DIR):
        self.index_dir = Path(index_dir)
        self.barrel_dir = self.index_dir / "barrels"

        if not (self.index_dir / "stats.json").exists():
            raise FileNotFoundError(
                "Index not found. Build the initial index first."
            )

    def _load_barrel(self, barrel_number):
        """Load all term postings from one JSONL barrel."""
        barrel_path = (
            self.barrel_dir / f"barrel_{barrel_number}.jsonl"
        )

        term_postings = {}

        if not barrel_path.exists():
            return term_postings

        with open(barrel_path, "r", encoding="utf-8") as file:
            for line in file:
                if not line.strip():
                    continue

                record = json.loads(line)

                term_postings[str(record["term_id"])] = (
                    record["postings"]
                )

        return term_postings

    def add_game(self, game):
        """
        Add one game dictionary to the existing index.

        Returns the new internal document ID.
        """

        if not isinstance(game, dict):
            raise TypeError("Game must be a dictionary.")

        if game.get("id") is None or str(game.get("id")).strip() == "":
            raise ValueError("Game must have a unique 'id' field.")

        stats_path = self.index_dir / "stats.json"
        lexicon_path = self.index_dir / "lexicon.json"
        documents_path = self.index_dir / "documents.jsonl"
        forward_path = self.index_dir / "forward_index.jsonl"
        lengths_path = self.index_dir / "doc_lengths.json"
        offsets_path = self.index_dir / "doc_offsets.json"

        with open(lexicon_path, encoding="utf-8") as file:
            lexicon = json.load(file)

        with open(stats_path, encoding="utf-8") as file:
            stats = json.load(file)

        with open(lengths_path, encoding="utf-8") as file:
            document_lengths = json.load(file)

        with open(offsets_path, encoding="utf-8") as file:
            doc_offsets = json.load(file)

        # Stream through documents.jsonl once: reject duplicate external IDs
        # and count the existing documents (the count is the new doc_id).
        doc_id = 0

        with open(documents_path, encoding="utf-8") as file:
            for line in file:
                if not line.strip():
                    continue

                existing_game = json.loads(line).get("game", {})

                if str(existing_game.get("id")) == str(game["id"]):
                    raise ValueError(
                        f"Game ID {game['id']} already exists."
                    )

                doc_id += 1

        # A previous crash can leave extra lines in documents.jsonl.
        if doc_id != len(document_lengths) or doc_id != len(doc_offsets):
            raise RuntimeError(
                "Index files are inconsistent (possible interrupted add). "
                "Rebuild the index."
            )

        words = tokenize(
            get_searchable_text(game),
            remove_stopwords=True,
        )

        if not words:
            raise ValueError("Game contains no searchable words.")

        term_positions = defaultdict(list)

        next_term_id = max(
            (int(value) for value in lexicon.values()),
            default=0,
        ) + 1

        for position, word in enumerate(words):
            if word not in lexicon:
                lexicon[word] = next_term_id
                next_term_id += 1

            term_positions[word].append(position)

        forward_terms = []

        # Group updates by barrel so each barrel is rewritten once.
        updated_barrels = {}

        for word, positions in term_positions.items():
            term_id = int(lexicon[word])
            frequency = len(positions)

            forward_terms.append({
                "term_id": term_id,
                "frequency": frequency,
                "positions": positions,
            })

            barrel_number = (
                (term_id - 1) // stats["terms_per_barrel"]
            )

            if barrel_number not in updated_barrels:
                updated_barrels[barrel_number] = self._load_barrel(
                    barrel_number
                )

            postings = updated_barrels[barrel_number].setdefault(
                str(term_id), []
            )

            postings.append([doc_id, frequency])

        document_lengths.append(len(words))

        stats["num_docs"] = doc_id + 1
        stats["num_terms"] = len(lexicon)
        stats["avg_doc_len"] = (
            sum(document_lengths) / len(document_lengths)
        )
        stats["num_barrels"] = max(
            len(list(self.barrel_dir.glob("barrel_*.jsonl"))),
            (max(updated_barrels) + 1) if updated_barrels else 0,
        )

        # ---- Save everything. stats.json goes LAST (commit point). ----

        # The new document starts at the current end of documents.jsonl.
        doc_offsets.append(documents_path.stat().st_size)

        # Binary append with manual encoding keeps byte offsets exact
        # (text mode would write "\r\n" on Windows).
        with open(documents_path, "ab") as file:
            file.write(
                (
                    json.dumps(
                        {"doc_id": doc_id, "game": game},
                        ensure_ascii=False,
                    ) + "\n"
                ).encode("utf-8")
            )

        with open(forward_path, "ab") as file:
            file.write(
                (
                    json.dumps(
                        {"doc_id": doc_id, "terms": forward_terms}
                    ) + "\n"
                ).encode("utf-8")
            )

        atomic_write_json(offsets_path, doc_offsets)
        atomic_write_json(lengths_path, document_lengths)
        atomic_write_json(lexicon_path, lexicon)

        for barrel_number, term_postings in updated_barrels.items():
            write_barrel(
                self.barrel_dir,
                barrel_number,
                term_postings,
            )

        atomic_write_json(stats_path, stats)

        return doc_id

    def add_json_file(self, json_path):
        """Add one game stored in a JSON file."""
        json_path = Path(json_path)

        with open(json_path, encoding="utf-8-sig") as file:
            game = json.load(file)

        return self.add_game(game)

    def add_text(self, title, description, game_id):
        """Add plain-text content as a searchable game record."""

        game = {
            "id": str(game_id),
            "title": title,
            "description": description,
            "short_description": description,
            "genres": [],
            "tags": [],
            "categories": [],
            "developers": [],
            "publishers": [],
        }

        return self.add_game(game)


if __name__ == "__main__":
    print(
        "DynamicIndexer is ready. "
        "Import it to add new games to the existing index."
    )