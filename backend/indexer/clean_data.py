import glob, html, json, random, re
import pyarrow.parquet as pq

SRC = glob.glob("data/raw/**/*.parquet", recursive=True)[0]
OUT = "data/processed/games.jsonl"
TEST = "data/test/games_test.jsonl"
MAX_GAMES = 80000
MIN_DESC_WORDS = 30

COLS = ["appID", "name", "release_date", "estimated_owners", "peak_ccu", "price",
        "detailed_description", "short_description", "supported_languages",
        "positive", "negative", "recommendations", "metacritic_score",
        "developers", "publishers", "categories", "genres", "tags", "header_image"]

TAG_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"\s+")
YEAR_RE = re.compile(r"(19|20)\d{2}")


def clean_html(text):
    if not text:
        return ""
    text = TAG_RE.sub(" ", text)
    text = html.unescape(text)
    text = WS_RE.sub(" ", text).strip()
    if text.lower().startswith("about this game"):
        text = text[len("about this game"):].strip()
    return text


def as_list(v):
    if v is None:
        return []
    if isinstance(v, dict):
        return list(v.keys())
    return [str(x) for x in v]


def pop(r):
    return (r["positive"] or 0) + (r["negative"] or 0)


rows = pq.read_table(SRC, columns=COLS).to_pylist()
print("1. Loaded:", len(rows))

rows = [r for r in rows if "English" in as_list(r["supported_languages"])]
print("2. After English-only:", len(rows))

records = []
for r in rows:
    name = (r["name"] or "").strip()
    desc = clean_html(r["detailed_description"]) or clean_html(r["short_description"])
    if not name or len(desc.split()) < MIN_DESC_WORDS:
        continue
    m = YEAR_RE.search(r["release_date"] or "")
    records.append({
        "id": str(r["appID"]),
        "title": name,
        "description": desc,
        "short_description": clean_html(r["short_description"]),
        "release_date": r["release_date"] or "",
        "release_year": int(m.group(0)) if m else None,
        "price": r["price"] or 0.0,
        "genres": as_list(r["genres"]),
        "tags": as_list(r["tags"]),
        "categories": as_list(r["categories"]),
        "developers": as_list(r["developers"]),
        "publishers": as_list(r["publishers"]),
        "positive": r["positive"] or 0,
        "negative": r["negative"] or 0,
        "recommendations": r["recommendations"] or 0,
        "peak_ccu": r["peak_ccu"] or 0,
        "estimated_owners": r["estimated_owners"] or "",
        "metacritic_score": r["metacritic_score"] or 0,
        "header_image": r["header_image"] or "",
    })
print("3. After non-empty description (>= %d words):" % MIN_DESC_WORDS, len(records))

records.sort(key=pop, reverse=True)
seen_ids, seen_names, deduped = set(), set(), []
for rec in records:
    key = re.sub(r"\W+", "", rec["title"].lower())
    if rec["id"] in seen_ids or key in seen_names:
        continue
    seen_ids.add(rec["id"])
    seen_names.add(key)
    deduped.append(rec)
print("4. After dedupe:", len(deduped))

final = deduped[:MAX_GAMES]
print("5. Final kept (most-reviewed first, cap %d):" % MAX_GAMES, len(final))

with open(OUT, "w", encoding="utf-8") as f:
    for rec in final:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

test = random.Random(42).sample(final, 1000)
with open(TEST, "w", encoding="utf-8") as f:
    for rec in test:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

words = sorted(len(r["description"].split()) for r in final)
print("Median description words:", words[len(words) // 2])
print("Wrote", OUT, "and", TEST)
