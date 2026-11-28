"""Stream cleaned Steam JSONL into a stable search-document format.

The parser is intentionally independent of the later forward/inverted-index
implementation.  It gives every teammate one validated input contract while
keeping memory use bounded for the 80,000-game dataset.
"""

from __future__ import annotations
import argparse
import json
import math
from collections.abc import Iterator
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from backend.tokenizer import normalize_text, unique_tokens


@dataclass(frozen=True)
class SearchDocument:
    id: str
    title: str
    description: str
    short_description: str
    release_year: int | None
    price: float
    genres: list[str]
    tags: list[str]
    categories: list[str]
    popularity: int
    title_tokens: list[str]
    tag_tokens: list[str]


def _as_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def parse_record(record: dict[str, Any]) -> SearchDocument:
    """Validate one cleaned source record and select fields needed by search."""
    game_id = str(record.get("id", "")).strip()
    title = str(record.get("title", "")).strip()
    description = str(record.get("description", "")).strip()
    if not game_id:
        raise ValueError("record is missing id")
    if not title:
        raise ValueError(f"record {game_id} is missing title")
    if not description:
        raise ValueError(f"record {game_id} is missing description")

    release_year = record.get("release_year")
    if not isinstance(release_year, int):
        release_year = None
    price = record.get("price", 0.0)
    try:
        price = float(price)
    except (TypeError, ValueError):
        price = 0.0
    if not math.isfinite(price):
        price = 0.0

    tags = _as_string_list(record.get("tags"))

    if "popularity" in record:
        popularity = int(record["popularity"] or 0)
    else:
        popularity = int(record.get("positive", 0) or 0) + int(record.get("negative", 0) or 0)
        
    return SearchDocument(
        id=game_id,
        title=title,
        description=description,
        short_description=str(record.get("short_description", "")).strip(),
        release_year=release_year,
        price=max(price, 0.0),
        genres=_as_string_list(record.get("genres")),
        tags=tags,
        categories=_as_string_list(record.get("categories")),
        popularity=popularity,
        title_tokens=unique_tokens([title]),
        tag_tokens=unique_tokens(tags),
    )


def iter_documents(source: Path) -> Iterator[SearchDocument]:
    """Yield validated documents from JSONL without loading the corpus at once."""
    with source.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSON on line {line_number}") from exc
            if not isinstance(record, dict):
                raise ValueError(f"record on line {line_number} is not an object")
            try:
                yield parse_record(record)
            except ValueError as exc:
                raise ValueError(f"invalid record on line {line_number}: {exc}") from exc


def build_catalogue(source: Path, destination: Path) -> int:
    """Write the parsed corpus as JSONL and return its document count."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with destination.open("w", encoding="utf-8") as output:
        for document in iter_documents(source):
            output.write(json.dumps(asdict(document), ensure_ascii=False) + "\n")
            count += 1
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse cleaned Steam games into search documents.")
    parser.add_argument("--source", type=Path, default=Path("data/processed/games.jsonl"))
    parser.add_argument("--output", type=Path, default=Path("index/catalogue/games.jsonl"))
    args = parser.parse_args()
    count = build_catalogue(args.source, args.output)
    print(f"Wrote {count:,} validated game documents to {args.output}")


if __name__ == "__main__":
    main()
