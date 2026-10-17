"""Spec for companies.py: which companies and fiscal years a question is about.

    uv run python test_companies.py      (also run by GitHub Actions on every push)

These detectors decide the search filters, so a regression here silently changes every answer.
"""

from companies import detect_fiscal_years, detect_latest, detect_tickers

CASES = [
    ("one company, any case", detect_tickers("What did Nvidia say about China?"), ["NVDA"]),
    ("two companies, order of mention", detect_tickers("Compare AMD and Nvidia net income"), ["AMD", "NVDA"]),
    ("no company -> no filter", detect_tickers("What are the risks from tariffs?"), []),
    ("Intel still recognised (descoped -> clean refusal)", detect_tickers("Tell me about Intel"), ["INTC"]),
    ("from fiscal X to fiscal Y", detect_fiscal_years("How did NVIDIA's revenue change from fiscal 2024 to fiscal 2026?"), [2024, 2026]),
    ("FY list", detect_fiscal_years("FY2023, 2024 and 2025 revenue for Micron"), [2023, 2024, 2025]),
    ("two-digit FY", detect_fiscal_years("Broadcom FY25 R&D"), [2025]),
    ("bare calendar year is ignored", detect_fiscal_years("What was Qualcomm's revenue in 2025?"), []),
    ("future year kept (filters then match nothing)", detect_fiscal_years("What will NVIDIA's revenue be in fiscal 2028?"), [2028]),
    ("latest", detect_latest("Which reported higher net income in its latest fiscal year, AMD or NVIDIA?"), True),
    ("not latest", detect_latest("What was NVIDIA's revenue in fiscal 2026?"), False),
]

failed = 0
for name, got, want in CASES:
    ok = got == want
    failed += not ok
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"   (got {got!r}, want {want!r})"))
print(f"\n{len(CASES) - failed}/{len(CASES)} passed")
raise SystemExit(1 if failed else 0)
