"""Stage 3: cut each section into chunks, each carrying its metadata.

Reads  data/text/<TICKER>/<period_end>.json
Writes data/chunks.jsonl   (one JSON object per line)

Chunks are packed from whole lines (each line is one paragraph in the
extracted text), up to CHUNK_SIZE characters, so no chunk starts or ends
mid-word. A line longer than CHUNK_SIZE is first split at spaces.

chunk_text() (fixed size + overlap) is kept for comparison in Experiment 1.
"""

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
    n = 0
    with OUT.open("w", encoding="utf-8") as f:
        for path in sorted(TEXT.glob("*/*.json")):
            filing = json.loads(path.read_text(encoding="utf-8"))
            for section in filing["sections"]:
                for i, piece in enumerate(chunk_by_paragraph(section["text"], CHUNK_SIZE)):
                    chunk = {
                        "id": f"{filing['ticker']}-{filing['period_end']}-{section['item']}-{i}",
                        "ticker": filing["ticker"],
                        "period_end": filing["period_end"],
                        "item": section["item"],
                        "url": filing["url"],
                        "text": piece,
                    }
                    f.write(json.dumps(chunk) + "\n")
                    n += 1
    print(f"{n:,} chunks written to {OUT}")


if __name__ == "__main__":
    main()
