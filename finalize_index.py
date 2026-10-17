"""Final rebuild: drop Intel from the adopted index (tables + contextual headers).

Reads  data/chunks_tables_hdr.jsonl + data/embeddings_tables_hdr.npy   (line i <-> row i)
Writes data/chunks_final.jsonl     + data/embeddings_final.npy         (same order, Intel removed)

    uv run python finalize_index.py

Intel was descoped on 13 Oct: its 10-K text never split into sections properly (the "sections"
were ~40-character index rows; FAILURES.md). Removing its rows needs NO re-embedding -- every other
chunk keeps exactly the vector it had; only the rows are taken out, in order.
companies.py still recognises "Intel", so an Intel question finds no filing and gets a clean
"Not in the filings." instead of an answer built from broken text.
"""

import json
from pathlib import Path

import numpy as np

SRC_CHUNKS, SRC_VECTORS = Path("data/chunks_tables_hdr.jsonl"), Path("data/embeddings_tables_hdr.npy")
OUT_CHUNKS, OUT_VECTORS = Path("data/chunks_final.jsonl"), Path("data/embeddings_final.npy")
DROP = {"INTC"}


def main():
    chunks = [json.loads(line) for line in SRC_CHUNKS.open(encoding="utf-8")]
    vectors = np.load(SRC_VECTORS)
    if len(chunks) != len(vectors):
        raise SystemExit(f"{len(chunks)} chunks but {len(vectors)} vectors -- re-run embed.py first")
    keep = [i for i, c in enumerate(chunks) if c["ticker"] not in DROP]
    with OUT_CHUNKS.open("w", encoding="utf-8") as f:
        for i in keep:
            f.write(json.dumps(chunks[i]) + "\n")
    np.save(OUT_VECTORS, vectors[keep])
    tickers = sorted({chunks[i]["ticker"] for i in keep})
    print(f"{len(chunks):,} -> {len(keep):,} chunks ({len(chunks) - len(keep):,} Intel rows dropped); "
          f"companies: {', '.join(tickers)}")
    print(f"wrote {OUT_CHUNKS} and {OUT_VECTORS} {np.load(OUT_VECTORS).shape}")


if __name__ == "__main__":
    main()
