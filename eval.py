"""Score the pipeline against golden.jsonl.

    uv run python eval.py                  # retrieval + answers + judge (24 LLM calls, ~2 US cents)
    uv run python eval.py --no-llm         # retrieval only, free
    uv run python eval.py --out results/baseline.json
    uv run python eval.py --rejudge results/t12.json   # judge answers already saved (12 calls)
    uv run python eval.py --rejudge results/exp3b_hybrid.json --labels human_labels_30.json
    uv run python eval.py --index fixed --out results/exp1_fixed.json   # Experiment 1
    uv run python eval.py --store pgvector --out results/pg_hybrid.json  # search in Supabase
    uv run python eval.py --out results/p1b_expand.json                  # Phase 1b: R&D expansion (default on)
    uv run python eval.py --rewrite 1 --out results/p1b_rewrite.json     # Phase 1b part 2 v1 (per company x year)
    uv run python eval.py --rewrite 2 --out results/p1b_rewrite2.json    # v2 (per company, keeps key words)
    uv run python eval.py --prompt 3 --out results/p1b_prompt3.json      # answer prompt + exact-number rule
    uv run python eval.py --out results/p2_facts.json                    # Phase 2: + exact XBRL figures (default on)

Uses YOUR scoring functions from metrics.py. Answer correctness is graded by an
LLM judge (judge.py) and checked against your own labels in human_labels.json.
"""

import argparse
import json
from collections import defaultdict
from pathlib import Path

from ask import build_prompt, call_llm
from companies import detect_fiscal_years, detect_latest, detect_tickers
from judge import CATEGORY_VERDICT, JUDGE_MODEL, judge
from metrics import agreement, is_refusal, refusal_correct, source_recall, verdict_score
from retrieve import retrieve_multi, retrieve_planned, set_index, set_store
from rewrite import plan_searches
from facts import lookup as lookup_facts

GOLDEN = Path("golden.jsonl")
HUMAN = Path("human_labels.json")


def run(k: int, use_llm: bool, mode: str = "hybrid", max_per_section: int | None = None,
        prompt_version: int = 1, rubric: str = "v2.1", expand: bool = True,
        rewrite: int | None = None, split_only: bool = False, facts: bool = True) -> list[dict]:
    rows = []
    for n, line in enumerate(GOLDEN.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        g = json.loads(line)
        tickers = detect_tickers(g["question"])
        years = detect_fiscal_years(g["question"])
        latest = detect_latest(g["question"])
        plan = None
        if rewrite:      # Phase 1b part 2: one focused search per company x year, text written by an LLM
            plan = plan_searches(g["question"], tickers, years, latest, use_llm=not split_only, version=rewrite)
            chunks = retrieve_planned(plan["searches"], k=k, latest=latest, mode=mode,
                                      max_per_section=max_per_section)
        else:
            chunks = retrieve_multi(g["question"], k=k, tickers=tickers, fiscal_years=years, latest=latest,
                                    mode=mode, max_per_section=max_per_section, expand=expand)
        xbrl = lookup_facts(g["question"], tickers, years, latest) if facts else []
        answer = call_llm(build_prompt(g["question"], chunks + xbrl, prompt_version), temperature=0) if use_llm else None
        graded = judge(g["question"], g["answer"], answer, rubric, g.get("required")) if answer is not None else None
        rows.append({
            "n": n,
            "type": g["type"],
            "question": g["question"],
            "filters": {"tickers": tickers, "fiscal_years": years, "latest": latest},
            "searches": plan["searches"] if plan else None,
            "facts": [f"{x['ticker']} {x['text']}" for x in xbrl] if facts else None,
            "rewritten": plan["rewritten"] if plan else None,
            "retrieved": [f"{c['ticker']} {c['period_end']} Item {c['item']}" for c in chunks],
            "chunk_ids": [c["id"] for c in chunks],
            "chunk_texts": [c["text"] for c in chunks],
            "recall": source_recall(g["sources"], chunks),
            "answer": answer,
            "refused": is_refusal(answer) if answer is not None else None,
            "refusal_ok": refusal_correct(answer, g["answer"]) if answer is not None else None,
            "verdict": graded["verdict"] if graded else None,
            "category": graded.get("category") if graded else None,
            "judge_reason": graded["reason"] if graded else None,
            "answer_score": verdict_score(graded["verdict"]) if graded else None,
            "crag": crag_score(graded["verdict"], answer) if graded else None,
        })
    return rows


def crag_score(verdict: str, answer: str) -> float | None:
    """CRAG-style score: correct +1, partial +0.5, refusing 0, a WRONG answer -1.
    A made-up answer costs more than saying "Not in the filings." (rubric v2, rule 5)."""
    if verdict == "correct":
        return 1.0
    if verdict == "partial":
        return 0.5
    if verdict == "incorrect":
        return 0.0 if is_refusal(answer) else -1.0
    return None


def rejudge(path: Path, rubric: str = "v2.1") -> list[dict]:
    """Grade the answers saved in an earlier run, so the judge sees EXACTLY the answers
    you labelled by hand (a fresh run would generate new, slightly different answers)."""
    golden = [json.loads(l) for l in GOLDEN.read_text(encoding="utf-8").splitlines() if l.strip()]
    rows = json.loads(path.read_text(encoding="utf-8"))["rows"]
    for r in rows:
        g = golden[r["n"] - 1]
        graded = judge(g["question"], g["answer"], r["answer"], rubric, g.get("required")) if r.get("answer") is not None else None
        r["verdict"] = graded["verdict"] if graded else None
        r["category"] = graded.get("category") if graded else None
        r["judge_reason"] = graded["reason"] if graded else None
        r["answer_score"] = verdict_score(graded["verdict"]) if graded else None
        r["crag"] = crag_score(graded["verdict"], r["answer"]) if graded else None
    return rows


def fmt(x) -> str:
    if x is None:
        return "  -  "
    if isinstance(x, bool):
        return " yes " if x else " NO  "
    return f"{x:5.2f}"


def report(rows: list[dict], k: int, rejudged: bool = False, labels: Path = HUMAN) -> None:
    print(f"\n#   type           recall@{k}  refusal ok  verdict     question")
    for r in rows:
        v = r.get("verdict") or "-"
        print(f"{r['n']:<3} {r['type']:<14} {fmt(r['recall'])}      {fmt(r['refusal_ok'])}      {v:<11} {r['question'][:52]}")

    by_type = defaultdict(list)
    for r in rows:
        by_type[r["type"]].append(r)
    print(f"\ntype           n   mean recall@{k}   refusal ok   answer score   CRAG")
    for t, rs in list(by_type.items()) + [("ALL", rows)]:
        recalls = [r["recall"] for r in rs if r["recall"] is not None]
        oks = [r["refusal_ok"] for r in rs if r["refusal_ok"] is not None]
        scores = [r.get("answer_score") for r in rs if r.get("answer_score") is not None]
        mean = f"{sum(recalls) / len(recalls):.2f}" if recalls else "  -"
        ok = f"{sum(oks)}/{len(oks)}" if oks else "-"
        sc = f"{sum(scores) / len(scores):.2f}" if scores else "  -"
        crags = [r.get("crag") for r in rs if r.get("crag") is not None]
        cr = f"{sum(crags) / len(crags):+.2f}" if crags else "  -"
        print(f"{t:<14} {len(rs):<3} {mean:>8}          {ok:>5}        {sc:>5}      {cr:>5}")
    wrong = [r["n"] for r in rows if r.get("crag") == -1.0]
    if any(r.get("crag") is not None for r in rows):
        print(f"\nWrong answers (CRAG -1, not refusals): {len(wrong)}  {wrong}")

    # Labels are made on ONE set of saved answers, so the comparison is only valid when the
    # judge grades those same answers: --rejudge <that file> --labels <your labels for it>.
    #   human_labels.json     -> results/t12.json          (8 labels, original questions)
    #   human_labels_30.json  -> results/exp3b_hybrid.json (10 labels, new questions)
    #   human_labels_v2_t12.json / human_labels_v2_30.json -> same answers, re-labelled A-E (rubric v2)
    if rejudged and labels.exists() and any(r.get("verdict") for r in rows):
        raw = json.loads(labels.read_text(encoding="utf-8"))
        # labels may be verdicts ("partial") or rubric-v2 categories ("A".."E")
        human = {int(n): CATEGORY_VERDICT.get(v.upper(), v) for n, v in raw.items()
                 if n.isdigit() and (v in ("correct", "partial", "incorrect") or v.upper() in CATEGORY_VERDICT)}
        judged = {r["n"]: r["verdict"] for r in rows if r.get("verdict")}
        agree = agreement(human, judged)
        print(f"\nJudge vs your labels: {agree:.2f} agreement on {len(human)} labelled questions" if agree is not None
              else "\nJudge vs your labels: no overlap")
        for n in sorted(human):
            if n in judged and judged[n] != human[n]:
                print(f"  Q{n}: you said {human[n]}, judge said {judged[n]}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--k", type=int, default=10)   # Experiment 2: k=10 chosen
    p.add_argument("--no-llm", action="store_true")
    p.add_argument("--out", type=Path)
    p.add_argument("--rejudge", type=Path, help="grade the answers saved in this results file")
    p.add_argument("--labels", type=Path, default=HUMAN, help="your hand labels for the --rejudge file")
    p.add_argument("--rubric", default="v2.1", choices=["v1", "v2", "v2.1"],
                   help="judge rubric: v2.1 (default) grades against each question's required facts")
    p.add_argument("--index", default="final",
                   help='"final" (default: tables + headers, Intel removed), "tables_hdr" (16 Oct runs), '
                        '"main" (original paragraph chunks), "fixed", ...')
    p.add_argument("--no-expand", action="store_true",
                   help="turn OFF abbreviation expansion (default on since Phase 1b; off reproduces earlier runs)")
    p.add_argument("--rewrite", type=int, choices=[1, 2], default=None,
                   help="Phase 1b part 2: LLM writes one focused search per target (+1 LLM call per question). "
                        "1 = per company x year (16 Oct: 0.68, 5 wrong, not adopted), 2 = per company")
    p.add_argument("--no-facts", action="store_true",
                   help="turn OFF the exact XBRL figures (default on since Phase 2: 0.67 -> 0.77); off reproduces earlier runs")
    p.add_argument("--split-only", action="store_true",
                   help="with --rewrite: split per company x year but search the original question (no LLM)")
    p.add_argument("--store", default="numpy", choices=["numpy", "pgvector"], help="where vectors are searched")
    p.add_argument("--mode", default="hybrid", choices=["dense", "hybrid"], help="Experiment 3b: hybrid won (0.65 vs 0.55)")
    p.add_argument("--max-per-section", type=int, default=None, help="Experiment 3a, e.g. 3 (off by default: lost answers)")
    p.add_argument("--prompt", type=int, default=1, choices=[1, 2, 3],
                   help="1 = T07 rules (default), 2 = + company-total rule (step 4: 0.63 vs 0.65, not adopted), "
                        "3 = + copy numbers exactly (Phase 1b)")
    a = p.parse_args()
    set_index(a.index)
    set_store(a.store)

    rows = (rejudge(a.rejudge, a.rubric) if a.rejudge
            else run(a.k, not a.no_llm, a.mode, a.max_per_section, a.prompt, a.rubric,
                     not a.no_expand, a.rewrite, a.split_only, not a.no_facts))
    report(rows, a.k, rejudged=bool(a.rejudge), labels=a.labels)
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps({"k": a.k, "index": a.index, "store": a.store, "mode": a.mode,
                                          "max_per_section": a.max_per_section, "expand": not a.no_expand, "rewrite": a.rewrite, "split_only": a.split_only, "facts": not a.no_facts,
                                          "prompt": a.prompt, "rubric": a.rubric,
                                          "judge_model": JUDGE_MODEL if a.rubric == "v2.1" else "answer model", "rows": rows}, indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"\nSaved {a.out}")


if __name__ == "__main__":
    main()
