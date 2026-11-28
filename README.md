# Steam Games Search Engine

CS-250 Data Structures & Algorithms semester project (BESE-2025, NUST SEECS, Prof. Dr. Faisal Shafait).
A search engine over 45,000+ Steam games with its own indexing and ranking code, autocomplete,
filters, and live addition of new games. No database is used: the index is plain files.

**Team:** Muhammad Talal Aqdas (frontend, API, autocomplete, deployment) ·
Manal Faisal (BM25 ranking, multi-word and semantic search) ·
Fatima Zahra Mustapha (indexing, barrels, dynamic content).

## How it works

```
games.jsonl ──► tokenizer ──► lexicon + forward index + inverted index (barrels, byte-offset tables)
                                              │
 browser ◄─ React UI ◄─ FastAPI ◄─ BM25 ranker reads only the barrels a query needs
                          │
                          └─ autocomplete trie (top-5 suggestions stored at every node)
```

| Part | Location | What it does |
|---|---|---|
| Data scripts | `backend/indexer/download_data.py`, `clean_data.py` | Download the dataset, keep English games with descriptions, strip HTML, write JSONL |
| Tokenizer | `backend/tokenizer/` | Lowercase, split into words; shared by indexing and queries |
| Indexer | `backend/indexer/index_builder.py` | Lexicon, forward index, inverted index split into barrels with offset tables |
| Dynamic indexer | `backend/indexer/dynamic_indexer.py` | Adds a new game to the existing files |
| Ranking | `backend/search/bm25.py` | Own Okapi BM25 (k1 = 1.2, b = 0.75), all query words must match (AND), rarest word first |
| Semantic search | `backend/search/glove.py` | GloVe query expansion (no LLMs or transformer models) |
| Autocomplete | `backend/search/trie.py` | Compressed trie; typed prefix is walked once and the top-5 answer is read from the node |
| API | `backend/app/` | FastAPI: `/search`, `/suggest`, `/games`, `/health` |
| UI | `frontend/` | React + Vite: search box with suggestions, filters, pagination, add-games page |

### Autocomplete
Titles (and each later word of a title), tags and genres go into a radix trie. Every node keeps its five best
entries (games ranked by review count, tags by how many games use them), so a lookup costs the length of the
prefix and does not depend on how many titles share it. Typical lookup time is well under 1 ms (limit: 100 ms).

### Adding new content
`POST /games` accepts one or more games (manual form, JSON file, or text file in the UI). A single background
writer thread adds them with the dynamic indexer, then loads a fresh index and trie and swaps them in with
one assignment. Searches keep running on the old index until the swap, so they are never blocked.
Progress is available at `GET /games/jobs/{job_id}`.

## Run it locally

Requires Python 3.11+ and Node 20+.

```bash
pip install -r requirements.txt

# 1. Build the index (the repo ships a 1,000-game test file)
python -m backend.indexer.index_builder                # uses data/test/games_test.jsonl
# for the full dataset:
#   pip install -r requirements-data.txt
#   python backend/indexer/download_data.py
#   python backend/indexer/clean_data.py
#   python -m backend.indexer.index_builder --data data/processed/games.jsonl

# 2. Start the API (http://localhost:8000, docs at /docs)
uvicorn backend.app.main:app --reload

# 3. Start the UI (http://localhost:5173)
cd frontend && npm install && npm run dev
```

Run the tests with `python -m pytest`. Check speed and memory with `python -m backend.search.benchmark`.

### Configuration

| Variable | Where | Default | Meaning |
|---|---|---|---|
| `STEAM_INDEX_DIR` | backend | `data/index` | Folder holding the index files |
| `CORS_ORIGINS` | backend | `http://localhost:5173,http://127.0.0.1:5173` | Comma-separated frontend addresses allowed to call the API |
| `VITE_API_BASE_URL` | frontend | `http://localhost:8000` | Address of the API |

## API

| Request | Result |
|---|---|
| `GET /search?query=space strategy&limit=10&offset=0` | Ranked games, `total` matches, `took_ms` |
| `...&genre=Strategy&min_price=0&max_price=10&year_from=2015&year_to=2024` | Same search with filters |
| `GET /suggest?q=star` | Up to 5 suggestions, each marked `game` or `tag` |
| `POST /games` with `{"games":[{"title":"…","description":"…"}]}` | `202` and a job id |
| `GET /games/jobs/{id}` | `queued`, `running`, `done` or `error` |
| `GET /health` | `{"status":"ok","index_loaded":true}` |

## Deployment

The frontend and backend are deployed separately because the backend keeps the index in files and memory.

**Backend (Docker, e.g. Render, Railway or a VM).** The `Dockerfile` builds the index while the image is built.
By default it uses the 1,000-game test file; to publish a bigger subset, commit it (for example
`data/deploy/games.jsonl`), copy it into the image and build with `--build-arg DEPLOY_DATA=data/deploy/games.jsonl`.
Free hosts have little memory (Render free: 512 MB), so deploy a subset there and show the full dataset locally.
Set `CORS_ORIGINS` to the frontend's public address. New games added on a host with an ephemeral disk are lost on restart.

**Frontend (Vercel).** Import the repo, set the root directory to `frontend`, and add the environment variable
`VITE_API_BASE_URL` with the backend's public address.

## Data and credits

Game data: [Steam Games Dataset by Fronkon Games](https://huggingface.co/datasets/FronkonGames/steam-games-dataset),
licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), collected from the
[Steam Store API](https://store.steampowered.com/) and [SteamSpy](https://steamspy.com/).
Word vectors: [GloVe 6B](https://nlp.stanford.edu/projects/glove/) (Stanford, public domain licence).
This project is not affiliated with Valve or Steam.
