"""LLM-as-judge: is the system's answer correct, compared with the golden answer?

    from judge import judge
    judge(question, golden_answer, system_answer, required=...)    # rubric v2.1
    -> {"verdict": "correct" | "partial" | "incorrect", "category": "A".."E", "reason": "..."}

Two rubrics:
  v1  (T13) correct / partial / incorrect by our own rules; rounding counted as partial.
  v2  (16 Oct, default) the judge picks a CATEGORY, as in OpenAI's "fact" grader
      (A subset · B superset · C same · D contradicts · E differs only in ways that don't
      matter); B/C/E = correct, A = partial, D = incorrect. Rounding to the stated precision
      is allowed. Decided BEFORE re-grading anything, so the ruler wasn't tuned to the score.
  v2.1 (16 Oct, default) v2 graded against each question's `required` facts (golden.jsonl):
      leaving out OPTIONAL context costs nothing, stating anything wrong is still D. Graded by
      a stronger model than the system uses (JUDGE_MODEL, default gpt-4o) — gpt-4o-mini ignored
      rubric v2's own $8.4B example.
Check the judge against your own labels before trusting its numbers.
"""

import json
import os
import re

from ask import call_llm

VERDICTS = ("correct", "partial", "incorrect")

RUBRIC_V1 = """\
- correct: every number in the answer matches the golden answer for the right company and
  fiscal year, quoted as the filing states it. Different formatting of the SAME figure is fine
  ($67,120 million = $67.1 billion). For a "which is higher" question, the conclusion must be
  right AND the supporting numbers must match. For narrative questions, the answer covers the
  golden key points and adds nothing that contradicts them.
- partial: right company, year and conclusion, but a number is only approximately right
  (e.g. computed or rounded instead of quoted: 39.8% vs 40%) or uses a different but
  reasonable definition (e.g. balance-sheet debt instead of debt principal).
  For NARRATIVE questions: the answer is accurate on at least ONE of the golden key points
  and contradicts none of them, even if it leaves out other key points, specific events
  or numbers. Missing points make it partial, not incorrect.
- incorrect: any invented or unsupported number, the wrong fiscal year, the wrong company,
  the wrong conclusion, or a statement that contradicts the golden answer — even if the final
  conclusion happens to be right. For NARRATIVE questions: incorrect only if the answer covers
  none of the golden key points, or says something false.
- refusals: if the golden answer is "Not in the filings." then a refusal is correct and any
  attempted answer is incorrect. If the golden answer is a real answer, a refusal is incorrect."""

RUBRIC_V2 = """\
Compare the facts in the SYSTEM ANSWER with the GOLDEN ANSWER and pick ONE category:
  A  The system answer is a SUBSET of the golden answer: everything it states is consistent
     with the golden answer, but it leaves out some of it (e.g. covers 1 of 4 key points, or
     gives the numbers without the stated reason).
  B  The system answer is a SUPERSET: it contains everything in the golden answer, plus extra
     information that is consistent with it.
  C  The system answer contains the same facts as the golden answer.
  D  The system answer CONTRADICTS the golden answer anywhere: a wrong number, a number for the
     wrong fiscal year or wrong company, a wrong conclusion, a false statement, an invented
     figure — even if other parts are right. A refusal ("Not in the filings.") when the golden
     answer is a real answer is D. Any attempted answer when the golden answer is
     "Not in the filings." is D.
  E  The answers differ only in ways that don't matter: wording, units or formatting
     ($67,120 million = $67.1 billion), or rounding to the precision written
     ($63.9 billion for $63,887 million; $4.0 billion for $3,957 million). A figure outside
     that rounding is a wrong number (D): $8.4 billion for $8,091 million is D.
If the golden answer is "Not in the filings." and the system also refuses, that is C."""

PROMPT_V1 = """You are grading an answer from a question-answering system about SEC 10-K filings.
Compare the SYSTEM ANSWER with the GOLDEN ANSWER (the verified correct answer) using these rules:

{rubric}

QUESTION: {question}

GOLDEN ANSWER: {golden}

SYSTEM ANSWER: {answer}

Reply with JSON only, no other text:
{{"verdict": "correct" | "partial" | "incorrect", "reason": "<one sentence>"}}"""


PROMPT_V2 = """You are grading an answer from a question-answering system about SEC 10-K filings.

{rubric}

QUESTION: {question}

GOLDEN ANSWER: {golden}

SYSTEM ANSWER: {answer}

Reply with JSON only, no other text:
{{"category": "A" | "B" | "C" | "D" | "E", "reason": "<one sentence>"}}"""

RUBRIC_V21 = """\
The GOLDEN ANSWER has two parts. REQUIRED FACTS are what the question asks for. The FULL GOLDEN
ANSWER adds optional context. Compare the SYSTEM ANSWER with them and pick ONE category:
  A  Everything the system states is consistent with the full golden answer, but it is MISSING
     one or more REQUIRED FACTS (e.g. covers 1 of 3 required points). Missing OPTIONAL context
     is NOT a reason for A.
  B  It contains all REQUIRED FACTS plus extra information that is consistent with the full golden
     answer (or is not contradicted by it).
  C  It contains all REQUIRED FACTS and nothing that matters beyond them.
  D  It CONTRADICTS the golden answer anywhere — required OR optional part: a wrong number, a
     number for the wrong fiscal year or wrong company, a wrong conclusion, a false statement, an
     invented figure — even if other parts are right. A refusal ("Not in the filings.") when the
     required facts are a real answer is D. Any attempted answer when the golden answer is
     "Not in the filings." is D.
  E  It contains all REQUIRED FACTS, differing only in ways that don't matter: wording, units or
     formatting ($67,120 million = $67.1 billion), or rounding to the precision written ($63.9
     billion for $63,887 million; $4.0 billion for $3,957 million). A figure outside that rounding
     is a wrong number, so D: $8.4 billion for $8,091 million is D.
If the golden answer is "Not in the filings." and the system also refuses, that is C."""

PROMPT_V21 = """You are grading an answer from a question-answering system about SEC 10-K filings.

{rubric}

QUESTION: {question}

REQUIRED FACTS: {required}

FULL GOLDEN ANSWER: {golden}

SYSTEM ANSWER: {answer}

Reply with JSON only, no other text:
{{"category": "A" | "B" | "C" | "D" | "E", "reason": "<one sentence>"}}"""

JUDGE_MODEL = os.getenv("JUDGE_MODEL", "gpt-4o")

CATEGORY_VERDICT = {"A": "partial", "B": "correct", "C": "correct", "D": "incorrect", "E": "correct"}


def _parse(raw: str) -> dict:
    m = re.search(r"\{.*\}", raw, re.DOTALL)          # tolerate ```json fences or stray text
    try:
        return json.loads(m.group(0)) if m else {}
    except json.JSONDecodeError:
        return {}


def judge(question: str, golden: str, answer: str, rubric: str = "v2.1", required: str | None = None) -> dict:
    """-> {"verdict": correct | partial | incorrect | unparsed, "category": A-E or None, "reason": ...}"""
    if rubric == "v1":
        raw = call_llm(PROMPT_V1.format(rubric=RUBRIC_V1, question=question, golden=golden, answer=answer),
                       temperature=0) or ""
        out = _parse(raw)
        verdict = str(out.get("verdict", "")).lower().strip()
        if verdict not in VERDICTS:
            return {"verdict": "unparsed", "category": None, "reason": raw[:200]}
        return {"verdict": verdict, "category": None, "reason": out.get("reason", "")}

    if rubric == "v2.1":
        prompt = PROMPT_V21.format(rubric=RUBRIC_V21, question=question, required=required or golden,
                                   golden=golden, answer=answer)
        model = None if os.getenv("ANTHROPIC_API_KEY") and "JUDGE_MODEL" not in os.environ else JUDGE_MODEL
        raw = call_llm(prompt, temperature=0, model=model) or ""
    else:
        raw = call_llm(PROMPT_V2.format(rubric=RUBRIC_V2, question=question, golden=golden, answer=answer),
                       temperature=0) or ""
    out = _parse(raw)
    category = str(out.get("category", "")).upper().strip()[:1]
    if category not in CATEGORY_VERDICT:
        return {"verdict": "unparsed", "category": None, "reason": raw[:200]}
    return {"verdict": CATEGORY_VERDICT[category], "category": category, "reason": out.get("reason", "")}
