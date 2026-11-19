
import json
import shutil
from pathlib import Path

import pytest

from backend.indexer.dynamic_indexer import DynamicIndexer
from backend.indexer.index_reader import GameSearchIndex





def create_test_game():
    """Return a sample game for dynamic indexing tests."""
    return {
        "id": "test-dynamic-123",
        "title": "Nebula Crystal Adventure",
        "description": (
            "Explore mysterious galaxies, discover glowing crystals, "
            "and defeat powerful space creatures."
        ),
        "short_description": (
            "A space adventure about discovering rare crystals."
        ),
        "genres": ["Adventure", "Indie"],
        "tags": ["Space", "Exploration"],
        "categories": ["Single-player"],
        "developers": ["Test Developer"],
        "publishers": ["Test Publisher"],
        "price": 5.99
    }


def test_add_game_updates_index_and_search(temporary_index):
    indexer = DynamicIndexer(index_dir=temporary_index)

    with open(temporary_index / "stats.json", encoding="utf-8") as file:
        old_stats = json.load(file)

    old_count = old_stats["num_docs"]

    new_doc_id = indexer.add_game(create_test_game())

    assert new_doc_id == old_count

    with open(temporary_index / "stats.json", encoding="utf-8") as file:
        new_stats = json.load(file)

    assert new_stats["num_docs"] == old_count + 1

    search_engine = GameSearchIndex(index_dir=temporary_index)
    results = search_engine.search("nebula crystals")

    assert len(results) > 0
    assert results[0]["title"] == "Nebula Crystal Adventure"


def test_duplicate_game_is_rejected(temporary_index):
    indexer = DynamicIndexer(index_dir=temporary_index)

    game = create_test_game()

    indexer.add_game(game)

    with pytest.raises(ValueError):
        indexer.add_game(game)


def test_json_file_with_utf8_bom(temporary_index, tmp_path):
    indexer = DynamicIndexer(index_dir=temporary_index)

    game = create_test_game()
    game["id"] = "test-bom-456"
    game["title"] = "BOM Testing Galaxy"

    json_file = tmp_path / "bom_game.json"

    json_file.write_text(
        json.dumps(game),
        encoding="utf-8-sig"
    )

    new_doc_id = indexer.add_json_file(json_file)

    assert isinstance(new_doc_id, int)

    search_engine = GameSearchIndex(index_dir=temporary_index)
    results = search_engine.search("BOM Testing Galaxy")

    assert len(results) > 0
    assert results[0]["title"] == "BOM Testing Galaxy"
