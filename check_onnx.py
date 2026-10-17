"""Does ONNX Runtime embed questions the same way PyTorch does? (Before deploying the slim container.)

    uv run python check_onnx.py

Embeds every golden + held-out question with both backends of the SAME model (all-MiniLM-L6-v2)
and prints the cosine similarity of each pair. 1.0000 = identical direction. Chunk vectors are not
re-made: they stay the PyTorch ones from embed.py, so only the question side can differ.
"""

import json
from pathlib import Path

import numpy as np

import retrieve

questions = [json.loads(l)["question"] for f in ("golden.jsonl", "heldout.jsonl")
             for l in Path(f).read_text(encoding="utf-8").splitlines() if l.strip()]

retrieve.EMBEDDER = "torch"
a = retrieve._make_model().encode(questions, normalize_embeddings=True)
retrieve.EMBEDDER = "onnx"
b = retrieve._make_model().encode(questions, normalize_embeddings=True)

cos = (a * b).sum(axis=1)
print(f"{len(questions)} questions: cosine torch vs onnx  min {cos.min():.6f}  mean {cos.mean():.6f}")
worst = int(cos.argmin())
print(f"least similar: {cos[worst]:.6f}  {questions[worst][:70]}")
