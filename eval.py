"""Score the pipeline against golden.jsonl.

    uv run python eval.py                  # retrieval + answers (12 LLM calls, about 1 US cent)
    uv run python eval.py --no-llm         # retrieval only, free
    uv run python eval.py --out results/baseline.json

Uses YOUR scoring functions from metrics.py. Answer correctness for facts and
narratives is not scored yet (that needs Ragas / an LLM judge); answers are saved
so you can read them.
"""

import argparse
import json
from collections import defaultdict
from pathlib import Path

from ask import build_prompt, call_llm
from companies import detect_fiscal_year, detect_ticker
from metrics import is_refusal, refusal_correct, source_recall
from retrieve import retrieve

GOLDEN = Path("golden.jsonl")


def run(k: int, use_llm: bool) -> list[dict]:
    rows = []
    for n, line in enumerate(GOLDEN.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        g = json.loads(line)
        ticker = detect_ticker(g["question"])
        fy = detect_fiscal_year(g["question"])
        chunks = retrieve(g["question"], k=k, ticker=ticker, fiscal_year=fy)
        answer = call_llm(build_prompt(g["question"], chunks)) if use_llm else None
        rows.append({
            "n": n,
            "type": g["type"],
            "question": g["question"],
            "filters": {"ticker": ticker, "fiscal_year": fy},
            "retrieved": [f"{c['ticker']} {c['period_end']} Item {c['item']}" for c in chunks],
            "recall": source_recall(g["sources"], chunks),
            "answer": answer,
            "refused": is_refusal(answer) if answer is not None else None,
            "refusal_ok": refusal_correct(answer, g["answer"]) if answer is not None else None,
        })
    return rows


def fmt(x) -> str:
    if x is None:
        return "  -  "
    if isinstance(x, bool):
        return " yes " if x else " NO  "
    return f"{x:5.2f}"


def report(rows: list[dict], k: int) -> None:
    print(f"\n#   type           recall@{k}  refusal ok  question")
    for r in rows:
        print(f"{r['n']:<3} {r['type']:<14} {fmt(r['recall'])}      {fmt(r['refusal_ok'])}      {r['question'][:60]}")

    by_type = defaultdict(list)
    for r in rows:
        by_type[r["type"]].append(r)
    print(f"\ntype           n   mean recall@{k}   refusal ok")
    for t, rs in list(by_type.items()) + [("ALL", rows)]:
        recalls = [r["recall"] for r in rs if r["recall"] is not None]
        oks = [r["refusal_ok"] for r in rs if r["refusal_ok"] is not None]
        mean = f"{sum(recalls) / len(recalls):.2f}" if recalls else "  -"
        ok = f"{sum(oks)}/{len(oks)}" if oks else "-"
        print(f"{t:<14} {len(rs):<3} {mean:>8}          {ok:>5}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--k", type=int, default=5)
    p.add_argument("--no-llm", action="store_true")
    p.add_argument("--out", type=Path)
    a = p.parse_args()

    rows = run(a.k, not a.no_llm)
    report(rows, a.k)
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps({"k": a.k, "rows": rows}, indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"\nSaved {a.out}")


if __name__ == "__main__":
    main()
