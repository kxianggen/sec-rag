"""Stage 3: cut each section into chunks, each carrying its metadata.

Reads  data/text/<TICKER>/<period_end>.json
Writes data/chunks.jsonl   (one JSON object per line)

    uv run python chunk.py                                                  # paragraph packing (default)
    uv run python chunk.py --method fixed --out data/chunks_fixed.jsonl     # Experiment 1
    uv run python chunk.py --text data/text_tables --out data/chunks_tables.jsonl   # Experiment 4

Chunks are packed from whole lines (each line is one paragraph in the
extracted text), up to CHUNK_SIZE characters, so no chunk starts or ends
mid-word. A line longer than CHUNK_SIZE is first split at spaces.

chunk_text() (fixed size + overlap) is kept for comparison in Experiment 1.
"""

import argparse
import json
from pathlib import Path

TEXT = Path("data/text")
OUT = Path("data/chunks.jsonl")
CHUNK_SIZE = 1000   # characters
CHUNK_OVERLAP = 150


def chunk_text(text: str, size: int, overlap: int) -> list[str]:
    if size - overlap <= 0:
        raise ValueError(f"overlap ({overlap}) must be smaller than size ({size})")
    return [text[i:i + size] for i in range(0, len(text), size - overlap)]

def pack(pieces: list[str], size: int, sep: str) -> list[str]:
    chunks = []
    current: str = ""

    for piece in pieces:
        if current == "":
            current = piece
        elif len(current) + len(sep) + len(piece) <= size:
            current += sep + piece
        else:
            chunks.append(current)
            current = piece

    if current:
        chunks.append(current)

    return chunks

def chunk_by_paragraph(text: str, size: int) -> list[str]:
    pieces = []
    for line in text.split("\n"):

        if not line.strip():
            continue

        if len(line) <= size:
            pieces.append(line)
        else:
            words = line.split(" ")
            parts = pack(words, size, " ")
            pieces.extend(parts)
    
    return pack(pieces, size, "\n")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--method", choices=["paragraph", "fixed"], default="paragraph")
    p.add_argument("--out", type=Path, default=OUT)
    p.add_argument("--text", type=Path, default=TEXT, help="folder written by extract.py")
    a = p.parse_args()

    # Experiment 1 compares ONE thing: where the cuts fall. Same size (1000), no overlap in either.
    def split(text: str) -> list[str]:
        if a.method == "fixed":
            return chunk_text(text, CHUNK_SIZE, 0)
        return chunk_by_paragraph(text, CHUNK_SIZE)

    n = 0
    with a.out.open("w", encoding="utf-8") as f:
        for path in sorted(a.text.glob("*/*.json")):
            filing = json.loads(path.read_text(encoding="utf-8"))
            for section in filing["sections"]:
                for i, piece in enumerate(split(section["text"])):
                    chunk = {
                        "id": f"{filing['ticker']}-{filing['period_end']}-{section['item']}-{i}",
                        "ticker": filing["ticker"],
                        "period_end": filing["period_end"],
                        "fiscal_year": filing["fiscal_year"],
                        "item": section["item"],
                        "url": filing["url"],
                        "text": piece,
                    }
                    f.write(json.dumps(chunk) + "\n")
                    n += 1
    print(f"{n:,} chunks ({a.method}) written to {a.out}")


if __name__ == "__main__":
    main()
