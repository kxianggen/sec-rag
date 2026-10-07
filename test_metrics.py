"""Tests for metrics.py. Run:  uv run python test_metrics.py

Each line checks one behaviour. If one fails, you'll see which, and what it got.
Read the cases BEFORE writing metrics.py: they are the spec.
"""

from metrics import is_refusal, source_found, source_recall, refusal_correct

AVGO = {"ticker": "AVGO", "period_end": "2025-11-02", "item": "7"}
QCOM = {"ticker": "QCOM", "period_end": "2025-09-28", "item": "16"}


def chunk(ticker, period_end, item):
    return {"ticker": ticker, "period_end": period_end, "item": item, "text": "..."}


chunks_qcom_only = [chunk("QCOM", "2025-09-28", "16"), chunk("QCOM", "2025-09-28", "1A")]
chunks_both = [chunk("QCOM", "2025-09-28", "16"), chunk("AVGO", "2025-11-02", "7")]
chunks_wrong_year = [chunk("AVGO", "2024-11-03", "7")]
chunks_wrong_item = [chunk("AVGO", "2025-11-02", "1A")]

CASES = [
    # is_refusal
    ("is_refusal: exact phrase", is_refusal("Not in the filings."), True),
    ("is_refusal: with spaces around", is_refusal("  Not in the filings.\n"), True),
    ("is_refusal: a real answer", is_refusal("NVIDIA's revenue was $215.9 billion [1]."), False),
    # source_found
    ("source_found: same ticker, period, item", source_found(QCOM, chunks_qcom_only), True),
    ("source_found: company missing", source_found(AVGO, chunks_qcom_only), False),
    ("source_found: right company, wrong year", source_found(AVGO, chunks_wrong_year), False),
    ("source_found: right filing, wrong item", source_found(AVGO, chunks_wrong_item), False),
    # source_recall
    ("source_recall: 1 of 2 sources found", source_recall([AVGO, QCOM], chunks_qcom_only), 0.5),
    ("source_recall: 2 of 2 sources found", source_recall([AVGO, QCOM], chunks_both), 1.0),
    ("source_recall: 0 of 1 found", source_recall([AVGO], chunks_qcom_only), 0.0),
    ("source_recall: no sources -> None", source_recall([], chunks_both), None),
    # refusal_correct
    ("refusal_correct: unanswerable, refused", refusal_correct("Not in the filings.", "Not in the filings."), True),
    ("refusal_correct: unanswerable, answered", refusal_correct("$70 billion [1]", "Not in the filings."), False),
    ("refusal_correct: answerable, answered", refusal_correct("$215.9 billion [1]", "$215.9 billion"), True),
    ("refusal_correct: answerable, refused", refusal_correct("Not in the filings.", "$215.9 billion"), False),
]

failed = 0
for name, got, want in CASES:
    ok = got == want
    failed += not ok
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"   (got {got!r}, want {want!r})"))
print(f"\n{len(CASES) - failed}/{len(CASES)} passed")
