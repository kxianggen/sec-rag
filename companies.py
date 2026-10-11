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
