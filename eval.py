"""Score the pipeline against golden.jsonl.

    uv run python eval.py                  # retrieval + answers + judge (24 LLM calls, ~2 US cents)
    uv run python eval.py --no-llm         # retrieval only, free
    uv run python eval.py --out results/baseline.json
    uv run python eval.py --rejudge results/t12.json   # judge answers already saved (12 calls)

Uses YOUR scoring functions from metrics.py. Answer correctness is graded by an
LLM judge (judge.py) and checked against your own labels in human_labels.json.
"""

import argparse
import json
from collections import defaultdict
from pathlib import Path

from ask import build_prompt, call_llm
from companies import detect_fiscal_years, detect_tickers
from judge import judge
from metrics import agreement, is_refusal, refusal_correct, source_recall, verdict_score
from retrieve import retrieve_multi

GOLDEN = Path("golden.jsonl")
HUMAN = Path("human_labels.json")


def run(k: int, use_llm: bool) -> list[dict]:
    rows = []
    for n, line in enumerate(GOLDEN.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        g = json.loads(line)
        tickers = detect_tickers(g["question"])
        years = detect_fiscal_years(g["question"])
        chunks = retrieve_multi(g["question"], k=k, tickers=tickers, fiscal_years=years)
        answer = call_llm(build_prompt(g["question"], chunks)) if use_llm else None
        graded = judge(g["question"], g["answer"], answer) if answer is not None else None
        rows.append({
            "n": n,
            "type": g["type"],
            "question": g["question"],
            "filters": {"tickers": tickers, "fiscal_years": years},
            "retrieved": [f"{c['ticker']} {c['period_end']} Item {c['item']}" for c in chunks],
            "recall": source_recall(g["sources"], chunks),
            "answer": answer,
            "refused": is_refusal(answer) if answer is not None else None,
            "refusal_ok": refusal_correct(answer, g["answer"]) if answer is not None else None,
            "verdict": graded["verdict"] if graded else None,
            "judge_reason": graded["reason"] if graded else None,
            "answer_score": verdict_score(graded["verdict"]) if graded else None,
        })
    return rows


def rejudge(path: Path) -> list[dict]:
    """Grade the answers saved in an earlier run, so the judge sees EXACTLY the answers
    you labelled by hand (a fresh run would generate new, slightly different answers)."""
    golden = [json.loads(l) for l in GOLDEN.read_text(encoding="utf-8").splitlines() if l.strip()]
    rows = json.loads(path.read_text(encoding="utf-8"))["rows"]
    for r in rows:
        g = golden[r["n"] - 1]
        graded = judge(g["question"], g["answer"], r["answer"]) if r.get("answer") is not None else None
        r["verdict"] = graded["verdict"] if graded else None
        r["judge_reason"] = graded["reason"] if graded else None
        r["answer_score"] = verdict_score(graded["verdict"]) if graded else None
    return rows


def fmt(x) -> str:
    if x is None:
        return "  -  "
    if isinstance(x, bool):
        return " yes " if x else " NO  "
    return f"{x:5.2f}"


def report(rows: list[dict], k: int) -> None:
    print(f"\n#   type           recall@{k}  refusal ok  verdict     question")
    for r in rows:
        v = r.get("verdict") or "-"
        print(f"{r['n']:<3} {r['type']:<14} {fmt(r['recall'])}      {fmt(r['refusal_ok'])}      {v:<11} {r['question'][:52]}")

    by_type = defaultdict(list)
    for r in rows:
        by_type[r["type"]].append(r)
    print(f"\ntype           n   mean recall@{k}   refusal ok   answer score")
    for t, rs in list(by_type.items()) + [("ALL", rows)]:
        recalls = [r["recall"] for r in rs if r["recall"] is not None]
        oks = [r["refusal_ok"] for r in rs if r["refusal_ok"] is not None]
        scores = [r.get("answer_score") for r in rs if r.get("answer_score") is not None]
        mean = f"{sum(recalls) / len(recalls):.2f}" if recalls else "  -"
        ok = f"{sum(oks)}/{len(oks)}" if oks else "-"
        sc = f"{sum(scores) / len(scores):.2f}" if scores else "  -"
        print(f"{t:<14} {len(rs):<3} {mean:>8}          {ok:>5}        {sc:>5}")

    if HUMAN.exists() and any(r.get("verdict") for r in rows):
        human = {int(n): v for n, v in json.loads(HUMAN.read_text(encoding="utf-8")).items() if n.isdigit()}
        judged = {r["n"]: r["verdict"] for r in rows if r.get("verdict")}
        agree = agreement(human, judged)
        print(f"\nJudge vs your labels: {agree:.2f} agreement on {len(human)} labelled questions" if agree is not None
              else "\nJudge vs your labels: no overlap")
        for n in sorted(human):
            if n in judged and judged[n] != human[n]:
                print(f"  Q{n}: you said {human[n]}, judge said {judged[n]}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--k", type=int, default=5)
    p.add_argument("--no-llm", action="store_true")
    p.add_argument("--out", type=Path)
    p.add_argument("--rejudge", type=Path, help="grade the answers saved in this results file")
    a = p.parse_args()

    rows = rejudge(a.rejudge) if a.rejudge else run(a.k, not a.no_llm)
    report(rows, a.k)
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps({"k": a.k, "rows": rows}, indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"\nSaved {a.out}")


if __name__ == "__main__":
    main()
