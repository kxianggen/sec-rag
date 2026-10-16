"""Phase 1b part 2: LLM query rewriting -- one focused search per company x fiscal year.

The question "Which spent more on R&D in its latest fiscal year, NVIDIA or AMD?" is a
comparison sentence; searched as-is it matches chunks ABOUT R&D, not the row with the amount.
One small LLM call turns it into one short search per target, in the words a 10-K uses:

    NVIDIA (latest 10-K)  ->  "NVIDIA research and development expenses"
    AMD    (latest 10-K)  ->  "AMD research and development expenses"

Who decides what:
  * companies and years come from companies.py (rules, as before) -- the LLM cannot add or
    drop a company or a year, so the filters stay predictable;
  * the LLM only writes the search TEXT for each target;
  * if the call fails or the reply is malformed, every target falls back to the original
    question (with the abbreviation list from retrieve.expand_query) -- still split per target.
  * use_llm=False (eval.py --split-only) does that on purpose: the split WITHOUT the LLM text,
    to tell which half of this change did the work if the result is unclear.

The answer prompt still gets the ORIGINAL question; rewriting only changes what is searched.

    uv run python rewrite.py "Which had more employees, Micron or Marvell?"   # see the plan
"""

import json
import re
import sys

from ask import call_llm
from companies import detect_fiscal_years, detect_latest, detect_tickers
from retrieve import expand_query

NAMES = {"NVDA": "NVIDIA", "AMD": "AMD", "INTC": "Intel", "MU": "Micron", "AVGO": "Broadcom",
         "QCOM": "Qualcomm", "MRVL": "Marvell"}

PROMPT = """You write search queries for a search engine over companies' annual reports (SEC 10-K filings).
Write ONE query for EACH target below, in the same order. Each query must:
- name the target's company (if it has one),
- ask for the one fact THAT target must supply to answer the question,
- use the words a 10-K uses (e.g. "research and development expenses", "net revenue",
  "net income", "number of employees", "gross margin"), with abbreviations written out,
- be short: 4 to 12 words, keywords rather than a sentence, no years.
Do not answer the question. Do not mention companies other than the target's.

Example
Question: Which had more employees at the end of its latest fiscal year, Micron or Marvell?
Targets:
1. Micron, latest 10-K
2. Marvell, latest 10-K
Reply: {{"queries": ["Micron number of employees", "Marvell number of employees"]}}

Question: {question}
Targets:
{targets}
Reply with JSON only."""


def _describe(ticker, year, latest) -> str:
    who = NAMES.get(ticker, ticker) if ticker else "any company"
    when = f"fiscal {year} 10-K" if year else ("latest 10-K" if latest else "any year")
    return f"{who}, {when}"


def plan_searches(question: str, tickers: list[str], years: list[int], latest: bool,
                  use_llm: bool = True) -> dict:
    """Returns {"searches": [{"ticker", "fiscal_years", "query"}, ...], "rewritten": bool}."""
    targets = [(t, y) for t in (tickers or [None]) for y in (years or [None])]
    queries = None
    try:
        if not use_llm:
            raise RuntimeError("split only")
        reply = call_llm(PROMPT.format(
            question=question,
            targets="\n".join(f"{i}. {_describe(t, y, latest)}" for i, (t, y) in enumerate(targets, 1))),
            temperature=0)
        m = re.search(r"\{.*\}", reply or "", re.DOTALL)
        got = json.loads(m.group(0))["queries"] if m else None
        if isinstance(got, list) and len(got) == len(targets) and all(isinstance(q, str) and q.strip() for q in got):
            queries = got
    except Exception:          # network error, bad JSON, ... -> fall back, never crash the question
        queries = None
    rewritten = queries is not None
    if not rewritten:
        queries = [question] * len(targets)
    return {"rewritten": rewritten,
            "searches": [{"ticker": t, "fiscal_years": [y] if y else None, "query": expand_query(q)}
                         for (t, y), q in zip(targets, queries)]}


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    q = " ".join(sys.argv[1:]) or "Which spent more on R&D in its latest fiscal year, NVIDIA or AMD?"
    plan = plan_searches(q, detect_tickers(q), detect_fiscal_years(q), detect_latest(q))
    print("rewritten by the LLM:" if plan["rewritten"] else "FALLBACK (original question):")
    for s in plan["searches"]:
        print(f"  {s['ticker'] or 'all'} {s['fiscal_years'] or ''}: {s['query']}")
