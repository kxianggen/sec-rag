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


def retrieve(question: str, k: int = 5, ticker: str | None = None, fiscal_years: list[int] | None = None) -> list[dict]:
    _load()
    q = _model.encode([question], normalize_embeddings=True)[0]
    scores = _vectors @ q                     # cosine similarity: vectors are normalised
    top = np.argsort(scores)[::-1]
    results = []
    for i in top:
        if ticker and _chunks[i]["ticker"] != ticker:
            continue
        if fiscal_years and _chunks[i]["fiscal_year"] not in fiscal_years:
            continue
        results.append({**_chunks[i], "score": float(scores[i])})
        if len(results) == k:
            break
    return results

def retrieve_multi(question: str, k: int = 5, tickers: list[str] | None = None, fiscal_years: list[int] | None = None)-> list[dict]:
    if not tickers:
        return retrieve(question, k, ticker=None, fiscal_years=fiscal_years)
    if len(tickers) == 1:
        return retrieve(question, k, ticker=tickers[0], fiscal_years=fiscal_years)
    else:
        per_company = max(1, k//len(tickers))
        results = []
        for t in tickers:
            results.extend(retrieve(question, ticker=t, k=per_company, fiscal_years=fiscal_years))
    return results


if __name__ == "__main__":
    import sys
    question = " ".join(sys.argv[1:]) or "What are the risks from export controls?"
    for r in retrieve(question):
        print(f"{r['score']:.3f}  {r['ticker']} {r['period_end']} Item {r['item']}")
        print("   ", r["text"][:200].replace("\n", " "), "\n")
