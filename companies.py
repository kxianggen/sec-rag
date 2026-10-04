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