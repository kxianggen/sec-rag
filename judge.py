"""LLM-as-judge: is the system's answer correct, compared with the golden answer?

    from judge import judge
    judge(question, golden_answer, system_answer)
    -> {"verdict": "correct" | "partial" | "incorrect", "reason": "..."}

The rules (RUBRIC) were decided in T13; the judge is only as good as they are.
Check it against your own labels (human_labels.json) before trusting its numbers.
"""

import json
import re

from ask import call_llm

VERDICTS = ("correct", "partial", "incorrect")

RUBRIC = """\
- correct: every number in the answer matches the golden answer for the right company and
  fiscal year, quoted as the filing states it. Different formatting of the SAME figure is fine
  ($67,120 million = $67.1 billion). For a "which is higher" question, the conclusion must be
  right AND the supporting numbers must match. For narrative questions, the answer covers the
  golden key points and adds nothing that contradicts them.
- partial: right company, year and conclusion, but a number is only approximately right
  (e.g. computed or rounded instead of quoted: 39.8% vs 40%) or uses a different but
  reasonable definition (e.g. balance-sheet debt instead of debt principal); or a narrative
  answer covers only some of the key points.
- incorrect: any invented or unsupported number, the wrong fiscal year, the wrong company,
  the wrong conclusion, or a statement that contradicts the golden answer — even if the final
  conclusion happens to be right.
- refusals: if the golden answer is "Not in the filings." then a refusal is correct and any
  attempted answer is incorrect. If the golden answer is a real answer, a refusal is incorrect."""

PROMPT = """You are grading an answer from a question-answering system about SEC 10-K filings.
Compare the SYSTEM ANSWER with the GOLDEN ANSWER (the verified correct answer) using these rules:

{rubric}

QUESTION: {question}

GOLDEN ANSWER: {golden}

SYSTEM ANSWER: {answer}

Reply with JSON only, no other text:
{{"verdict": "correct" | "partial" | "incorrect", "reason": "<one sentence>"}}"""


def judge(question: str, golden: str, answer: str) -> dict:
    raw = call_llm(PROMPT.format(rubric=RUBRIC, question=question, golden=golden, answer=answer)) or ""
    m = re.search(r"\{.*\}", raw, re.DOTALL)          # tolerate ```json fences or stray text
    try:
        out = json.loads(m.group(0)) if m else {}
    except json.JSONDecodeError:
        out = {}
    verdict = str(out.get("verdict", "")).lower().strip()
    if verdict not in VERDICTS:
        return {"verdict": "unparsed", "reason": raw[:200]}
    return {"verdict": verdict, "reason": out.get("reason", "")}
