"""Work out which companies and fiscal years a question is about.

detect_tickers("What did Nvidia say about China?")       ->  ["NVDA"]
detect_tickers("Compare AMD and Nvidia net income")      ->  ["AMD", "NVDA"]   (order of mention)
detect_tickers("What are the risks from tariffs?")       ->  []

An empty list means "don't filter": retrieval then searches every company.
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


def detect_tickers(question: str) -> list[str]:
    """Every company the question names, in the order they are first mentioned."""
    q = question.lower()
    first_seen = {}
    for ticker, names in ALIASES.items():
        for name in names:
            m = re.search(r"\b" + re.escape(name) + r"\b", q)
            if m and (ticker not in first_seen or m.start() < first_seen[ticker]):
                first_seen[ticker] = m.start()
    return sorted(first_seen, key=first_seen.get)


# "fiscal 2025", "fiscal year 2025", "fiscal years 2024 and 2026", "FY2025", "FY 25", "FY'25",
# plus 4-digit years chained right after one: "fiscal 2024 to 2026", "FY2023, 2024 and 2025".
YEAR = r"'?(\d{4}|\d{2})\b"
FY_Q_RE = re.compile(
    r"\b(?:fiscal(?:\s+years?)?|fys?)\s*" + YEAR
    + r"((?:\s*(?:,|and|to|through|-|–)\s*(?:(?:fy|fiscal)\s*'?(?:\d{4}|\d{2})|\d{4})\b)*)",
    re.IGNORECASE,
)
CHAINED_RE = re.compile(r"(\d{4}|\d{2})\b")


def _to_year(y: str) -> int:
    return int(y) if len(y) == 4 else 2000 + int(y)


def detect_fiscal_years(question: str) -> list[int]:
    """Every fiscal year the question names, in order, no duplicates.

    'fiscal 2026'                        -> [2026]
    'from fiscal 2024 to fiscal 2026'    -> [2024, 2026]
    'fiscal years 2024 and 2025'         -> [2024, 2025]
    'revenue in 2025'                    -> []   (bare year: ambiguous, so no filter)

    An empty list means "don't filter": retrieve() then searches every year.
    """
    years = []
    for m in FY_Q_RE.finditer(question):
        for y in [m.group(1)] + CHAINED_RE.findall(m.group(2)):
            year = _to_year(y)
            if year not in years:
                years.append(year)
    return years
