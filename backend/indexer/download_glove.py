"""
Downloads GloVe 6B and keeps only the 100-d file: data/glove/glove.6B.100d.txt

    python -m backend.indexer.download_glove   (run from the repo root)

The zip is ~822 MB; the extracted 100d file is ~350 MB. Do NOT commit it (see .gitignore).
"""
import os
import sys
from pathlib import Path
import urllib.request
import zipfile

URLS = [
    "https://nlp.stanford.edu/data/glove.6B.zip",
    "https://downloads.cs.stanford.edu/nlp/data/glove.6B.zip", """Honestly have no clue why we are using stanford data need to check later wth this is"""
]
REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = str(REPO_ROOT / "data" / "glove")
TARGET = "glove.6B.100d.txt"


def _progress(blocks, block_size, total):
    if total > 0:
        pct = min(100, blocks * block_size * 100 // total)
        sys.stdout.write(f"\rDownloading... {pct}%")
        sys.stdout.flush()


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    target_path = os.path.join(OUT_DIR, TARGET)
    if os.path.exists(target_path):
        print(f"{target_path} already exists, nothing to do.")
        return

    zip_path = os.path.join(OUT_DIR, "glove.6B.zip")
    for url in URLS:
        try:
            print(f"Trying {url}")
            urllib.request.urlretrieve(url, zip_path, _progress)
            print()
            break
        except Exception as e:  # noqa: BLE001
            print(f"\nFailed: {e}")
    else:
        sys.exit("All mirrors failed. Download glove.6B.zip manually and put glove.6B.100d.txt in data/glove/ (repo root)")

    with zipfile.ZipFile(zip_path) as z:
        z.extract(TARGET, OUT_DIR)
    os.remove(zip_path)
    print(f"Done: {target_path}")


if __name__ == "__main__":
    main()