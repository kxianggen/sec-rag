"""Tests for the two T13 functions you add to metrics.py.  Run:  uv run python test_scoring.py

Read the cases first - they are the spec.
"""

from metrics import agreement, verdict_score

CASES = [
    # verdict_score: turn the judge's word into a number we can average
    ("verdict_score: correct", verdict_score("correct"), 1.0),
    ("verdict_score: partial", verdict_score("partial"), 0.5),
    ("verdict_score: incorrect", verdict_score("incorrect"), 0.0),
    ("verdict_score: anything else -> None (left out of averages)", verdict_score("unparsed"), None),
    # agreement: on the questions BOTH you and the judge graded, what fraction match?
    ("agreement: all match", agreement({1: "correct", 2: "partial"}, {1: "correct", 2: "partial"}), 1.0),
    ("agreement: 1 of 2 match", agreement({1: "correct", 2: "partial"}, {1: "correct", 2: "incorrect"}), 0.5),
    ("agreement: only shared questions count",
     agreement({1: "correct", 6: "incorrect"}, {1: "correct", 2: "partial", 3: "correct", 6: "incorrect"}), 1.0),
    ("agreement: 0 of 3 match",
     agreement({1: "correct", 2: "correct", 3: "correct"}, {1: "partial", 2: "incorrect", 3: "partial"}), 0.0),
    ("agreement: no shared questions -> None", agreement({1: "correct"}, {2: "correct"}), None),
]

failed = 0
for name, got, want in CASES:
    ok = got == want
    failed += not ok
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"   (got {got!r}, want {want!r})"))
print(f"\n{len(CASES) - failed}/{len(CASES)} passed")
raise SystemExit(1 if failed else 0)
