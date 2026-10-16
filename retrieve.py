"""Stage 5: find the chunks most similar to a question.

Loads data/chunks.jsonl and data/embeddings.npy, embeds the question with the
same model, and returns the top-k chunks by cosine similarity.

Plain numpy, no vector database, no framework. See TICKETS.md.

Two storage backends ("stores"), same results for dense search:
  numpy     data/chunks.jsonl + data/embeddings.npy, searched in memory (default)
  pgvector  the `chunks` table on Supabase (Postgres + pgvector), searched with SQL;
            needs DATABASE_URL in .env. Filters run inside the query (WHERE ...).
Pick with set_store("pgvector") or SEC_RAG_STORE=pgvector.

Query expansion (Phase 1b, default ON since 16 Oct): expand=True adds the long form of finance abbreviations to the
search text, e.g. "R&D" -> "R&D (research and development)", because BM25 only matches exact
words and the filings write the long form. The prompt still gets the original question.

Two optional switches (Experiment 3):
  mode="hybrid"      blend the embedding ranking with a BM25 keyword ranking (reciprocal rank fusion)
  max_per_section=N  keep at most N chunks from the same filing section (ticker + period + Item)
"""

import json
import math
import os
import re
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

# Default index since Phase 1a (16 Oct): table rows (Exp 4) + contextual headers.
# 0.67 / CRAG +0.60 / 2 wrong vs the old paragraph index 0.63 / +0.47 / 5 (rubric v2.1).
CHUNKS = Path("data/chunks_tables_hdr.jsonl")
VECTORS = Path("data/embeddings_tables_hdr.npy")
MODEL = "sentence-transformers/all-MiniLM-L6-v2"

_model = None
_chunks = None
_vectors = None
_latest = None      # {ticker: newest fiscal_year in the corpus}, built in _load()
_bm25 = None        # keyword index, built on first hybrid search
_conn = None        # Postgres connection (pgvector store only)

STORE = os.getenv("SEC_RAG_STORE", "numpy")

RRF_K = 60          # reciprocal rank fusion constant (the usual default)
TOKEN_RE = re.compile(r"[a-z0-9]+")
STOPWORDS = {"the", "a", "an", "of", "in", "its", "it", "to", "and", "or", "what", "did", "was",
             "were", "is", "how", "which", "for", "on", "from", "say", "about", "had", "have", "do",
             "does", "their", "this", "that", "by", "at", "with", "much", "many"}


def set_index(name: str) -> None:
    """Switch to another chunk/vector index, e.g. "fixed" -> data/chunks_fixed.jsonl +
    data/embeddings_fixed.npy. "main" = the original paragraph index (data/chunks.jsonl),
    "tables_hdr" = the default since Phase 1a."""
    global CHUNKS, VECTORS, _model
    if name == "main":
        CHUNKS, VECTORS = Path("data/chunks.jsonl"), Path("data/embeddings.npy")
    else:
        CHUNKS, VECTORS = Path(f"data/chunks_{name}.jsonl"), Path(f"data/embeddings_{name}.npy")
    global _bm25
    _model = None          # forces _load() to read the new files
    _bm25 = None


def set_store(name: str) -> None:
    """"numpy" (local files) or "pgvector" (Supabase)."""
    global STORE, _model, _bm25
    if name not in ("numpy", "pgvector"):
        raise ValueError(f"unknown store {name!r}")
    STORE = name
    _model = None
    _bm25 = None


def _connect():
    global _conn
    if _conn is None:
        import psycopg
        from dotenv import load_dotenv
        load_dotenv()
        url = os.getenv("DATABASE_URL")
        if not url:
            raise SystemExit("DATABASE_URL is not set in .env (Supabase > Connect > Session pooler)")
        _conn = psycopg.connect(url, autocommit=True)
    return _conn


def _load():
    global _model, _chunks, _vectors, _latest
    if _model is None:
        _model = SentenceTransformer(MODEL)
        if STORE == "pgvector":
            # Chunk text + metadata still come into memory: BM25 (hybrid) needs every text.
            # Vectors stay in the database; only the search runs there.
            rows = _connect().execute(
                "select chunk_id, ticker, period_end, fiscal_year, item, text from chunks order by idx"
            ).fetchall()
            _chunks = [dict(zip(("id", "ticker", "period_end", "fiscal_year", "item", "text"), r)) for r in rows]
            _vectors = None
        else:
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
        toks = _tokens(c.get("header", "") + "\n" + c["text"])   # header: Phase 1a (if present)
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


def _ranking_pg(question: str, mode: str, ticker, fiscal_years, latest_only, pool: int | None):
    """pgvector store: the filters run inside Postgres (WHERE), but every rank is a GLOBAL
    rank -- the chunk's position among ALL chunks, computed before filtering, exactly like
    the numpy store. Hybrid mixes ranks (1 / (60 + rank)), so ranking only the filtered
    chunks would change the mix: that version swapped ~2 of 10 chunks per question and
    scored 0.57 vs 0.65 (FAILURES #38)."""
    q = _model.encode([question], normalize_embeddings=True)[0]
    qtext = "[" + ",".join(f"{x:.7f}" for x in q) + "]"
    where, params = [], []
    if ticker:
        where.append("ticker = %s")
        params.append(ticker)
    if fiscal_years:
        where.append("fiscal_year = any(%s)")
        params.append(list(fiscal_years))
    if latest_only:
        where.append("ticker || ':' || fiscal_year = any(%s)")
        params.append([f"{t}:{y}" for t, y in _latest.items()])
    # inner query: distance + global rank for every chunk; outer query: keep the filtered ones
    sql = ("select idx, score, global_rank from ("
           "  select idx, ticker, fiscal_year, 1 - (embedding <=> %s::extensions.vector) as score,"
           "         row_number() over (order by embedding <=> %s::extensions.vector) as global_rank"
           "  from chunks) ranked"
           + (" where " + " and ".join(where) if where else "")
           + " order by global_rank"
           + (" limit %s" if pool else ""))
    rows = _connect().execute(sql, [qtext, qtext, *params] + ([pool] if pool else [])).fetchall()
    dense = np.zeros(len(_chunks))       # chunks outside the dense pool show score 0.000
    dense_rank = {}
    for idx, score, global_rank in rows:
        dense[idx] = score
        dense_rank[idx] = global_rank
    dense_order = np.array([idx for idx, _, _ in rows], dtype=int)
    if mode == "dense":
        return dense_order, dense
    # hybrid: BM25 global ranks (same numpy call as the numpy store), then reciprocal rank fusion
    bm25_order = np.argsort(_bm25_scores(question))[::-1]
    rrf = defaultdict(float)
    for idx, rank in dense_rank.items():
        rrf[idx] += 1.0 / (RRF_K + rank)
    for rank, idx in enumerate(bm25_order, 1):
        if _passes(idx, ticker, fiscal_years, latest_only):
            rrf[int(idx)] += 1.0 / (RRF_K + rank)
    return np.array(sorted(rrf, key=rrf.get, reverse=True), dtype=int), dense


def _passes(i: int, ticker, fiscal_years, latest_only) -> bool:
    c = _chunks[i]
    if ticker and c["ticker"] != ticker:
        return False
    if fiscal_years and c["fiscal_year"] not in fiscal_years:
        return False
    if latest_only and c["fiscal_year"] != _latest[c["ticker"]]:
        return False
    return True


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
    if STORE == "pgvector":
        # dense: only the top k are needed. Hybrid (or the cap) needs the dense rank of EVERY
        # filtered chunk to match the numpy store exactly, so no LIMIT (a few hundred rows,
        # all 8,504 only for questions that name no company).
        pool = k if (mode == "dense" and not max_per_section) else None
        top, scores = _ranking_pg(question, mode, ticker, fiscal_years, latest_only, pool)
    else:
        top, scores = _ranking(question, mode)
    per_section = Counter()
    results = []
    for i in top:
        if not _passes(i, ticker, fiscal_years, latest_only):
            continue
        section = (_chunks[i]["ticker"], _chunks[i]["period_end"], _chunks[i]["item"])
        if max_per_section and per_section[section] >= max_per_section:
            continue
        per_section[section] += 1
        results.append({**_chunks[i], "score": float(scores[i])})
        if len(results) == k:
            break
    return results

ABBREVIATIONS = {
    r"\bR\s*&\s*D\b": "research and development",
    r"\bSG\s*&\s*A\b": "selling, general and administrative",
    r"\bcapex\b": "capital expenditures",
    r"\bEPS\b": "earnings per share",
    r"\bheadcount\b": "employees",
}


def expand_query(question: str) -> str:
    """Add the long form after each abbreviation the question uses (search text only)."""
    extra = [long for pattern, long in ABBREVIATIONS.items()
             if re.search(pattern, question, re.IGNORECASE) and long.lower() not in question.lower()]
    return question + (" (" + "; ".join(extra) + ")" if extra else "")


def retrieve_multi(question: str, k: int = 5, tickers: list[str] | None = None,
                   fiscal_years: list[int] | None = None, latest: bool = False,
                   mode: str = "dense", max_per_section: int | None = None,
                   expand: bool = True) -> list[dict]:
    if expand:
        question = expand_query(question)
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


def retrieve_planned(searches: list[dict], k: int = 10, latest: bool = False, mode: str = "hybrid",
                     max_per_section: int | None = None) -> list[dict]:
    """Phase 1b part 2: run one search per planned target (rewrite.plan_searches), each with
    its own search text and filters, sharing the k slots like retrieve_multi (k // n each)."""
    per_search = max(1, k // len(searches))
    results = []
    for s in searches:
        years = s["fiscal_years"]
        results.extend(retrieve(s["query"], per_search, ticker=s["ticker"], fiscal_years=years,
                                latest_only=latest and not years, mode=mode, max_per_section=max_per_section))
    return results


if __name__ == "__main__":
    import sys
    question = " ".join(sys.argv[1:]) or "What are the risks from export controls?"
    for r in retrieve(question):
        print(f"{r['score']:.3f}  {r['ticker']} {r['period_end']} Item {r['item']}")
        print("   ", r["text"][:200].replace("\n", " "), "\n")
