"""Work out which company a question is about.

detect_ticker("What did Nvidia say about China?")  ->  "NVDA"
detect_ticker("Compare AMD and Intel margins")     ->  None   (two companies)
detect_ticker("What are the risks from tariffs?")  ->  None   (no company)

None means "don't filter": retrieve() then searches every company.
"""

import re

ALIASES = {
    "NVDA": ["nvidia", "nvda"],
    "AMD":  ["amd", "advanced micro devices"],
    "INTC": ["intel", "intc"],
    "MU":   ["micron", "mu"],
    "AVGO": ["broadcom", "avgo"],
    "QCOM": ["qualcomm", "qcom"],
    "MRVL": ["marvell", "mrvl"],
}


def detect_ticker(question: str) -> str | None:
    q = question.lower()
    found = set()
    for ticker, names in ALIASES.items():
        for name in names:
            if re.search(r"\b" + re.escape(name) + r"\b", q):
                found.add(ticker)
                break
    if len(found) == 1:
        return found.pop()
    return None

FY_Q_RE = re.compile(r"\b(?:fiscal(?:\s+year)?|fy)\s*'?(\d{4}|\d{2})\b", re.IGNORECASE)

def detect_fiscal_year(question: str) -> int | None:
    """'fiscal 2025', 'fiscal year 2025', 'FY2025', 'FY 2025', 'FY25' -> 2025.
    A bare '2025' returns None on purpose: it's ambiguous (calendar or fiscal?)."""
    m = FY_Q_RE.search(question)
    if not m:
        return None
    y = m.group(1)
    return int(y) if len(y) == 4 else 2000 + int(y)