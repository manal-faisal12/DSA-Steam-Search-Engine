
import json

from backend.indexer.index_reader import GameSearchIndex


def test_index_files_exist(base_index_dir):
    assert (base_index_dir / "lexicon.json").exists()
    assert (base_index_dir / "forward_index.jsonl").exists()
    assert (base_index_dir / "documents.jsonl").exists()
    assert (base_index_dir / "stats.json").exists()
    assert (base_index_dir / "barrels").is_dir()


def test_lexicon_ids_are_unique(base_index_dir):
    lexicon = json.loads(
        (base_index_dir / "lexicon.json").read_text(encoding="utf-8")
    )
    assert len(lexicon) > 0
    assert len(set(lexicon.values())) == len(lexicon)


def test_forward_index_document_count(base_index_dir):
    with open(
        base_index_dir / "forward_index.jsonl",
        encoding="utf-8"
    ) as file:
        records = [json.loads(line) for line in file if line.strip()]

    stats = json.loads(
        (base_index_dir / "stats.json").read_text(encoding="utf-8")
    )
    assert len(records) == stats["num_docs"]


def test_barrel_count(base_index_dir):
    stats = json.loads(
        (base_index_dir / "stats.json").read_text(encoding="utf-8")
    )
    barrel_files = list(
        (base_index_dir / "barrels").glob("barrel_*.json")
    )
    assert len(barrel_files) == stats["num_barrels"]


def test_search_xoxo_game(base_index_dir):
    engine = GameSearchIndex(index_dir=base_index_dir)
    results = engine.search("XOXO Blood Droplets")
    assert len(results) > 0
    assert results[0]["id"] == "780820"


def test_search_guardians_game(base_index_dir):
    engine = GameSearchIndex(index_dir=base_index_dir)
    results = engine.search("Guardians Orion")
    assert len(results) > 0
    assert results[0]["id"] == "407840"


def test_search_multiple_words(base_index_dir):
    engine = GameSearchIndex(index_dir=base_index_dir)
    results = engine.search("dinosaurs robots")
    assert len(results) > 0
    for result in results:
        assert result["id"]


def test_unknown_word(base_index_dir):
    engine = GameSearchIndex(index_dir=base_index_dir)
    results = engine.search("zzzzunknownword123")
    assert results == []


def test_empty_query(base_index_dir):
    engine = GameSearchIndex(index_dir=base_index_dir)
    results = engine.search("")
    assert results == []
