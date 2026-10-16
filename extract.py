"""Stage 2: turn each raw 10-K HTML file into plain text, split into Items.

Reads  data/raw/index.json  (written by ingest.py)
Writes data/text/<TICKER>/<period_end>.json

    uv run python extract.py                                     # tables as self-contained rows
    uv run python extract.py --tables cells --out data/text_cells   # old behaviour (Experiment 4)

Experiment 4 — tables. The old extractor put every table cell on its own line, so a number
lost its row label and its column (which year?). Now each table row becomes one line that
carries its own column headers:
    Total debt principal outstanding (in millions): November 2, 2025 = $67,120; November 3, 2024 = $69,847
A chunk cut in the middle of a table therefore still knows which number belongs to which year.
"""

import argparse
import json
import re
import warnings
from pathlib import Path

from bs4 import BeautifulSoup, NavigableString, XMLParsedAsHTMLWarning

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

RAW = Path("data/raw")
OUT = Path("data/text")

# Matches a line that starts an Item heading, e.g. "Item 1A. Risk Factors"
ITEM_RE = re.compile(
    r"(?im)^[ \t]*item[\s\xa0]+(1a|1b|1c|1|2|3|4|5|6|7a|7|8|9a|9b|9c|9|10|11|12|13|14|15|16)\b\.?"
)
# The company's own label for the fiscal year, from the filing's hidden XBRL tags,
# e.g. <ix:nonNumeric name="dei:DocumentFiscalYearFocus" ...>2026</ix:nonNumeric>
FY_RE = re.compile(r'DocumentFiscalYearFocus"[^>]*>\s*(\d{4})\s*<')

NUMBER_RE = re.compile(r"^\(?-?\$?\s?\(?[\d,]*\.?\d+\)?\s?%?\)?$|^[—–-]+$")   # 1,234  (56)  $7  12.5%  —
YEAR_ONLY = re.compile(r"^(?:fiscal\s+(?:year\s+)?)?(?:19|20)\d{2}$", re.I)
UNIT_RE = re.compile(r"\((?:dollars |amounts )?in (millions|thousands|billions)[^)]*\)", re.I)


def fiscal_year(html: str, period_end: str) -> int:
    """Fiscal year as the company labels it; falls back to the year of period_end."""
    m = FY_RE.search(html)
    return int(m.group(1)) if m else int(period_end[:4])


def _cells(tr) -> list[str]:
    """Non-empty cell texts of a row, with lone '$', '%' and ')' glued to their number."""
    raw = [" ".join(td.get_text(" ").split()) for td in tr.find_all(["td", "th"])]
    out = []
    for c in raw:
        c = c.replace("\xa0", " ").strip()
        if not c:
            continue
        if out and c in ("%", ")", "%)") and NUMBER_RE.match(out[-1].replace(" ", "")):
            out[-1] += c
        elif out and out[-1] in ("$", "(", "$(", "($"):
            out[-1] += c
        else:
            out.append(c)
    return out


def _is_number(c: str) -> bool:
    return bool(NUMBER_RE.match(c.replace(" ", "")))


def table_to_text(table) -> str:
    """One line per row. Numeric rows get their column headers written into the line."""
    rows = [_cells(tr) for tr in table.find_all("tr")]
    rows = [r for r in rows if r]
    if not rows:
        return ""
    unit = None
    headers = None
    lines = []
    for cells in rows:
        m = UNIT_RE.search(" ".join(cells))
        if m and not unit:
            unit = m.group(1).lower()
        if all(YEAR_ONLY.match(c) for c in cells):          # "2025 | 2024 | 2023" is a header, not data
            headers = cells
            lines.append(" | ".join(cells))
            continue
        label = cells[0] if not _is_number(cells[0]) else ""
        values = cells[1:] if label else cells
        numeric = values and all(_is_number(v) for v in values)
        if not numeric:
            # header candidate: a text row with 2+ cells ("November 2, 2025 | November 3, 2024",
            # "Gross | Accumulated amortization | Net"); one-cell rows are section labels
            names = [c for c in cells if not UNIT_RE.fullmatch(c)]
            if len(names) >= 2:
                headers = names
            lines.append(" | ".join(cells))
            continue
        name = label + (f" (in {unit})" if unit and label else "")
        if headers and len(values) <= len(headers):
            cols = headers[-len(values):]          # numbers sit in the right-most columns
            lines.append(f"{name}: " + "; ".join(f"{h} = {v}" for h, v in zip(cols, values)))
        else:
            lines.append(f"{name}: " + " | ".join(values) if name else " | ".join(values))
    return "\n".join(lines)


def html_to_text(html: str, tables: str = "rows") -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style"]):
        tag.decompose()
    for tag in soup.find_all("ix:header"):      # hidden XBRL metadata block
        tag.decompose()
    if tables == "rows":
        for table in soup.find_all("table"):
            if table.find_parent("table"):        # nested tables are handled by their parent
                continue
            table.replace_with(NavigableString("\n" + table_to_text(table) + "\n"))
    text = soup.get_text("\n")
    text = text.replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    text = re.sub(r"\n\d{1,3}\nTable of Contents\n", "\n", text)
    text = re.sub(r"\nTable of Contents\n", "\n", text)
    return text.strip()


def split_items(text: str) -> list[dict]:
    """Split the text into Item sections.

    Every heading appears twice: once in the table of contents, once in the body.
    The body starts at the last "Item 1", so every match before it is ignored.
    """
    matches = list(ITEM_RE.finditer(text))

    body_start = None
    for i, m in enumerate(matches):
        if m.group(1) == "1":
            body_start = i
    if body_start is None:
        return []
    matches = matches[body_start:]

    sections = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        sections.append({"item": m.group(1).upper(), "text": body})
    return sections


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--tables", choices=["rows", "cells"], default="rows")
    p.add_argument("--out", type=Path, default=OUT)
    a = p.parse_args()

    index = json.loads((RAW / "index.json").read_text(encoding="utf-8"))
    for filing in index:
        ticker, period = filing["ticker"], filing["period_end"]
        src = RAW / ticker / f"{period}.html"
        html = src.read_text(encoding="utf-8")
        fy = fiscal_year(html, period)
        text = html_to_text(html, a.tables)
        sections = split_items(text)

        out = a.out / ticker / f"{period}.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({**filing, "fiscal_year": fy, "sections": sections}, indent=1), encoding="utf-8")

        found = ", ".join(s["item"] for s in sections)
        print(f"{ticker} FY{fy} (ends {period})  {len(text):>8,} chars  items: {found}")


if __name__ == "__main__":
    main()
