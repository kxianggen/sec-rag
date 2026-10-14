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
_latest = None      # {ticker: newest fiscal_year in the corpus}, built in _load()


def set_index(name: str) -> None:
    """Switch to another chunk/vector index, e.g. "fixed" -> data/chunks_fixed.jsonl +
    data/embeddings_fixed.npy. "main" is the default index. Used by Experiment 1."""
    global CHUNKS, VECTORS, _model
    if name == "main":
        CHUNKS, VECTORS = Path("data/chunks.jsonl"), Path("data/embeddings.npy")
    else:
        CHUNKS, VECTORS = Path(f"data/chunks_{name}.jsonl"), Path(f"data/embeddings_{name}.npy")
    _model = None          # forces _load() to read the new files


def _load():
    global _model, _chunks, _vectors, _latest
    if _model is None:
        _model = SentenceTransformer(MODEL)
        _chunks = [json.loads(line) for line in CHUNKS.open(encoding="utf-8")]
        _vectors = np.load(VECTORS)
        _latest = {}
        for c in _chunks:
            if c["ticker"] not in _latest or c["fiscal_year"] > _latest[c["ticker"]]:
                _latest[c["ticker"]] = c["fiscal_year"]


def retrieve(question: str, k: int = 5, ticker: str | None = None, fiscal_years: list[int] | None = None,
             latest_only: bool = False) -> list[dict]:
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
        if latest_only and _chunks[i]["fiscal_year"] != _latest[_chunks[i]["ticker"]]:
            continue
        results.append({**_chunks[i], "score": float(scores[i])})
        if len(results) == k:
            break
    return results

def retrieve_multi(question: str, k: int = 5, tickers: list[str] | None = None,
                   fiscal_years: list[int] | None = None, latest: bool = False) -> list[dict]:
    # "latest" only applies when the question names no explicit year: years win.
    latest_only = latest and not fiscal_years
    if not tickers:
        return retrieve(question, k, ticker=None, fiscal_years=fiscal_years, latest_only=latest_only)
    if len(tickers) == 1:
        return retrieve(question, k, ticker=tickers[0], fiscal_years=fiscal_years, latest_only=latest_only)
    else:
        per_company = max(1, k//len(tickers))
        results = []
        for t in tickers:
            results.extend(retrieve(question, ticker=t, k=per_company, fiscal_years=fiscal_years,
                                    latest_only=latest_only))
    return results


if __name__ == "__main__":
    import sys
    question = " ".join(sys.argv[1:]) or "What are the risks from export controls?"
    for r in retrieve(question):
        print(f"{r['score']:.3f}  {r['ticker']} {r['period_end']} Item {r['item']}")
        print("   ", r["text"][:200].replace("\n", " "), "\n")
