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
    return text.strip()


def split_items(text: str) -> list[dict]:
    """Split the text at every Item heading.

    The table of contents also contains every heading, packed close together,
    so any "section" shorter than 1,000 characters is treated as a TOC entry
    and thrown away.
    """
    matches = list(ITEM_RE.finditer(text))
    sections = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        if len(body) < 1000:
            continue
        sections.append({"item": m.group(1).upper(), "text": body})
    return sections


def main():
    index = json.loads((RAW / "index.json").read_text(encoding="utf-8"))
    for filing in index:
        ticker, period = filing["ticker"], filing["period_end"]
        src = RAW / ticker / f"{period}.html"
        text = html_to_text(src.read_text(encoding="utf-8"))
        sections = split_items(text)

        out = OUT / ticker / f"{period}.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({**filing, "sections": sections}, indent=1), encoding="utf-8")

        found = ", ".join(s["item"] for s in sections)
        print(f"{ticker} {period}  {len(text):>8,} chars  items: {found}")


if __name__ == "__main__":
    main()
