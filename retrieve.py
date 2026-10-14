"""Stage 5: find the chunks most similar to a question.

Loads data/chunks.jsonl and data/embeddings.npy, embeds the question with the
same model, and returns the top-k chunks by cosine similarity.

Plain numpy, no vector database, no framework. See TICKETS.md.

Two optional switches (Experiment 3):
  mode="hybrid"      blend the embedding ranking with a BM25 keyword ranking (reciprocal rank fusion)
  max_per_section=N  keep at most N chunks from the same filing section (ticker + period + Item)
"""

import json
import math
import re
from collections import Counter, defaultdict
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
_bm25 = None        # keyword index, built on first hybrid search

RRF_K = 60          # reciprocal rank fusion constant (the usual default)
TOKEN_RE = re.compile(r"[a-z0-9]+")
STOPWORDS = {"the", "a", "an", "of", "in", "its", "it", "to", "and", "or", "what", "did", "was",
             "were", "is", "how", "which", "for", "on", "from", "say", "about", "had", "have", "do",
             "does", "their", "this", "that", "by", "at", "with", "much", "many"}


def set_index(name: str) -> None:
    """Switch to another chunk/vector index, e.g. "fixed" -> data/chunks_fixed.jsonl +
    data/embeddings_fixed.npy. "main" is the default index. Used by Experiment 1."""
    global CHUNKS, VECTORS, _model
    if name == "main":
        CHUNKS, VECTORS = Path("data/chunks.jsonl"), Path("data/embeddings.npy")
    else:
        CHUNKS, VECTORS = Path(f"data/chunks_{name}.jsonl"), Path(f"data/embeddings_{name}.npy")
    global _bm25
    _model = None          # forces _load() to read the new files
    _bm25 = None


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


def _tokens(text: str) -> list[str]:
    return [t for t in TOKEN_RE.findall(text.lower()) if t not in STOPWORDS]


def _build_bm25(k1: float = 1.5, b: float = 0.75) -> dict:
    """Classic BM25 over all chunk texts: an inverted index (term -> {chunk: count})."""
    postings = defaultdict(dict)
    lengths = np.zeros(len(_chunks))
    for i, c in enumerate(_chunks):
        toks = _tokens(c["text"])
        lengths[i] = len(toks)
        for term, tf in Counter(toks).items():
            postings[term][i] = tf
    n = len(_chunks)
    idf = {t: math.log(1 + (n - len(d) + 0.5) / (len(d) + 0.5)) for t, d in postings.items()}
    return {"postings": postings, "idf": idf, "lengths": lengths, "avgdl": lengths.mean(), "k1": k1, "b": b}


def _bm25_scores(question: str) -> np.ndarray:
    global _bm25
    if _bm25 is None:
        _bm25 = _build_bm25()
    ix = _bm25
    scores = np.zeros(len(_chunks))
    for term in set(_tokens(question)):
        if term not in ix["postings"]:
            continue
        idf = ix["idf"][term]
        for i, tf in ix["postings"][term].items():
            norm = ix["k1"] * (1 - ix["b"] + ix["b"] * ix["lengths"][i] / ix["avgdl"])
            scores[i] += idf * tf * (ix["k1"] + 1) / (tf + norm)
    return scores


def _ranking(question: str, mode: str) -> tuple[np.ndarray, np.ndarray]:
    """Chunk indices best-first, plus the dense (cosine) score of every chunk."""
    q = _model.encode([question], normalize_embeddings=True)[0]
    dense = _vectors @ q                      # cosine similarity: vectors are normalised
    dense_order = np.argsort(dense)[::-1]
    if mode == "dense":
        return dense_order, dense
    # hybrid: reciprocal rank fusion. A chunk scores 1/(60 + its rank) in each list;
    # ranks, not raw scores, are combined, so the two scales never need matching.
    bm25_order = np.argsort(_bm25_scores(question))[::-1]
    rrf = np.zeros(len(_chunks))
    rrf[dense_order] += 1.0 / (RRF_K + np.arange(1, len(_chunks) + 1))
    rrf[bm25_order] += 1.0 / (RRF_K + np.arange(1, len(_chunks) + 1))
    return np.argsort(rrf)[::-1], dense


def retrieve(question: str, k: int = 5, ticker: str | None = None, fiscal_years: list[int] | None = None,
             latest_only: bool = False, mode: str = "dense", max_per_section: int | None = None) -> list[dict]:
    _load()
    top, scores = _ranking(question, mode)
    per_section = Counter()
    results = []
    for i in top:
        if ticker and _chunks[i]["ticker"] != ticker:
            continue
        if fiscal_years and _chunks[i]["fiscal_year"] not in fiscal_years:
            continue
        if latest_only and _chunks[i]["fiscal_year"] != _latest[_chunks[i]["ticker"]]:
            continue
        section = (_chunks[i]["ticker"], _chunks[i]["period_end"], _chunks[i]["item"])
        if max_per_section and per_section[section] >= max_per_section:
            continue
        per_section[section] += 1
        results.append({**_chunks[i], "score": float(scores[i])})
        if len(results) == k:
            break
    return results

def retrieve_multi(question: str, k: int = 5, tickers: list[str] | None = None,
                   fiscal_years: list[int] | None = None, latest: bool = False,
                   mode: str = "dense", max_per_section: int | None = None) -> list[dict]:
    # "latest" only applies when the question names no explicit year: years win.
    latest_only = latest and not fiscal_years
    opts = {"fiscal_years": fiscal_years, "latest_only": latest_only, "mode": mode,
            "max_per_section": max_per_section}
    if not tickers:
        return retrieve(question, k, ticker=None, **opts)
    if len(tickers) == 1:
        return retrieve(question, k, ticker=tickers[0], **opts)
    else:
        per_company = max(1, k//len(tickers))
        results = []
        for t in tickers:
            results.extend(retrieve(question, ticker=t, k=per_company, **opts))
    return results


if __name__ == "__main__":
    import sys
    question = " ".join(sys.argv[1:]) or "What are the risks from export controls?"
    for r in retrieve(question):
        print(f"{r['score']:.3f}  {r['ticker']} {r['period_end']} Item {r['item']}")
        print("   ", r["text"][:200].replace("\n", " "), "\n")
