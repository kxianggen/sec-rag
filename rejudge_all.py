"""Re-grade every saved run with rubric v2.1, so all numbers use the same ruler.

    uv run python rejudge_all.py            # ~180 judge calls with gpt-4o, about 50 US cents

Re-uses the ANSWERS saved in each results file (the system is not re-run), so any change in
score here comes from the rubric alone. Writes results/v21/<run>.json and prints a table.
"""

import json
from pathlib import Path

from eval import rejudge

RUNS = [
    ("golden30_t0.json",        "Baseline: dense"),
    ("exp3a_cap3.json",         "3a: section cap"),
    ("exp3b_hybrid.json",       "3b: hybrid (adopted)"),
    ("exp3c_hybrid_cap3.json",  "3c: hybrid + cap"),
    ("step4_prompt2.json",      "Step 4: prompt rule 5"),
    ("exp4_tables.json",        "Exp 4: table rows"),
]
OUT = Path("results/v21")


def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    print(f"{'run':<24}{'v1 score':>9}{'v2.1':>7}{'CRAG':>7}{'wrong':>7}")
    for name, label in RUNS:
        src = Path("results") / name
        if not src.exists():
            print(f"{label:<24}  (missing {src})")
            continue
        old = json.loads(src.read_text(encoding="utf-8"))
        v1 = mean(r.get("answer_score") for r in old["rows"])
        rows = rejudge(src, "v2.1")
        (OUT / name).write_text(json.dumps({**old, "rubric": "v2.1", "rows": rows}, indent=1, ensure_ascii=False),
                                encoding="utf-8")
        v2 = mean(r["answer_score"] for r in rows)
        crag = mean(r["crag"] for r in rows)
        wrong = sum(r["crag"] == -1.0 for r in rows)
        print(f"{label:<24}{v1:>9.2f}{v2:>7.2f}{crag:>+7.2f}{wrong:>7}")


if __name__ == "__main__":
    main()
