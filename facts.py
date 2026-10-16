"""Phase 2, step 2: look up exact XBRL numbers for a question and hand them to the answer model.

Design A (his choice, 16 Oct): a fixed word list, no LLM. A metric word in the question
("revenue", "R&D", "net income", ...) + the companies and years companies.py detected ->
the company-wide, full-year facts from data/facts.jsonl (written by xbrl.py).

They go into the prompt as extra numbered excerpts after the text passages, e.g.

    [11] AMD 10-K, fiscal 2025 -- XBRL financial data
    Research and development expenses (company-wide total), fiscal 2025 (year ended 2025-12-27): $8,091 million

so the model can cite them like any passage.

Deliberately NOT in the list (each has a definition trap the tag does not resolve):
  * share repurchases -- the cash-flow tag is cash PAID in the year ($40,086M for NVIDIA FY2026),
    the text reports shares BOUGHT ($40.4B): two true numbers that answer different questions;
  * gross margin %    -- not tagged; computing GrossProfit / revenue gives 39.8% where the filing says 40%;
  * debt              -- principal vs carrying amount vs fair value (FAILURES: Q3).

    uv run python facts.py "Which spent more on R&D in its latest fiscal year, NVIDIA or AMD?"
"""

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

FACTS = Path("data/facts.jsonl")

NAMES = {"NVDA": "NVIDIA", "AMD": "AMD", "INTC": "Intel", "MU": "Micron", "AVGO": "Broadcom",
         "QCOM": "Qualcomm", "MRVL": "Marvell"}

# (label shown to the model, words in the question, XBRL concepts in order of preference, kind)
METRICS = [
    ("Total revenue (company-wide, all segments combined)", r"\brevenues?\b|\bnet sales\b",
     ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax"], "usd"),
    ("Net income (company-wide)", r"\bnet income\b|\bnet earnings\b|\bnet (?:profit|loss)\b",
     ["NetIncomeLoss"], "usd"),
    ("Research and development expenses (company-wide total)", r"research and development|\bR\s*&\s*D\b",
     ["ResearchAndDevelopmentExpense"], "usd"),
    ("Gross profit (company-wide)", r"\bgross profit\b", ["GrossProfit"], "usd"),
    ("Operating income (company-wide)", r"\boperating income\b|\boperating (?:profit|loss)\b",
     ["OperatingIncomeLoss"], "usd"),
    ("Selling, general and administrative expenses (company-wide)", r"selling, general|\bSG\s*&\s*A\b",
     ["SellingGeneralAndAdministrativeExpense"], "usd"),
    ("Capital expenditures: purchases of property and equipment (company-wide)",
     r"capital expenditures?|\bcapex\b", ["PaymentsToAcquirePropertyPlantAndEquipment"], "usd"),
    ("Diluted earnings per share", r"earnings per share|\bEPS\b", ["EarningsPerShareDiluted"], "per_share"),
]

_by_key = None   # (ticker, fiscal_year, concept) -> list of facts


def _load():
    global _by_key
    if _by_key is None:
        _by_key = defaultdict(list)
        latest = {}
        for line in FACTS.open(encoding="utf-8"):
            x = json.loads(line)
            latest[x["ticker"]] = max(latest.get(x["ticker"], 0), x["filing_fiscal_year"])
            if x["dims"] or x["period"] != "year":          # company-wide, full-year facts only
                continue
            _by_key[(x["ticker"], x["fiscal_year"], x["concept"].split(":")[-1])].append(x)
        _by_key["_latest"] = latest
    return _by_key


def _fmt(value: float, kind: str) -> str:
    if kind == "per_share":
        return f"${value:,.2f} per share"
    millions = value / 1e6
    shown = f"{millions:,.0f}" if abs(millions - round(millions)) < 0.05 else f"{millions:,.1f}"
    return f"${shown} million"


def lookup(question: str, tickers: list[str], years: list[int], latest: bool) -> list[dict]:
    """Excerpt-shaped dicts (ticker, fiscal_year, period_end, item, text, id) for the prompt."""
    metrics = [m for m in METRICS if re.search(m[1], question, re.IGNORECASE)]
    if not metrics or not tickers or not FACTS.exists():
        return []
    ix = _load()
    out = []
    for ticker in tickers:
        for label, _, concepts, kind in metrics:
            for fy in (years or [ix["_latest"].get(ticker)]):
                for concept in concepts:                   # first concept the company uses wins
                    found = ix.get((ticker, fy, concept))
                    if not found:
                        continue
                    # same number is often in two filings (prior-year column); prefer its own year's 10-K
                    fact = min(found, key=lambda x: (x["filing_fiscal_year"] != fy, -x["filing_fiscal_year"]))
                    out.append({
                        "id": f"XBRL-{ticker}-{fy}-{concept}",
                        "ticker": ticker,
                        "fiscal_year": fy,
                        "period_end": fact["end"],
                        "item": "XBRL",
                        "text": f"{label}, fiscal {fy} (year ended {fact['end']}): {_fmt(fact['value'], kind)}",
                        "concept": fact["concept"],
                        "source_filing": fact["filing_period_end"],
                    })
                    break
    return out


if __name__ == "__main__":
    from companies import detect_fiscal_years, detect_latest, detect_tickers
    q = " ".join(sys.argv[1:]) or "Which spent more on R&D in its latest fiscal year, NVIDIA or AMD?"
    rows = lookup(q, detect_tickers(q), detect_fiscal_years(q), detect_latest(q))
    for r in rows:
        print(f"{NAMES.get(r['ticker'], r['ticker'])}: {r['text']}   [{r['concept']}, from the "
              f"{r['source_filing']} 10-K]")
    if not rows:
        print("no facts (no metric word, no company named, or data/facts.jsonl missing)")
