import json
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.main import create_app


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.catalogue = Path(self.directory.name) / "games.jsonl"
        self.catalogue.write_text(json.dumps({
            "id": "1", "title": "Space Tactics", "description": "A strategy game.",
            "short_description": "Tactical space combat", "release_year": 2025,
            "price": 9.99, "genres": ["Strategy"], "tags": ["Space"],
            "categories": [], "popularity": 50, "title_tokens": ["space", "tactics"],
            "tag_tokens": ["space"],
        }) + "\n", encoding="utf-8")
        self.client = TestClient(create_app(self.catalogue))

    def tearDown(self):
        self.directory.cleanup()

    def test_health_reports_ready_before_catalogue_is_loaded(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok", "catalogue_loaded": False})

    def test_search_returns_contract_with_catalogue_match(self):
        response = self.client.get("/search", params={"query": "space"})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["engine"], "temporary_catalogue_match")
        self.assertEqual(payload["results"][0]["title"], "Space Tactics")

    def test_search_rejects_blank_query(self):
        response = self.client.get("/search", params={"query": ""})
        self.assertEqual(response.status_code, 422)
