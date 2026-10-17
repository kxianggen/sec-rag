"""Ask a question about the filings.

    uv run python ask.py "What did NVIDIA say about export controls?"

Retrieves the top chunks, then asks an LLM to answer from them. Uses Anthropic
if ANTHROPIC_API_KEY is set in .env, otherwise OpenAI if OPENAI_API_KEY is set,
otherwise just prints the retrieved chunks.
"""

import os
import sys

from dotenv import load_dotenv

from retrieve import retrieve_multi
from companies import detect_fiscal_years, detect_latest, detect_tickers

load_dotenv()


# Step 4 (prompt v2): one new rule, aimed at answers that quote a segment's number
# (e.g. Qualcomm QCT, AMD Data Center) when the question asks about the whole company.
# Not adopted (0.63 vs 0.65): fixed nothing; Q6 swapped "not provided" for a wrong AMD figure. Kept for the record.
RULE_TOTAL = ("5. When the question asks about a company's revenue, net income, R&D or similar, use the "
              "company-wide total, not a segment's figure, unless the question names the segment.\n")

# Prompt v3 (16 Oct, his rule): copy numbers exactly. The rubric already marked converted / re-rounded
# figures wrong, but the ANSWER prompt never told the model -- e.g. Q23 wrote AMD's "$8.1 billion" as
# "$8,100 million" (false precision; filing: $8,091 million). v3 = rules 1-4 + this rule (no RULE_TOTAL).
RULE_EXACT = ("5. Copy every number exactly as the excerpt writes it, with the same unit and precision: "
              "if it says \"$8,091 million\", write \"$8,091 million\"; if it says \"$8.1 billion\", write "
              "\"$8.1 billion\". Never convert units or re-round. If the excerpts give the same figure at "
              "different precision, use the most exact one. Calculate (a change, a percentage) only when the "
              "question asks for it, and show the exact figures you used.\n")

PROMPT_RULES = {1: "", 2: RULE_TOTAL, 3: RULE_EXACT}


def _excerpt(i: int, c: dict) -> str:
    if c["item"] == "XBRL":     # Phase 2: an exact figure from the filing's XBRL data (facts.py)
        return f"[{i}] {c['ticker']} 10-K, fiscal {c['fiscal_year']}: XBRL financial data (exact reported figure)\n{c['text']}"
    return f"[{i}] {c['ticker']} 10-K, fiscal {c['fiscal_year']} (period ending {c['period_end']}), Item {c['item']}\n{c['text']}"


def build_prompt(question: str, chunks: list[dict], prompt_version: int = 1) -> str:
    context = "\n\n".join(_excerpt(i, c) for i, c in enumerate(chunks, 1))
    return f"""You answer questions about companies' SEC 10-K filings. Follow these rules:
1. Use only the numbered excerpts below. Do not use outside knowledge, even if you know the answer.
2. After every claim, cite the excerpt it came from, like [1] or [2][3].
3. When you state a fact, say which company and which fiscal period it comes from.
4. If the excerpts do not contain the answer, reply exactly: Not in the filings.
{PROMPT_RULES[prompt_version]}
Excerpts:
{context}

Question: {question}"""


def call_llm(prompt: str, temperature: float | None = None, model: str | None = None) -> str | None:
    """temperature=None uses the provider default; the judge passes 0 so its grades repeat.
    model=None uses ANTHROPIC_MODEL / OPENAI_MODEL; the judge passes a stronger one (JUDGE_MODEL)."""
    extra = {} if temperature is None else {"temperature": temperature}
    if os.getenv("ANTHROPIC_API_KEY"):
        import anthropic
        client = anthropic.Anthropic()
        resp = client.messages.create(
            model=model or os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5"),
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}],
            **extra,
        )
        return resp.content[0].text
    if os.getenv("OPENAI_API_KEY"):
        from openai import OpenAI
        client = OpenAI()
        resp = client.chat.completions.create(
            model=model or os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[{"role": "user", "content": prompt}],
            **extra,
        )
        return resp.choices[0].message.content
    return None


def main():
    question = " ".join(sys.argv[1:])
    if not question:
        sys.exit('Usage: uv run python ask.py "your question"')

    tickers = detect_tickers(question)
    years = detect_fiscal_years(question)
    latest = detect_latest(question)
    chunks = retrieve_multi(question, k=10, tickers=tickers, fiscal_years=years, latest=latest, mode="hybrid")
    from facts import lookup as lookup_facts       # Phase 2: exact XBRL figures after the passages
    chunks = chunks + lookup_facts(question, tickers, years, latest)
    print(f"\nCOMPANY FILTER: {tickers or 'none (searching all companies)'}")
    print(f"FISCAL YEAR FILTER: {years or ('latest filing per company' if latest else 'none (all years)')}")
    answer = call_llm(build_prompt(question, chunks), temperature=0)

    print("\nANSWER\n" + (answer or "(no API key set — showing retrieved chunks only)"))
    print("\nSOURCES")
    for i, c in enumerate(chunks, 1):
        print(f"[{i}] {c.get('score', 1.0):.3f}  {c['ticker']} {c['period_end']} Item {c['item']}"
              + (f"  {c['text']}" if c["item"] == "XBRL" else ""))


if __name__ == "__main__":
    main()
