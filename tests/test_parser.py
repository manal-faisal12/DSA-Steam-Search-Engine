import json
import tempfile
import unittest
from pathlib import Path

from backend.indexer.parser import build_catalogue, iter_documents, parse_record


class ParserTests(unittest.TestCase):
    def test_parse_record_selects_search_fields(self):
        document = parse_record({
            "id": 7,
            "title": "Galaxy Tactics",
            "description": "Command a tactical fleet in deep space.",
            "short_description": "Fleet tactics",
            "release_year": 2024,
            "price": "19.99",
            "genres": ["Strategy"],
            "tags": ["Space", "Turn-Based"],
            "categories": ["Single-player"],
            "positive": 15,
            "negative": 2,
        })
        self.assertEqual(document.id, "7")
        self.assertEqual(document.title_tokens, ["galaxy", "tactics"])
        self.assertEqual(document.tag_tokens, ["space", "turn", "based"])
        self.assertEqual(document.popularity, 17)

    def test_parser_rejects_missing_description(self):
        with self.assertRaisesRegex(ValueError, "missing description"):
            parse_record({"id": "1", "title": "Missing text"})

    def test_build_catalogue_streams_jsonl(self):
        first = {"id": "1", "title": "Alpha", "description": "A complete description."}
        second = {"id": "2", "title": "Beta", "description": "Another complete description."}
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.jsonl"
            output = Path(directory) / "catalogue" / "games.jsonl"
            source.write_text("\n".join(json.dumps(row) for row in [first, second]) + "\n", encoding="utf-8")
            self.assertEqual(build_catalogue(source, output), 2)
            self.assertEqual([document.id for document in iter_documents(output)], ["1", "2"])
