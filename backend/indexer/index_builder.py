
"""
Steam Game Search Engine - Index Builder

Creates:
1. Lexicon: word -> term ID
2. Forward index: document -> terms and positions
3. Inverted index: term -> documents and frequencies
4. Barrels: JSONL files containing term postings
5. Offset tables: term ID -> byte position in barrel
6. Document storage and statistics
"""

import argparse
import json
from collections import defaultdict
from pathlib import Path

from backend.tokenizer.tokenizer import tokenize


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA = ROOT / "data" / "test" / "games_test.jsonl"
INDEX_DIR = ROOT / "data" / "index"

TERMS_PER_BARREL = 1000


def read_jsonl(path):
    """Read a JSONL file one record at a time."""
    with open(path, "r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if line.strip():
                try:
                    yield json.loads(line)
                except json.JSONDecodeError as error:
                    raise ValueError(
                        f"Invalid JSON on line {line_number}: {error}"
                    )


def get_searchable_text(game):
    """Combine the text fields that should be searchable."""
    fields = [
        game.get("title", ""),
        game.get("description", ""),
        game.get("short_description", ""),
    ]

    for field in [
        "genres", "tags", "categories", "developers", "publishers"
    ]:
        value = game.get(field, [])

        if isinstance(value, list):
            fields.extend(str(item) for item in value)
        elif value:
            fields.append(str(value))

    return " ".join(str(value) for value in fields if value)


def write_barrel(barrel_dir, barrel_number, term_postings):
    """
    Write one JSONL barrel and its byte-offset table.

    Each line contains one term ID and its postings.
    Offsets are measured in bytes, not characters.
    """
    barrel_dir = Path(barrel_dir)
    barrel_dir.mkdir(parents=True, exist_ok=True)

    barrel_path = barrel_dir / f"barrel_{barrel_number}.jsonl"
    offset_path = barrel_dir / f"offsets_{barrel_number}.json"

    offsets = {}

    with open(barrel_path, "wb") as file:
        for term_id in sorted(term_postings, key=int):
            offsets[str(term_id)] = file.tell()

            record = {
                "term_id": int(term_id),
                "postings": term_postings[term_id],
            }

            line = (
                json.dumps(
                    record,
                    ensure_ascii=False,
                    separators=(",", ":"),
                ).encode("utf-8") + b"\n"
            )

            file.write(line)

    with open(offset_path, "w", encoding="utf-8") as file:
        json.dump(offsets, file, indent=4)


def build_index(data_path=DEFAULT_DATA, index_dir=INDEX_DIR):
    """Build all index files from a JSONL dataset."""

    data_path = Path(data_path)
    index_dir = Path(index_dir)

    if not data_path.exists():
        raise FileNotFoundError(f"Dataset not found: {data_path}")

    index_dir.mkdir(parents=True, exist_ok=True)

    barrel_dir = index_dir / "barrels"
    barrel_dir.mkdir(parents=True, exist_ok=True)

    # Remove old barrel and offset files.
    for pattern in [
        "barrel_*.json",
        "barrel_*.jsonl",
        "offsets_*.json",
    ]:
        for old_file in barrel_dir.glob(pattern):
            old_file.unlink()

    lexicon = {}
    inverted = defaultdict(list)
    forward_records = []
    documents = []
    document_lengths = []

    next_term_id = 1

    print(f"Reading dataset: {data_path}")

    for doc_id, game in enumerate(read_jsonl(data_path)):
        searchable_text = get_searchable_text(game)
        words = tokenize(searchable_text, remove_stopwords=True)

        term_data = defaultdict(list)

        for position, word in enumerate(words):
            if word not in lexicon:
                lexicon[word] = next_term_id
                next_term_id += 1

            term_data[word].append(position)

        forward_terms = []

        for word, positions in term_data.items():
            term_id = lexicon[word]
            frequency = len(positions)

            forward_terms.append({
                "term_id": term_id,
                "frequency": frequency,
                "positions": positions,
            })

            inverted[word].append([doc_id, frequency])

        forward_records.append({
            "doc_id": doc_id,
            "terms": forward_terms,
        })

        documents.append({
            "doc_id": doc_id,
            "game": game,
        })

        document_lengths.append(len(words))

        if (doc_id + 1) % 100 == 0:
            print(f"Indexed {doc_id + 1} games...")

    # Save lexicon.
    with open(index_dir / "lexicon.json", "w", encoding="utf-8") as file:
        json.dump(lexicon, file, ensure_ascii=False)

    # Save original game records.
    with open(index_dir / "documents.jsonl", "w", encoding="utf-8") as file:
        for record in documents:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")

    # Save forward index.
    with open(index_dir / "forward_index.jsonl", "w", encoding="utf-8") as file:
        for record in forward_records:
            file.write(json.dumps(record) + "\n")

    # Group inverted-index terms into barrels.
    barrels = defaultdict(dict)

    for word, postings in inverted.items():
        term_id = lexicon[word]
        barrel_number = (term_id - 1) // TERMS_PER_BARREL

        barrels[barrel_number][str(term_id)] = postings

    # Write each barrel and its offset table.
    for barrel_number, term_postings in barrels.items():
        write_barrel(barrel_dir, barrel_number, term_postings)

    average_length = (
        sum(document_lengths) / len(document_lengths)
        if document_lengths else 0
    )

    stats = {
        "num_docs": len(documents),
        "num_terms": len(lexicon),
        "avg_doc_len": average_length,
        "terms_per_barrel": TERMS_PER_BARREL,
        "num_barrels": len(barrels),
    }

    with open(index_dir / "stats.json", "w", encoding="utf-8") as file:
        json.dump(stats, file, indent=4)

    with open(index_dir / "doc_lengths.json", "w", encoding="utf-8") as file:
        json.dump(document_lengths, file)

    print("\nINDEX BUILD COMPLETE")
    print("--------------------")
    print(f"Documents indexed: {stats['num_docs']}")
    print(f"Unique terms:      {stats['num_terms']}")
    print(f"Average doc length: {stats['avg_doc_len']:.2f}")
    print(f"Barrels created:   {stats['num_barrels']}")
    print(f"Index location:    {index_dir}")


def main():
    parser = argparse.ArgumentParser(
        description="Build the Steam game search indexes."
    )

    parser.add_argument(
        "--data",
        type=Path,
        default=DEFAULT_DATA,
        help="Path to the input JSONL dataset.",
    )

    args = parser.parse_args()
    build_index(args.data)


if __name__ == "__main__":
    main()
