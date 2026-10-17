"""Copy the chunks and their vectors into the Supabase `chunks` table (pgvector).

Reads  data/chunks_final.jsonl + data/embeddings_final.npy  (same order: line i <-> row i)
Writes table public.chunks  (emptied first, so re-running is safe), including each chunk's
contextual header (Phase 1a), which BM25 reads in retrieve.py

    uv run python upload_pg.py
    uv run python upload_pg.py --chunks data/chunks.jsonl --vectors data/embeddings.npy   # an older index

Needs DATABASE_URL in .env (Supabase > Connect > Session pooler). Run it again whenever
chunk.py or embed.py has been re-run, or the database will search old chunks.
"""

import argparse
import json
import os
import time
from pathlib import Path

import numpy as np
import psycopg
from dotenv import load_dotenv

CHUNKS = Path("data/chunks_final.jsonl")
VECTORS = Path("data/embeddings_final.npy")


def vec_text(v) -> str:
    return "[" + ",".join(f"{x:.7f}" for x in v) + "]"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--chunks", type=Path, default=CHUNKS)
    p.add_argument("--vectors", type=Path, default=VECTORS)
    a = p.parse_args()
    load_dotenv()
    url = os.getenv("DATABASE_URL")
    if not url:
        raise SystemExit("DATABASE_URL is not set in .env")

    chunks = [json.loads(line) for line in a.chunks.open(encoding="utf-8")]
    vectors = np.load(a.vectors)
    if len(chunks) != len(vectors):
        raise SystemExit(f"{len(chunks)} chunks but {len(vectors)} vectors -- re-run embed.py first")

    start = time.time()
    with psycopg.connect(url) as conn:
        with conn.cursor() as cur:
            cur.execute("truncate table chunks")
            columns = "idx, chunk_id, ticker, fiscal_year, period_end, item, text, header, embedding"
            with cur.copy(f"copy chunks ({columns}) from stdin") as copy:
                for i, (c, v) in enumerate(zip(chunks, vectors)):
                    copy.write_row((i, c["id"], c["ticker"], c["fiscal_year"], c["period_end"],
                                    c["item"], c["text"], c.get("header"), vec_text(v)))
            cur.execute("analyze chunks")
            n = cur.execute("select count(*) from chunks").fetchone()[0]
            # sanity check: the database's cosine similarity matches numpy for one pair of rows
            db_sim = cur.execute("select 1 - (a.embedding <=> b.embedding) from chunks a, chunks b "
                                 "where a.idx = 0 and b.idx = 1").fetchone()[0]
    print(f"{n:,} chunks uploaded in {time.time() - start:.0f}s")
    print(f"similarity of rows 0 and 1: database {db_sim:.5f} vs numpy {float(vectors[0] @ vectors[1]):.5f}")


if __name__ == "__main__":
    main()
