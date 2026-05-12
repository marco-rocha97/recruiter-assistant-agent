"""
Chroma read-only loader.

Opens the PersistentClient once at startup (singleton pattern) and returns the
candidates collection for semantic search queries. Never writes to the index at
runtime — all indexing happens at build time via scripts/prepare_dataset.py.

DATA_DIR defaults to the repo-root data/ folder for local dev; the Docker image
overrides it with ENV DATA_DIR=/app/data.
"""

import os
from pathlib import Path

import chromadb

DATA_DIR = Path(os.getenv("DATA_DIR", str(Path(__file__).resolve().parents[4] / "data")))
CHROMA_DIR = DATA_DIR / "chroma"
POOL_DIR = DATA_DIR / "pool"

_collection: chromadb.Collection | None = None


def get_collection() -> chromadb.Collection:
    """Return the singleton Chroma candidates collection (read-only at runtime)."""
    global _collection
    if _collection is None:
        client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        _collection = client.get_collection("candidates")
    return _collection
