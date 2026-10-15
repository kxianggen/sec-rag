"""Compare two eval results files question by question.

    uv run python compare_runs.py results/golden30_t0.json results/exp3b_hybrid.json

For each question: did the retrieved chunks change, and did the judge's verdict change?
Changes WITHOUT a retrieval change are answer-generation noise (see FAILURES #31).
"""

import json
import sys
from pathlib import Path


def load(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return data["rows"] if isinstance(data, dict) else data


def main():
    if len(sys.argv) != 3:
        sys.exit("Usage: uv run python compare_runs.py OLD.json NEW.json")
    old, new = load(sys.argv[1]), load(sys.argv[2])
    same_retrieval = 0
    print(f"{'#':<4}{'retrieval':<12}{'verdict':<26}question")
    for a, b in zip(old, new):
        key = "chunk_ids" if "chunk_ids" in a and "chunk_ids" in b else "retrieved"
        same = a[key] == b[key]
        same_retrieval += same
        graded = a["verdict"] is not None and b["verdict"] is not None   # --no-llm runs have no verdicts
        if same and (not graded or a["verdict"] == b["verdict"]):
            continue
        if not graded:
            verdict = "-"
        else:
            verdict = a["verdict"] if a["verdict"] == b["verdict"] else f"{a['verdict']} -> {b['verdict']}"
        print(f"{a['n']:<4}{'same' if same else 'CHANGED':<12}{str(verdict):<26}{a['question'][:60]}")
    print(f"\nRetrieval identical on {same_retrieval}/{len(old)} questions"
          f" (compared by {'chunk id' if key == 'chunk_ids' else 'section label only'}).")


if __name__ == "__main__":
    main()
