import random
import string
import time

from backend.search.trie import AutocompleteTrie, build_trie, normalize

GAMES = [
    {"title": "Stardew Valley", "positive": 900, "negative": 10, "tags": ["Farming Sim", "Pixel Graphics"], "genres": ["Simulation"]},
    {"title": "Star Wars: Battlefront", "positive": 100, "negative": 20, "tags": ["Shooter"], "genres": ["Action"]},
    {"title": "Starbound", "positive": 400, "negative": 40, "tags": ["Pixel Graphics"], "genres": ["Adventure"]},
    {"title": "Stars in Shadow", "positive": 5, "negative": 1, "tags": [], "genres": ["Strategy"]},
    {"title": "Café Owner", "positive": 3, "negative": 0, "tags": [], "genres": []},
]


def texts(rows):
    return [row["text"] for row in rows]


def test_prefix_returns_most_popular_first():
    trie = build_trie(GAMES)
    assert texts(trie.suggest("star"))[:3] == ["Stardew Valley", "Starbound", "Star Wars: Battlefront"]


def test_returns_at_most_five_suggestions():
    trie = build_trie([{"title": f"Alpha {i}", "positive": i} for i in range(50)])
    assert len(trie.suggest("alpha")) == 5


def test_matching_is_case_and_accent_insensitive():
    trie = build_trie(GAMES)
    assert texts(trie.suggest("CAFE")) == ["Café Owner"]
    assert texts(trie.suggest("  sTaRd ")) == ["Stardew Valley"]


def test_prefix_ending_inside_an_edge_still_matches():
    trie = build_trie(GAMES)
    assert texts(trie.suggest("stardew v")) == ["Stardew Valley"]


def test_later_words_of_a_title_are_searchable():
    trie = build_trie(GAMES)
    assert "Stardew Valley" in texts(trie.suggest("val"))
    assert texts(trie.suggest("shadow")) == ["Stars in Shadow"]


def test_stopword_word_starts_are_skipped():
    trie = build_trie(GAMES)
    assert trie.suggest("in shadow") == []


def test_tags_and_genres_are_suggested_with_their_kind():
    trie = build_trie(GAMES)
    rows = trie.suggest("pixel")
    assert rows == [{"text": "Pixel Graphics", "kind": "tag"}]
    assert trie.suggest("strat")[0] == {"text": "Strategy", "kind": "tag"}


def test_an_entry_is_listed_once_even_if_two_keys_match():
    trie = AutocompleteTrie()
    trie.add_entry("Star Star Wars", "game", 5.0, word_starts=True)
    assert texts(trie.suggest("star")) == ["Star Star Wars"]


def test_unknown_or_blank_prefix_returns_nothing():
    trie = build_trie(GAMES)
    assert trie.suggest("zzzz") == []
    assert trie.suggest("   ") == []


def test_limit_argument_caps_results():
    trie = build_trie(GAMES)
    assert len(trie.suggest("star", limit=2)) == 2


def test_normalize():
    assert normalize("  Pokémon   Red ") == "pokemon red"


def test_lookup_is_fast_at_full_dataset_scale():
    rng = random.Random(1)
    words = ["".join(rng.choice(string.ascii_lowercase) for _ in range(rng.randint(3, 9))) for _ in range(6000)]
    games = [
        {"title": " ".join(rng.choice(words) for _ in range(rng.randint(1, 5))).title(),
         "positive": rng.randint(0, 100000), "tags": [rng.choice(words)]}
        for _ in range(80000)
    ]
    trie = build_trie(games)
    prefixes = [normalize(g["title"])[:n] for g in rng.sample(games, 200) for n in (1, 2, 3, 5)]
    started = time.perf_counter()
    for prefix in prefixes:
        trie.suggest(prefix)
    average_ms = (time.perf_counter() - started) * 1000 / len(prefixes)
    assert average_ms < 5, f"average lookup {average_ms:.3f} ms"
