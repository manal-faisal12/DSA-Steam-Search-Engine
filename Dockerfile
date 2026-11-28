# Backend image: FastAPI + the file-based search index.
# The index is built while the image is built, from the games file in DEPLOY_DATA.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend ./backend
COPY data/test ./data/test

# Use a bigger subset by passing --build-arg DEPLOY_DATA=data/deploy/games.jsonl
# (and COPY that folder in as well).
ARG DEPLOY_DATA=data/test/games_test.jsonl
RUN python -m backend.indexer.index_builder --data "$DEPLOY_DATA"

# Set CORS_ORIGINS to the public address of the frontend, e.g. https://my-app.vercel.app
ENV STEAM_INDEX_DIR=data/index
EXPOSE 8000
CMD ["sh", "-c", "uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
