"""Stage 3: cut each section into chunks, each carrying its metadata.

Reads  data/text/<TICKER>/<period_end>.json
Writes data/chunks.jsonl   (one JSON object per line)

chunks overlap by CHUNK_OVERLAP characters
"""

import json
from pathlib import Path

TEXT = Path("data/text")
OUT = Path("data/chunks.jsonl")
CHUNK_SIZE = 1000   # characters
CHUNK_OVERLAP = 150


def chunk_text(text: str, size: int, overlap: int) -> list[str]:
    return [text[i:i + size] for i in range(0, len(text), size - overlap)]


def main():
    n = 0
    with OUT.open("w", encoding="utf-8") as f:
        for path in sorted(TEXT.glob("*/*.json")):
            filing = json.loads(path.read_text(encoding="utf-8"))
            for section in filing["sections"]:
                for i, piece in enumerate(chunk_text(section["text"], CHUNK_SIZE, CHUNK_OVERLAP)):
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
