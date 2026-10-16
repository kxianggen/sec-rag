"""Stage 4: turn every chunk into a vector with a local embedding model.

Reads  data/chunks.jsonl
Writes data/embeddings.npy   (one row per chunk, same order as chunks.jsonl)

Runs on your laptop, no API key, no cost. First run downloads the model (~90 MB).

    uv run python embed.py                                                                  # main index
    uv run python embed.py --chunks data/chunks_fixed.jsonl --out data/embeddings_fixed.npy # Experiment 1
    uv run python embed.py --chunks data/chunks_hdr.jsonl --out data/embeddings_hdr.npy     # Phase 1a

A chunk with a "header" field (chunk.py --headers) is embedded as header + newline + text.
The model reads at most 256 word pieces; anything longer is cut off silently, so the
script reports how many chunks are cut. --count-only reports that and stops (writes nothing).
"""

import argparse
import json
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

CHUNKS = Path("data/chunks.jsonl")
OUT = Path("data/embeddings.npy")
MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def embed_text(chunk: dict) -> str:
    """What the model reads: the chunk text, with its contextual header first if it has one."""
    return chunk["header"] + "\n" + chunk["text"] if chunk.get("header") else chunk["text"]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--chunks", type=Path, default=CHUNKS)
    p.add_argument("--out", type=Path, default=OUT)
    p.add_argument("--count-only", action="store_true", help="only report how many chunks are cut")
    a = p.parse_args()

    chunks = [json.loads(line) for line in a.chunks.open(encoding="utf-8")]
    model = SentenceTransformer(MODEL)
    texts = [embed_text(c) for c in chunks]
    limit = model.max_seq_length
    cut = sum(len(model.tokenizer.tokenize(t)) + 2 > limit for t in texts)   # +2: start/end markers
    print(f"{cut:,} of {len(texts):,} chunks are longer than {limit} word pieces (their end is not embedded)")
    if a.count_only:
        return
    vectors = model.encode(
        texts,
        batch_size=64,
        show_progress_bar=True,
        normalize_embeddings=True,
    )
    np.save(a.out, vectors)
    print(f"{vectors.shape[0]:,} vectors of size {vectors.shape[1]} written to {a.out}")


if __name__ == "__main__":
    main()
