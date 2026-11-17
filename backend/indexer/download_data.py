from huggingface_hub import snapshot_download

path = snapshot_download(
    repo_id="FronkonGames/steam-games-dataset",
    repo_type="dataset",
    local_dir="data/raw",
    allow_patterns=["*.parquet", "README.md"],
)
print("Downloaded to:", path)
