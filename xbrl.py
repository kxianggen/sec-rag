"""Phase 2, step 1: pull the machine-readable numbers (inline XBRL) out of every 10-K.

Reads  data/raw/<TICKER>/<period_end>.html   (the filings ingest.py downloaded)
       data/text/<TICKER>/<period_end>.json  (only for the filing's fiscal_year label)
Writes data/facts.jsonl                      (one tagged number per line)

    uv run python xbrl.py                     # extract all filings
    uv run python xbrl.py --check             # print the facts our number questions need

Every financial-statement number in a 10-K is wrapped in a tag that says exactly what it is:

    <ix:nonFraction name="us-gaap:Revenues" contextRef="c-1" scale="6" decimals="-6">44,284</ix:nonFraction>

  name        what the number is (a standard us-gaap "concept")
  contextRef  points to a <xbrli:context>: the period (start/end dates, or one date for balance-sheet
              items) and any DIMENSIONS -- e.g. "segment = QCT". A fact with NO dimensions is the
              company-wide total; that is how XBRL keeps "total revenue" apart from "QCT revenues".
  scale="6"   the shown 44,284 is in millions -> 44,284,000,000
  sign="-"    the shown number is negative

Each 10-K also tags the PRIOR years shown in its tables, so one filing gives several fiscal years.
"""

import argparse
import json
import re
import warnings
from datetime import date
from pathlib import Path

from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

RAW = Path("data/raw")
DESCOPED = {"INTC"}     # Intel was dropped from the corpus (finalize_index.py); no facts either
TEXT = Path("data/text")
OUT = Path("data/facts.jsonl")


def _d(s: str) -> date:
    return date.fromisoformat(s.strip())


def parse_contexts(soup) -> dict:
    """context id -> {"start", "end", "instant", "dims"}; dims = {"axis": "member", ...}."""
    out = {}
    for c in soup.find_all(re.compile(r"^xbrli:context$", re.I)):
        start = c.find(re.compile("startdate$", re.I))
        end = c.find(re.compile("enddate$", re.I))
        instant = c.find(re.compile("instant$", re.I))
        dims = {m.get("dimension"): m.get_text(strip=True)
                for m in c.find_all(re.compile("explicitmember$|typedmember$", re.I))}
        out[c.get("id")] = {
            "start": start.get_text(strip=True) if start else None,
            "end": (end or instant).get_text(strip=True) if (end or instant) else None,
            "instant": instant is not None,
            "dims": dims,
        }
    return out


def parse_value(tag) -> float | None:
    """The shown text, cleaned, times 10**scale, with the sign attribute applied."""
    text = tag.get_text(strip=True)
    fmt = (tag.get("format") or "").lower()
    if text in ("", "-", "—", "–") or "zerodash" in fmt or "fixed-zero" in fmt:
        return 0.0
    digits = re.sub(r"[^0-9.]", "", text.replace(",", "") if "comma-decimal" not in fmt else
                    text.replace(".", "").replace(",", "."))
    if not digits or digits == ".":
        return None
    value = float(digits) * 10 ** int(tag.get("scale") or 0)
    return -value if tag.get("sign") == "-" else value


def filing_facts(path: Path, ticker: str, period_end: str, fiscal_year: int) -> list[dict]:
    soup = BeautifulSoup(path.read_text(encoding="utf-8", errors="ignore"), "lxml")
    contexts = parse_contexts(soup)
    filing_end = _d(period_end)
    seen, facts = set(), []
    for tag in soup.find_all(re.compile(r"^ix:nonfraction$", re.I)):
        ctx = contexts.get(tag.get("contextref"))
        if not ctx or not ctx["end"]:
            continue
        value = parse_value(tag)
        if value is None:
            continue
        end = _d(ctx["end"])
        days = (_d(ctx["start"]) and (end - _d(ctx["start"])).days) if ctx["start"] else 0
        key = (tag.get("name"), tag.get("contextref"))
        if key in seen:                       # the same fact is often shown (and tagged) twice
            continue
        seen.add(key)
        facts.append({
            "ticker": ticker,
            "filing_period_end": period_end,
            "filing_fiscal_year": fiscal_year,
            # which fiscal year THIS number belongs to: the filing's own, or a prior year's column
            "fiscal_year": fiscal_year - round((filing_end - end).days / 365.25),
            "concept": tag.get("name"),
            "value": value,
            "unit": tag.get("unitref"),
            "decimals": tag.get("decimals"),
            "start": ctx["start"],
            "end": ctx["end"],
            "period": "instant" if ctx["instant"] else ("year" if 340 <= days <= 380 else f"{days}d"),
            "dims": ctx["dims"],
            "fact_id": tag.get("id"),
        })
    return facts


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--check", action="store_true", help="print the facts our number questions need")
    a = p.parse_args()
    if a.check:
        return check()
    n = 0
    with OUT.open("w", encoding="utf-8") as f:
        for path in sorted(RAW.glob("*/*.html")):
            ticker, period_end = path.parent.name, path.stem
            if ticker in DESCOPED:
                continue
            text = TEXT / ticker / f"{period_end}.json"
            fy = json.loads(text.read_text(encoding="utf-8"))["fiscal_year"] if text.exists() else None
            if fy is None:
                print(f"skip {path} (no fiscal year)")
                continue
            facts = filing_facts(path, ticker, period_end, fy)
            totals = sum(1 for x in facts if not x["dims"])
            print(f"{ticker} FY{fy}: {len(facts):,} facts ({totals:,} company-wide, no dimensions)")
            for x in facts:
                f.write(json.dumps(x) + "\n")
            n += len(facts)
    print(f"{n:,} facts written to {OUT}")


# The numbers golden questions Q5, Q6, Q17, Q18, Q22, Q23 need, with the answer key's value
# (millions). --check finds each one among the company-wide, full-year facts.
CHECKS = [
    ("QCOM", 2024, "ResearchAndDevelopmentExpense", 8893), ("QCOM", 2025, "ResearchAndDevelopmentExpense", 9042),
    ("NVDA", 2026, "NetIncomeLoss", 120067), ("AMD", 2025, "NetIncomeLoss", 4335),
    ("MU", 2024, "Revenues", 25111), ("MU", 2025, "Revenues", 37378),
    ("AVGO", 2024, "ResearchAndDevelopmentExpense", 9310), ("AVGO", 2025, "ResearchAndDevelopmentExpense", 10977),
    ("QCOM", 2025, "Revenues", 44284), ("AVGO", 2025, "Revenues", 63887),
    ("NVDA", 2026, "ResearchAndDevelopmentExpense", 18497), ("AMD", 2025, "ResearchAndDevelopmentExpense", 8091),
]
REVENUE_CONCEPTS = ("Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax")


def check():
    facts = [json.loads(line) for line in OUT.open(encoding="utf-8")]
    ok = 0
    for ticker, fy, concept, expected in CHECKS:
        names = REVENUE_CONCEPTS if concept == "Revenues" else (concept,)
        hits = sorted({(x["value"] / 1e6, x["filing_fiscal_year"]) for x in facts
                       if x["ticker"] == ticker and x["fiscal_year"] == fy and not x["dims"]
                       and x["period"] == "year" and x["concept"].split(":")[-1] in names})
        found = any(abs(v - expected) < 0.5 for v, _ in hits)
        ok += found
        shown = ", ".join(f"{v:,.0f} (from FY{src} filing)" for v, src in hits) or "NOT FOUND"
        print(f"{'OK ' if found else 'XX '} {ticker} FY{fy} {concept}: expected {expected:,}  got {shown}")
    print(f"\n{ok}/{len(CHECKS)} answer-key numbers found exactly")


if __name__ == "__main__":
    main()
