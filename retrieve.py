"""Stage 5: find the chunks most similar to a question.

Loads data/chunks.jsonl and data/embeddings.npy, embeds the question with the
same model, and returns the top-k chunks by cosine similarity.

Plain numpy, no vector database, no framework. See TICKETS.md.
"""

import json
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

CHUNKS = Path("data/chunks.jsonl")
VECTORS = Path("data/embeddings.npy")
MODEL = "sentence-transformers/all-MiniLM-L6-v2"

_model = None
_chunks = None
_vectors = None


def _load():
    global _model, _chunks, _vectors
    if _model is None:
        _model = SentenceTransformer(MODEL)
        _chunks = [json.loads(line) for line in CHUNKS.open(encoding="utf-8")]
        _vectors = np.load(VECTORS)


def retrieve(question: str, k: int = 5) -> list[dict]:
    _load()
    q = _model.encode([question], normalize_embeddings=True)[0]
    scores = _vectors @ q                     # cosine similarity: vectors are normalised
    top = np.argsort(scores)[::-1][:k]
    return [{**_chunks[i], "score": float(scores[i])} for i in top]


if __name__ == "__main__":
    import sys
    question = " ".join(sys.argv[1:]) or "What are the risks from export controls?"
    for r in retrieve(question):
        print(f"{r['score']:.3f}  {r['ticker']} {r['period_end']} Item {r['item']}")
        print("   ", r["text"][:200].replace("\n", " "), "\n")
