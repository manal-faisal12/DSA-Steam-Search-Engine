#This times 1-word and 5-word queries cold (caches cleared) and warm against the spec targets, and reports RAM if psutil is installed.
"""Time queries against the real index.

Run from the repo root:
    python -m backend.search.benchmark --index data/index
"""
import argparse
import statistics
import time
from pathlib import Path

from backend.indexer.index_reader import GameSearchIndex, INDEX_DIR

ONE_WORD = ["space", "farming", "zombie", "puzzle", "racing"]
FIVE_WORD = [
    "relaxing farming simulation game animals",
    "open world survival crafting game",
    "space strategy turn based combat",
    "cooperative horror survival game online",
    "pixel art roguelike dungeon crawler",
]


def run(engine, query, cold):
    if cold:
        engine.barrels.cache.clear()
        engine.barrels.offset_cache.clear()
    start = time.perf_counter()
    engine.search(query)
    return (time.perf_counter() - start) * 1000


def report(engine, label, queries, limit_ms):
    for cold in (True, False):
        times = [run(engine, q, cold) for q in queries]
        mode = "cold" if cold else "warm"
        worst = max(times)
        status = "OK" if worst < limit_ms else "TOO SLOW"
        print(f"{label:10s} {mode}: median {statistics.median(times):7.1f} ms | "
              f"max {worst:7.1f} ms | target < {limit_ms} ms  {status}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--index", type=Path, default=INDEX_DIR)
    args = parser.parse_args()

    start = time.perf_counter()
    engine = GameSearchIndex(args.index)
    print(f"Index load: {time.perf_counter() - start:.1f} s "
          f"({engine.stats['num_docs']:,} docs)")

    report(engine, "1-word", ONE_WORD, 500)
    report(engine, "5-word", FIVE_WORD, 1500)

    try:
        import psutil
        rss = psutil.Process().memory_info().rss / 1024 ** 3
        print(f"RAM (RSS): {rss:.2f} GB | target <= 2 GB")
    except ImportError:
        print("pip install psutil to also measure RAM")


if __name__ == "__main__":
    main()