import json

import pytest
from fastapi.testclient import TestClient

from backend.app.main import create_app
from backend.indexer.index_builder import build_index

GAMES = [
    {"id": "1", "title": "Space Tactics", "description": "Turn based space strategy with fleets and planets.",
     "short_description": "Tactical space combat", "release_year": 2021, "price": 9.99,
     "genres": ["Strategy"], "tags": ["Space"], "categories": [], "positive": 50, "negative": 5},
    {"id": "2", "title": "Farm Valley", "description": "Relaxing farming simulation with animals and crops.",
     "short_description": "Grow crops", "release_year": 2023, "price": 0.0,
     "genres": ["Simulation", "Casual"], "tags": ["Farming"], "categories": [], "positive": 900, "negative": 10},
    {"id": "3", "title": "Space Farm", "description": "Run a farm on a distant planet in space.",
     "short_description": "Farm among the stars", "release_year": 2019, "price": 19.5,
     "genres": ["Simulation"], "tags": ["Space", "Farming"], "categories": [], "positive": 10, "negative": 1},
]


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    root = tmp_path_factory.mktemp("api")
    data = root / "games.jsonl"
    data.write_text("\n".join(json.dumps(game) for game in GAMES), encoding="utf-8")
    index_dir = root / "index"
    build_index(data_path=data, index_dir=index_dir)
    return TestClient(create_app(index_dir))


def titles(response):
    return [row["title"] for row in response.json()["results"]]


def test_health_reports_ready_before_index_is_loaded(tmp_path):
    response = TestClient(create_app(tmp_path / "missing")).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "index_loaded": False}


def test_search_returns_503_when_index_is_missing(tmp_path):
    response = TestClient(create_app(tmp_path / "missing")).get("/search", params={"query": "space"})
    assert response.status_code == 503


def test_search_uses_bm25_over_the_index(client):
    response = client.get("/search", params={"query": "space"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["engine"] == "bm25_barrels"
    assert payload["total"] == 2
    assert set(titles(response)) == {"Space Tactics", "Space Farm"}
    assert payload["results"][0]["score"] >= payload["results"][1]["score"]


def test_multi_word_query_requires_every_word(client):
    response = client.get("/search", params={"query": "space farm"})
    assert titles(response) == ["Space Farm"]


def test_stopword_only_query_returns_nothing(client):
    response = client.get("/search", params={"query": "the"})
    assert response.status_code == 200
    assert response.json()["total"] == 0


def test_search_rejects_blank_query(client):
    assert client.get("/search", params={"query": ""}).status_code == 422


def test_genre_filter_is_case_insensitive(client):
    response = client.get("/search", params={"query": "farm", "genre": "simulation"})
    assert set(titles(response)) == {"Farm Valley", "Space Farm"}
    response = client.get("/search", params={"query": "farm", "genre": "Casual"})
    assert titles(response) == ["Farm Valley"]


def test_price_filter(client):
    response = client.get("/search", params={"query": "farm", "max_price": 0})
    assert titles(response) == ["Farm Valley"]
    response = client.get("/search", params={"query": "farm", "min_price": 10})
    assert titles(response) == ["Space Farm"]


def test_year_filter(client):
    response = client.get("/search", params={"query": "farm", "year_from": 2020})
    assert titles(response) == ["Farm Valley"]
    response = client.get("/search", params={"query": "farm", "year_to": 2019})
    assert titles(response) == ["Space Farm"]


def test_pagination_keeps_total_and_slices_results(client):
    first = client.get("/search", params={"query": "farm", "limit": 1, "offset": 0}).json()
    second = client.get("/search", params={"query": "farm", "limit": 1, "offset": 1}).json()
    assert first["total"] == second["total"] == 2
    assert len(first["results"]) == len(second["results"]) == 1
    assert first["results"][0]["id"] != second["results"][0]["id"]
    beyond = client.get("/search", params={"query": "farm", "offset": 5}).json()
    assert beyond["results"] == [] and beyond["total"] == 2


def test_cors_allows_configured_origin(client):
    response = client.get("/health", headers={"Origin": "http://localhost:5173"})
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
