"""Stage 3: cut each section into chunks, each carrying its metadata.

Reads  data/text/<TICKER>/<period_end>.json
Writes data/chunks.jsonl   (one JSON object per line)

    uv run python chunk.py                                                  # paragraph packing (default)
    uv run python chunk.py --method fixed --out data/chunks_fixed.jsonl     # Experiment 1
    uv run python chunk.py --text data/text_tables --out data/chunks_tables.jsonl   # Experiment 4
    uv run python chunk.py --headers --out data/chunks_hdr.jsonl                    # Phase 1a

Chunks are packed from whole lines (each line is one paragraph in the
extracted text), up to CHUNK_SIZE characters, so no chunk starts or ends
mid-word. A line longer than CHUNK_SIZE is first split at spaces.

chunk_text() (fixed size + overlap) is kept for comparison in Experiment 1.

--headers (Phase 1a, contextual chunk headers): every chunk also gets a "header" field, e.g.
    "NVIDIA 10-K fiscal 2026 · Item 7 Management's Discussion and Analysis · Results of Operations"
= company, year, section, and the nearest sub-heading ABOVE the chunk. The chunk's "text" is
unchanged; embed.py and retrieve.py's BM25 read header + text. A chunk in the middle of a
section often never says which company or topic it is about ("we", "this increase") -- the
header puts that back.
"""

import argparse
import bisect
import json
import re
from pathlib import Path

TEXT = Path("data/text")
OUT = Path("data/chunks.jsonl")
CHUNK_SIZE = 1000   # characters
CHUNK_OVERLAP = 150


NAMES = {"NVDA": "NVIDIA", "AMD": "AMD", "INTC": "Intel", "MU": "Micron", "AVGO": "Broadcom",
         "QCOM": "Qualcomm", "MRVL": "Marvell"}
ITEM_NAMES = {"1": "Business", "1A": "Risk Factors", "1B": "Unresolved Staff Comments", "1C": "Cybersecurity",
              "2": "Properties", "3": "Legal Proceedings", "4": "Mine Safety Disclosures",
              "5": "Market for Common Equity", "6": "Reserved", "7": "Management's Discussion and Analysis",
              "7A": "Market Risk", "8": "Financial Statements", "9": "Changes in Accountants",
              "9A": "Controls and Procedures", "9B": "Other Information", "9C": "Foreign Jurisdictions",
              "10": "Directors and Officers", "11": "Executive Compensation", "12": "Security Ownership",
              "13": "Relationships and Director Independence", "14": "Accountant Fees",
              "15": "Exhibits and Financial Statement Schedules", "16": "Form 10-K Summary"}
SMALL_WORDS = {"and", "of", "the", "in", "for", "to", "a", "an", "on", "or", "by", "with", "our", "from"}
NOT_HEADINGS = {"year ended", "change", "total", "name", "age", "position"}   # table cells, not titles


def is_heading(line: str) -> bool:
    """A sub-heading line, e.g. "Human Capital Management" or "Results of Operations": short, no
    sentence punctuation at the end, no figures, and every main word Capitalised."""
    s = line.strip()
    if not 3 <= len(s) <= 80 or s.lower() in NOT_HEADINGS:
        return False
    if s[-1] in ".:;,)" or not s[0].isupper() or re.search(r"\d{2,}|\$|%|=", s):
        return False
    main = [w for w in s.split() if w.lower() not in SMALL_WORDS]
    return 0 < len(main) <= 8 and all(w[0].isupper() for w in main)


def headings_for(text: str, pieces: list[str]) -> list[str]:
    """For each chunk (in order), the last sub-heading at or above where the chunk starts."""
    starts, titles, pos = [], [], 0
    for line in text.split("\n"):
        if is_heading(line):
            starts.append(pos)
            titles.append(line.strip())
        pos += len(line) + 1
    out, cursor = [], 0
    for piece in pieces:
        first = piece.split("\n")[0]
        found = text.find(first, cursor)
        at = found if found >= 0 else cursor
        cursor = at + 1
        i = bisect.bisect_right(starts, at) - 1
        out.append(titles[i] if i >= 0 else "")
    return out


def make_header(ticker: str, fiscal_year: int, item: str, heading: str) -> str:
    parts = [f"{NAMES.get(ticker, ticker)} 10-K fiscal {fiscal_year}",
             f"Item {item} {ITEM_NAMES.get(item, '')}".strip()]
    if heading:
        parts.append(heading)
    return " · ".join(parts)


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
    p.add_argument("--headers", action="store_true", help="Phase 1a: add a contextual header to every chunk")
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
                pieces = split(section["text"])
                headings = headings_for(section["text"], pieces) if a.headers else None
                for i, piece in enumerate(pieces):
                    chunk = {
                        "id": f"{filing['ticker']}-{filing['period_end']}-{section['item']}-{i}",
                        "ticker": filing["ticker"],
                        "period_end": filing["period_end"],
                        "fiscal_year": filing["fiscal_year"],
                        "item": section["item"],
                        "url": filing["url"],
                        "text": piece,
                    }
                    if a.headers:
                        chunk["header"] = make_header(filing["ticker"], filing["fiscal_year"],
                                                      section["item"], headings[i])
                    f.write(json.dumps(chunk) + "\n")
                    n += 1
    print(f"{n:,} chunks ({a.method}{', with headers' if a.headers else ''}) written to {a.out}")


if __name__ == "__main__":
    main()
