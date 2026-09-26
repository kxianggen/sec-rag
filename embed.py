"""Stage 4: turn every chunk into a vector with a local embedding model.

Reads  data/chunks.jsonl
Writes data/embeddings.npy   (one row per chunk, same order as chunks.jsonl)

Runs on your laptop, no API key, no cost. First run downloads the model (~90 MB).
"""

import json
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

CHUNKS = Path("data/chunks.jsonl")
OUT = Path("data/embeddings.npy")
MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def main():
    chunks = [json.loads(line) for line in CHUNKS.open(encoding="utf-8")]
    model = SentenceTransformer(MODEL)
    vectors = model.encode(
        [c["text"] for c in chunks],
        batch_size=64,
        show_progress_bar=True,
        normalize_embeddings=True,
    )
    np.save(OUT, vectors)
    print(f"{vectors.shape[0]:,} vectors of size {vectors.shape[1]} written to {OUT}")


if __name__ == "__main__":
    main()
