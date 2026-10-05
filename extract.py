"""Stage 2: turn each raw 10-K HTML file into plain text, split into Items.

Reads  data/raw/index.json  (written by ingest.py)
Writes data/text/<TICKER>/<period_end>.json

Deliberately crude. See TICKETS.md for what's wrong with it.
"""

import json
import re
import warnings
from pathlib import Path

from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

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


def fiscal_year(html: str, period_end: str) -> int:
    """Fiscal year as the company labels it; falls back to the year of period_end."""
    m = FY_RE.search(html)
    return int(m.group(1)) if m else int(period_end[:4])


def html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style"]):
        tag.decompose()
    for tag in soup.find_all("ix:header"):      # hidden XBRL metadata block
        tag.decompose()
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
    index = json.loads((RAW / "index.json").read_text(encoding="utf-8"))
    for filing in index:
        ticker, period = filing["ticker"], filing["period_end"]
        src = RAW / ticker / f"{period}.html"
        html = src.read_text(encoding="utf-8")
        fy = fiscal_year(html, period)
        text = html_to_text(html)
        sections = split_items(text)

        out = OUT / ticker / f"{period}.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({**filing, "fiscal_year": fy, "sections": sections}, indent=1), encoding="utf-8")

        found = ", ".join(s["item"] for s in sections)
        print(f"{ticker} FY{fy} (ends {period})  {len(text):>8,} chars  items: {found}")


if __name__ == "__main__":
    main()
